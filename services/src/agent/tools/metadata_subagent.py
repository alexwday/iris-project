"""
Metadata Subagent for Universal Cascading Retrieval Architecture.

Single path where every query goes through metadata first.
Each document gets a 3-way decision:
- "answered": Finding from metadata is sufficient
- "irrelevant": Document not relevant to query
- "needs_deep_research": Document likely relevant but needs full content

Flow:
1. Fetch all documents (summaries + top chunks)
2. Batch documents (batch_size=10, parallel processing)
3. For each document, LLM makes 3-way decision
4. Build response from "answered" findings with reference_index
5. Return list of doc IDs that need deep research

The database_router then:
- Uses answered_response directly
- Triggers file_research_subagent only for needs_research_doc_ids
- Merges file research findings with metadata findings
- Continues reference numbering across both

Key Design: Per-document decisions enable PROGRAMMATIC reference building.
The LLM returns document_id with each decision, which we validate against
what we sent. References are built from known document metadata,
not from LLM-generated text (which is error-prone).

Functions:
    query_metadata_unified: Entry point with mode-dependent processing
    fetch_all_documents: Fetch all docs with summaries and top chunks
    process_batch_unified: Process batch with 3-way decisions
    process_catalog_selection: Batch file selection for file_selection mode

Classes:
    DocumentMetadata: TypedDict for document metadata
    DocumentDecision: TypedDict for 3-way per-document decision
    UnifiedMetadataResult: TypedDict for unified result
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from sqlalchemy import text

from ...utils.env_config import config
from ...utils.prompt_loader import get_prompt
from ...connections.postgres import get_session
from ...connections.llm import call_llm

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION - loaded from database registry at runtime
# =============================================================================

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.2
DEFAULT_TOP_CHUNKS_PER_DOC = 3

MetadataContext = Dict[str, Any]


class MetadataSubagentError(Exception):
    """Exception raised for metadata subagent errors."""


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================


class DocumentMetadata(TypedDict):
    """Document-level metadata from iris_document_metadata."""

    document_id: str  # UUID as string
    document_name: str
    document_summary: str
    document_type: Optional[str]
    page_count: Optional[int]
    chunk_count: int
    file_name: Optional[str]
    similarity_score: float
    top_chunks: List[Dict[str, Any]]


class DocumentDecision(TypedDict):
    """Per-document 3-way decision from unified metadata processing.

    Unified architecture: LLM sees metadata and decides per-document:
    - "answered": Finding from metadata is sufficient
    - "irrelevant": Document not relevant to query
    - "needs_deep_research": Document likely relevant but needs full content
    """

    document_id: str
    status: str  # "answered" | "irrelevant" | "needs_deep_research"
    finding: Optional[str]  # If answered - the research finding
    page_reference: Optional[int]  # If answered - specific page if mentioned
    confidence: Optional[str]  # If answered - "high" | "medium" | "low"
    research_hint: Optional[str]  # If needs_deep_research - why it needs more


class UnifiedBatchResult(TypedDict):
    """Result from processing a batch with 3-way decisions."""

    batch_number: int
    document_decisions: List[DocumentDecision]


class UnifiedMetadataResult(TypedDict):
    """Result from unified metadata processing across all batches."""

    answered_findings: List[DocumentDecision]  # Documents answered from metadata
    needs_research_doc_ids: List[str]  # Document IDs needing deep research
    irrelevant_count: int  # Count of irrelevant documents
    answered_response: str  # Formatted response from answered findings
    answered_reference_index: Dict[str, Any]  # Reference index from answered


class BatchSelection(TypedDict):
    """Selection result from a single batch."""

    batch_number: int
    selected_ids: List[str]
    reasoning: str


class ReferenceEntry(TypedDict):
    """Reference index entry for a document finding."""

    doc_name: str
    page: Optional[int]
    file_link: Optional[str]
    file_name: Optional[str]
    source_filename: str
    highlight_text: str
    document_id: str
    finding: str


# =============================================================================
# CONFIG LOADING
# =============================================================================


def _get_research_config(db_source: str) -> Dict[str, Any]:
    """
    Load research_config from iris_database_registry.

    Args:
        db_source: Database source identifier.

    Returns:
        Research configuration dict with batch_size, max_selected_files, etc.

    Raises:
        MetadataSubagentError: If configuration cannot be loaded.
    """
    from .database_metadata import DatabaseMetadataRepository

    try:
        config = DatabaseMetadataRepository().get_research_config(db_source)
    except Exception as exc:
        raise MetadataSubagentError(
            f"Failed to load research_config for {db_source}: {exc}"
        ) from exc

    # Validate required config fields
    required_fields = [
        "batch_size",
        "max_selected_files",
        "top_chunks_in_catalog_selection",
        "top_chunks_in_metadata_research",
        "page_threshold_for_full_content",
        "enable_db_wide_deep_research",
    ]
    missing = [f for f in required_fields if f not in config]
    if missing:
        raise MetadataSubagentError(
            f"Missing required config fields for {db_source}: {missing}"
        )

    return config


# =============================================================================
# DATABASE QUERIES
# =============================================================================


def fetch_all_documents(
    db_source: str,
    query_embedding: List[float],
    top_chunks_per_doc: int = DEFAULT_TOP_CHUNKS_PER_DOC,
) -> List[DocumentMetadata]:
    """
    Fetch ALL documents with full summaries and top chunks.

    No limit on document count - batching handles token management.

    Args:
        db_source: The database source to query.
        query_embedding: The query embedding vector for similarity ranking.
        top_chunks_per_doc: Number of top chunks per document.

    Returns:
        List of DocumentMetadata with full summaries and top chunks.
    """
    logger.info("Fetching all documents for %s", db_source)
    documents: List[DocumentMetadata] = []

    try:
        with get_session() as session:
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Fetch all documents with embeddings, ranked by similarity
            doc_result = session.execute(
                text(
                    """
                    SELECT
                        m.id,
                        m.document_name,
                        m.document_summary,
                        m.document_type,
                        m.page_count,
                        m.file_name,
                        1 - (m.summary_embedding <=> CAST(:embedding AS halfvec)) AS similarity_score,
                        (SELECT COUNT(*) FROM iris_document_chunks c
                         WHERE c.document_id = m.id) as chunk_count
                    FROM iris_document_metadata m
                    WHERE m.db_source = :db_source
                    AND m.summary_embedding IS NOT NULL
                    ORDER BY similarity_score DESC
                    """
                ),
                {"embedding": embedding_str, "db_source": db_source},
            )

            doc_rows = doc_result.mappings().all()
            logger.info("Found %d documents in %s", len(doc_rows), db_source)

            for row in doc_rows:
                doc_id = str(row["id"])

                # Fetch top chunks for this document
                chunk_result = session.execute(
                    text(
                        """
                        SELECT
                            c.id,
                            c.chunk_number,
                            c.chunk_content,
                            c.primary_section_name,
                            c.subsection_name,
                            c.hierarchy_path,
                            c.page_number,
                            1 - (c.chunk_embedding <=> CAST(:embedding AS halfvec)) AS chunk_similarity
                        FROM iris_document_chunks c
                        WHERE c.document_id = :doc_id
                        AND c.chunk_embedding IS NOT NULL
                        ORDER BY chunk_similarity DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "embedding": embedding_str,
                        "doc_id": row["id"],
                        "limit": top_chunks_per_doc,
                    },
                )

                top_chunks = []
                for chunk_row in chunk_result.mappings().all():
                    top_chunks.append(
                        {
                            "chunk_id": str(chunk_row["id"]),
                            "chunk_number": chunk_row["chunk_number"],
                            "chunk_content": chunk_row["chunk_content"],
                            "primary_section_name": chunk_row["primary_section_name"],
                            "subsection_name": chunk_row["subsection_name"],
                            "hierarchy_path": chunk_row["hierarchy_path"],
                            "page_number": chunk_row["page_number"],
                            "similarity": (
                                float(chunk_row["chunk_similarity"])
                                if chunk_row["chunk_similarity"]
                                else 0.0
                            ),
                        }
                    )

                documents.append(
                    {
                        "document_id": doc_id,
                        "document_name": row["document_name"],
                        "document_summary": row["document_summary"] or "",
                        "document_type": row["document_type"],
                        "page_count": row["page_count"],
                        "chunk_count": row["chunk_count"] or 0,
                        "file_name": row["file_name"],
                        "similarity_score": float(row["similarity_score"]),
                        "top_chunks": top_chunks,
                    }
                )

    except (ValueError, TypeError, KeyError, RuntimeError) as exc:
        logger.error(
            "Error fetching documents for %s: %s", db_source, exc, exc_info=True
        )

    return documents


# =============================================================================
# DOCUMENT FORMATTING
# =============================================================================


def _format_batch_documents(documents: List[DocumentMetadata]) -> str:
    """Format batch documents for LLM processing.

    Each document includes its ID prominently so LLM can reference it
    in the per-document findings response.
    """
    formatted = ""

    for i, doc in enumerate(documents, 1):
        formatted += f"## Document {i}\n"
        formatted += f"**document_id:** `{doc['document_id']}`\n"
        formatted += f"**document_name:** {doc['document_name']}\n"
        formatted += f"**Type:** {doc.get('document_type', 'Unknown')}\n"
        formatted += f"**Pages:** {doc.get('page_count', 'Unknown')}\n\n"
        formatted += f"**Summary:**\n{doc['document_summary']}\n\n"

        if doc.get("top_chunks"):
            formatted += "**Most Relevant Excerpts:**\n"
            for chunk in doc["top_chunks"]:
                page_num = chunk.get("page_number", "?")
                if chunk.get("hierarchy_path"):
                    formatted += f"*From {chunk['hierarchy_path']} (Page {page_num})*\n"
                elif chunk.get("primary_section_name"):
                    formatted += f"*From {chunk['primary_section_name']}"
                    if chunk.get("subsection_name"):
                        formatted += f" > {chunk['subsection_name']}"
                    formatted += f" (Page {page_num})*\n"
                else:
                    formatted += f"*(Page {page_num})*\n"
                content = chunk.get("chunk_content", "")
                formatted += f"```\n{content}\n```\n\n"

        formatted += "---\n\n"

    return formatted


# =============================================================================
# FILE SELECTION PATH
# =============================================================================


def select_files_from_batch(
    research_statement: str,
    batch_documents: List[DocumentMetadata],
    batch_number: int,
    total_batches: int,
    ctx: MetadataContext,
) -> Tuple[BatchSelection, Optional[Dict[str, Any]]]:
    """
    LLM selects relevant files from a batch for deep research.

    Args:
        research_statement: The research query.
        batch_documents: Documents in this batch.
        batch_number: Current batch number (1-indexed).
        total_batches: Total number of batches.
        ctx: Context with token, process_monitor, etc.

    Returns:
        Tuple of (BatchSelection, usage_details).
    """
    logger.info("Selecting files from batch %d of %d", batch_number, total_batches)
    usage_details = None

    try:
        prompt = get_prompt("subagent", "catalog_batch_selection")
        if not prompt:
            raise ValueError("Prompt not found: subagent/catalog_batch_selection")

        formatted_docs = _format_batch_documents(batch_documents)

        system_prompt = prompt.get("system_prompt", "")
        user_prompt = (
            prompt.get("user_prompt", "")
            .replace("{{research_statement}}", research_statement)
            .replace("{{batch_number}}", str(batch_number))
            .replace("{{total_batches}}", str(total_batches))
            .replace("{{batch_documents}}", formatted_docs)
        )

        model_config = config.get_model_config(MODEL_CAPABILITY)
        tools = [prompt.get("tool_definition")] if prompt.get("tool_definition") else []

        result = call_llm(
            oauth_token=ctx.get("token") or "placeholder_token",
            model=model_config["name"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            tools=tools,
            tool_choice={
                "type": "function",
                "function": {"name": "select_relevant_files"},
            },
            stream=False,
            prompt_token_cost=model_config["prompt_token_cost"],
            completion_token_cost=model_config["completion_token_cost"],
        )

        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
        else:
            response = result

        # Track usage
        process_monitor = ctx.get("process_monitor")
        stage_name = ctx.get("stage_name")
        if usage_details and process_monitor and stage_name:
            process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)

        # Parse tool response - must get valid selection
        if not (
            response
            and hasattr(response, "choices")
            and response.choices
            and response.choices[0].message
            and response.choices[0].message.tool_calls
        ):
            raise MetadataSubagentError(
                f"No valid tool response from LLM for batch {batch_number}"
            )

        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name != "select_relevant_files":
            raise MetadataSubagentError(
                f"Unexpected tool call '{tool_call.function.name}' for batch {batch_number}"
            )

        arguments = json.loads(tool_call.function.arguments)
        selection: BatchSelection = {
            "batch_number": batch_number,
            "selected_ids": arguments.get("document_ids", []),
            "reasoning": arguments.get("reasoning", ""),
        }
        return selection, usage_details

    except (ValueError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        logger.error(
            "Error selecting files from batch %d: %s", batch_number, exc, exc_info=True
        )
        raise MetadataSubagentError(
            f"Failed to select files from batch {batch_number}: {exc}"
        ) from exc


def process_catalog_selection(
    research_statement: str,
    db_source: str,
    all_documents: List[DocumentMetadata],
    batch_size: int,
    max_selected_files: int,
    ctx: MetadataContext,
) -> Tuple[List[str], str]:
    """
    Process catalog selection path: batch documents and select relevant files.

    Args:
        research_statement: The research query.
        db_source: Database being queried.
        all_documents: All documents fetched from database.
        batch_size: Number of documents per batch.
        max_selected_files: Maximum number of files to select for deep research.
        ctx: Context with token, process_monitor, etc.

    Returns:
        Tuple of (list of selected document IDs, combined reasoning).

    Raises:
        MetadataSubagentError: If batch processing fails.
    """
    logger.info(
        "Processing catalog selection for %s with %d documents (max_selected=%d)",
        db_source,
        len(all_documents),
        max_selected_files,
    )

    # Create batches
    batches = [
        all_documents[i : i + batch_size]
        for i in range(0, len(all_documents), batch_size)
    ]
    total_batches = len(batches)
    logger.info(
        "Created %d batches of up to %d documents each", total_batches, batch_size
    )

    # Process each batch
    all_selected_ids: List[str] = []
    all_reasoning: List[str] = []

    for batch_num, batch_docs in enumerate(batches, 1):
        selection, _ = select_files_from_batch(
            research_statement=research_statement,
            batch_documents=batch_docs,
            batch_number=batch_num,
            total_batches=total_batches,
            ctx=ctx,
        )
        all_selected_ids.extend(selection["selected_ids"])
        if selection["reasoning"]:
            all_reasoning.append(f"Batch {batch_num}: {selection['reasoning']}")

    # Enforce max_selected_files limit
    if len(all_selected_ids) > max_selected_files:
        logger.info(
            "Limiting selected files from %d to %d (max_selected_files)",
            len(all_selected_ids),
            max_selected_files,
        )
        all_selected_ids = all_selected_ids[:max_selected_files]

    combined_reasoning = (
        " | ".join(all_reasoning) if all_reasoning else "File selection"
    )

    logger.info(
        "Catalog selection complete: %d files selected for %s",
        len(all_selected_ids),
        db_source,
    )

    return all_selected_ids, combined_reasoning


# =============================================================================
# UNIFIED METADATA-FIRST ARCHITECTURE
# Single path with 3-way per-document decisions:
# - answered: Finding from metadata is sufficient
# - irrelevant: Document not relevant
# - needs_deep_research: Needs full document analysis
# =============================================================================


def _validate_unified_decisions(
    raw_decisions: List[Dict[str, Any]],
    valid_doc_ids: set,
    batch_documents: List[DocumentMetadata],
) -> List[DocumentDecision]:
    """
    Validate and normalize 3-way decisions from LLM response.

    - Filters to only document_ids we actually sent
    - Ensures all documents in batch have a decision
    - Defaults missing documents to needs_deep_research (safer than irrelevant)

    Args:
        raw_decisions: Raw decisions from LLM response.
        valid_doc_ids: Set of document_ids we sent to LLM.
        batch_documents: The documents in the batch.

    Returns:
        Validated list of DocumentDecision.
    """
    validated: List[DocumentDecision] = []
    seen_ids: set = set()

    valid_statuses = {"answered", "irrelevant", "needs_deep_research"}

    for d in raw_decisions:
        doc_id = d.get("document_id", "")
        status = d.get("status", "")

        # Skip if not in our batch, already seen, or invalid status
        if doc_id not in valid_doc_ids or doc_id in seen_ids:
            if doc_id and doc_id not in valid_doc_ids:
                logger.warning("LLM returned unknown document_id: %s", doc_id)
            continue

        if status not in valid_statuses:
            logger.warning(
                "Invalid status '%s' for doc %s, defaulting to needs_deep_research",
                status,
                doc_id,
            )
            status = "needs_deep_research"

        seen_ids.add(doc_id)

        validated.append(
            {
                "document_id": doc_id,
                "status": status,
                "finding": d.get("finding") if status == "answered" else None,
                "page_reference": (
                    d.get("page_reference") if status == "answered" else None
                ),
                "confidence": d.get("confidence") if status == "answered" else None,
                "research_hint": (
                    d.get("research_hint") if status == "needs_deep_research" else None
                ),
            }
        )

    # Add missing documents - default to needs_deep_research (safer assumption)
    for doc in batch_documents:
        if doc["document_id"] not in seen_ids:
            logger.warning(
                "Document %s missing from LLM response, defaulting to needs_deep_research",
                doc["document_id"],
            )
            validated.append(
                {
                    "document_id": doc["document_id"],
                    "status": "needs_deep_research",
                    "finding": None,
                    "page_reference": None,
                    "confidence": None,
                    "research_hint": "Document was not evaluated by LLM",
                }
            )

    return validated


def _build_reference_index_from_decisions(
    decisions: List[DocumentDecision],
    documents: List[DocumentMetadata],
    start_ref_num: int = 1,
) -> Dict[str, ReferenceEntry]:
    """
    Build reference index from answered decisions.

    Only includes documents with status="answered" and a finding.
    References are built from KNOWN document metadata.

    Args:
        decisions: Per-document decisions with 3-way status.
        documents: Full document metadata list.
        start_ref_num: Starting reference number (for merging with file research).

    Returns:
        Reference index dict keyed by reference number.
    """
    doc_lookup = {doc["document_id"]: doc for doc in documents}

    reference_index: Dict[str, ReferenceEntry] = {}
    ref_num = start_ref_num

    for decision in decisions:
        if decision.get("status") != "answered" or not decision.get("finding"):
            continue

        doc_id = decision["document_id"]
        doc = doc_lookup.get(doc_id)

        if not doc:
            logger.warning("Document not found for decision: %s", doc_id)
            continue

        reference_index[str(ref_num)] = {
            "doc_name": doc["document_name"],
            "page": decision.get("page_reference"),
            "file_link": doc.get("file_name"),
            "file_name": doc.get("file_name"),
            "source_filename": doc["document_name"],
            "highlight_text": "",
            "document_id": doc_id,
            "finding": decision.get("finding", ""),
        }
        ref_num += 1

    return reference_index


def _format_unified_response(
    decisions: List[DocumentDecision],
    documents: List[DocumentMetadata],
    start_ref_num: int = 1,
) -> str:
    """
    Format answered decisions into research response text.

    Args:
        decisions: Per-document decisions.
        documents: Full document metadata list.
        start_ref_num: Starting reference number.

    Returns:
        Formatted research response string.
    """
    doc_lookup = {doc["document_id"]: doc for doc in documents}
    response_parts = []
    ref_num = start_ref_num

    for decision in decisions:
        if decision.get("status") != "answered" or not decision.get("finding"):
            continue

        doc = doc_lookup.get(decision["document_id"])
        if not doc:
            continue

        doc_name = doc["document_name"]
        page_ref = decision.get("page_reference")
        finding_text = decision["finding"]
        confidence = decision.get("confidence", "")

        # Format with reference and confidence
        if page_ref:
            header = f"**{doc_name}** (p. {page_ref}) [REF:{ref_num}]"
        else:
            header = f"**{doc_name}** [REF:{ref_num}]"

        if confidence:
            header += f" _{confidence} confidence_"

        response_parts.append(f"{header}:\n{finding_text}")
        ref_num += 1

    if not response_parts:
        return ""

    return "\n\n".join(response_parts)


def process_batch_unified(
    research_statement: str,
    batch_documents: List[DocumentMetadata],
    batch_number: int,
    total_batches: int,
    ctx: MetadataContext,
) -> Tuple[UnifiedBatchResult, Optional[Dict[str, Any]]]:
    """
    Process a batch with 3-way per-document decisions.

    Args:
        research_statement: The research query.
        batch_documents: Documents in this batch.
        batch_number: Current batch number (1-indexed).
        total_batches: Total number of batches.
        ctx: Context with token, process_monitor, etc.

    Returns:
        Tuple of (UnifiedBatchResult, usage_details).
    """
    logger.info(
        "Processing unified batch %d of %d (%d documents)",
        batch_number,
        total_batches,
        len(batch_documents),
    )
    usage_details = None
    valid_doc_ids = {doc["document_id"] for doc in batch_documents}

    try:
        prompt = get_prompt("subagent", "metadata_unified_findings")
        if not prompt:
            raise ValueError("Prompt not found: subagent/metadata_unified_findings")

        formatted_docs = _format_batch_documents(batch_documents)

        system_prompt = prompt.get("system_prompt", "")
        user_prompt = (
            prompt.get("user_prompt", "")
            .replace("{{research_statement}}", research_statement)
            .replace("{{batch_number}}", str(batch_number))
            .replace("{{total_batches}}", str(total_batches))
            .replace("{{document_count}}", str(len(batch_documents)))
            .replace("{{batch_documents}}", formatted_docs)
        )

        model_config = config.get_model_config(MODEL_CAPABILITY)
        tools = [prompt.get("tool_definition")] if prompt.get("tool_definition") else []

        result = call_llm(
            oauth_token=ctx.get("token") or "placeholder_token",
            model=model_config["name"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            tools=tools,
            tool_choice={
                "type": "function",
                "function": {"name": "return_unified_decisions"},
            },
            stream=False,
            prompt_token_cost=model_config["prompt_token_cost"],
            completion_token_cost=model_config["completion_token_cost"],
        )

        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
        else:
            response = result

        # Track usage
        process_monitor = ctx.get("process_monitor")
        stage_name = ctx.get("stage_name")
        if usage_details and process_monitor and stage_name:
            process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)

        # Parse tool response - must get valid decisions
        if not (
            response
            and hasattr(response, "choices")
            and response.choices
            and response.choices[0].message
            and response.choices[0].message.tool_calls
        ):
            raise MetadataSubagentError(
                f"No valid tool response from LLM for unified batch {batch_number}"
            )

        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name != "return_unified_decisions":
            raise MetadataSubagentError(
                f"Unexpected tool call '{tool_call.function.name}' for unified batch {batch_number}"
            )

        arguments = json.loads(tool_call.function.arguments)
        raw_decisions = arguments.get("document_decisions", [])

        validated_decisions = _validate_unified_decisions(
            raw_decisions, valid_doc_ids, batch_documents
        )

        return {
            "batch_number": batch_number,
            "document_decisions": validated_decisions,
        }, usage_details

    except (ValueError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        logger.error(
            "Error processing unified batch %d: %s", batch_number, exc, exc_info=True
        )
        raise MetadataSubagentError(
            f"Failed to process unified batch {batch_number}: {exc}"
        ) from exc


def query_metadata_unified(
    research_statement: str,
    db_source: str,
    query_context: Optional[MetadataContext] = None,
    mode: str = "metadata_research",
) -> UnifiedMetadataResult:
    """
    Query document metadata with mode-dependent processing.

    Two processing modes based on query type:

    **file_selection mode** (for selective/non-DB-wide queries):
    - Uses top 1 chunk per file (minimal context)
    - LLM SELECTS which files to deep research (binary yes/no)
    - ALL selected files go to deep research
    - Used when clarifier determines query is NOT DB-wide

    **metadata_research mode** (for DB-wide queries):
    - Uses top 3 chunks per file (more context for answering)
    - LLM makes 3-way decision: answered/irrelevant/needs_deep_research
    - Only "needs_deep_research" files go to deep research
    - Used when clarifier determines query IS DB-wide

    Args:
        research_statement: The research query/statement.
        db_source: Database source to query (e.g., 'internal_capm').
        query_context: Context dict containing:
            - token: OAuth token
            - process_monitor: For tracking
            - stage_name: For tracking
            - query_embedding: Required, pre-computed by planner
        mode: Processing mode - "file_selection" or "metadata_research"
            (default: "metadata_research" for backward compatibility)

    Returns:
        UnifiedMetadataResult with:
        - answered_findings: Documents answered from metadata (empty for file_selection)
        - needs_research_doc_ids: Document IDs for deep research
        - irrelevant_count: Count of irrelevant documents
        - answered_response: Formatted response from answered findings
        - answered_reference_index: Reference index from answered
    """
    ctx = query_context or {}

    # Validate mode - strict, no fallback
    if mode not in ("file_selection", "metadata_research"):
        raise MetadataSubagentError(
            f"Invalid mode '{mode}'. Must be 'file_selection' or 'metadata_research'."
        )

    logger.info(
        "Starting metadata query for %s (mode=%s): '%s...'",
        db_source,
        mode,
        research_statement[:100],
    )

    # Query embedding is required - no fallback
    query_embedding = ctx.get("query_embedding")
    if query_embedding is None:
        raise MetadataSubagentError(
            f"No query_embedding provided for {db_source}. "
            "Query embedding must be pre-computed by planner."
        )

    # Load config - will raise MetadataSubagentError if config unavailable
    research_config = _get_research_config(db_source)
    batch_size = research_config["batch_size"]
    max_selected_files = research_config["max_selected_files"]

    # Mode-dependent chunk count from config:
    # - file_selection: top_chunks_in_catalog_selection (typically 1)
    # - metadata_research: top_chunks_in_metadata_research (typically 3)
    if mode == "file_selection":
        top_chunks = research_config["top_chunks_in_catalog_selection"]
    else:
        top_chunks = research_config["top_chunks_in_metadata_research"]

    logger.info(
        "Config for %s (mode=%s): batch_size=%d, top_chunks=%d, max_selected_files=%d",
        db_source,
        mode,
        batch_size,
        top_chunks,
        max_selected_files,
    )

    # Fetch all documents
    all_documents = fetch_all_documents(db_source, query_embedding, top_chunks)

    if not all_documents:
        return {
            "answered_findings": [],
            "needs_research_doc_ids": [],
            "irrelevant_count": 0,
            "answered_response": f"No documents found in {db_source}.",
            "answered_reference_index": {},
        }

    # ==========================================================================
    # MODE-DEPENDENT PROCESSING
    # ==========================================================================

    if mode == "file_selection":
        # FILE SELECTION MODE (for selective/non-DB-wide queries)
        # - LLM selects files from catalog (binary yes/no)
        # - ALL selected files go to deep research
        # - No answered findings (selection only, not answering)
        logger.info(
            "File selection mode: selecting files from %d documents",
            len(all_documents),
        )

        selected_ids, reasoning = process_catalog_selection(
            research_statement=research_statement,
            db_source=db_source,
            all_documents=all_documents,
            batch_size=batch_size,
            max_selected_files=max_selected_files,
            ctx=ctx,
        )

        logger.info(
            "File selection complete for %s: %d files selected for deep research",
            db_source,
            len(selected_ids),
        )

        # For file_selection mode, ALL selected files go to deep research
        # No answered findings - this is selection, not answering
        return {
            "answered_findings": [],
            "needs_research_doc_ids": selected_ids,
            "irrelevant_count": len(all_documents) - len(selected_ids),
            "answered_response": "",  # No response - just selection
            "answered_reference_index": {},
        }

    else:
        # METADATA RESEARCH MODE (for DB-wide queries)
        # - LLM makes 3-way decisions: answered/irrelevant/needs_deep_research
        # - Only "needs_deep_research" files go to deep research
        logger.info(
            "Metadata research mode: processing %d documents with 3-way decisions",
            len(all_documents),
        )

        # Create batches
        batches = [
            all_documents[i : i + batch_size]
            for i in range(0, len(all_documents), batch_size)
        ]
        total_batches = len(batches)
        logger.info("Created %d batches for sequential processing", total_batches)

        # Process batches sequentially
        all_decisions: List[DocumentDecision] = []

        for batch_num, batch_docs in enumerate(batches, 1):
            try:
                batch_result, _ = process_batch_unified(
                    research_statement,
                    batch_docs,
                    batch_num,
                    total_batches,
                    ctx,
                )
                all_decisions.extend(batch_result["document_decisions"])
                logger.info(
                    "Metadata research batch %d/%d complete: %d decisions",
                    batch_num,
                    total_batches,
                    len(batch_result["document_decisions"]),
                )
            except Exception as exc:
                logger.error(
                    "Metadata research batch %d failed: %s",
                    batch_num,
                    exc,
                    exc_info=True,
                )
                raise

        # Categorize decisions
        answered_findings = [d for d in all_decisions if d.get("status") == "answered"]
        needs_research = [
            d for d in all_decisions if d.get("status") == "needs_deep_research"
        ]
        irrelevant = [d for d in all_decisions if d.get("status") == "irrelevant"]

        needs_research_doc_ids = [d["document_id"] for d in needs_research]

        logger.info(
            "Metadata research complete for %s: %d answered, %d need research, %d irrelevant",
            db_source,
            len(answered_findings),
            len(needs_research),
            len(irrelevant),
        )

        # Build response and reference index from answered findings
        answered_response = _format_unified_response(answered_findings, all_documents)
        answered_reference_index = _build_reference_index_from_decisions(
            answered_findings, all_documents
        )

        return {
            "answered_findings": answered_findings,
            "needs_research_doc_ids": needs_research_doc_ids,
            "irrelevant_count": len(irrelevant),
            "answered_response": answered_response,
            "answered_reference_index": answered_reference_index,
        }
