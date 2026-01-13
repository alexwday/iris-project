"""Metadata subagent that routes every query through document metadata.

The LLM makes per-document 3-way decisions (answered, irrelevant, needs_deep_research)
so references can be built deterministically from metadata before any deep research.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict

from sqlalchemy import text

from ...utils.env_config import config
from ...utils.prompt_loader import fetch_prompt_with_context
from ...connections.postgres import get_database_session
from ...connections.llm import execute_llm_call
from .research_types import Finding, FindingsList

logger = logging.getLogger(__name__)

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.2

MetadataContext = Dict[str, Any]


class MetadataSubagentError(Exception):
    """Exception raised for metadata subagent errors."""


class DocumentMetadata(TypedDict):
    """Document-level metadata from iris_document_metadata."""

    document_id: str
    document_name: str
    document_index: int
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
    Finding is required for all statuses; page_reference is optional.
    """

    document_id: str
    status: str
    finding: str
    page_reference: Optional[int]


class UnifiedBatchResult(TypedDict):
    """Result from processing a batch with 3-way decisions."""

    batch_number: int
    document_decisions: List[DocumentDecision]


class UnifiedMetadataResult(TypedDict):
    """Result from unified metadata processing across all batches."""

    answered_findings: List[DocumentDecision]
    needs_research_doc_ids: List[str]
    irrelevant_count: int
    answered_response: str
    findings: FindingsList  # Unified finding format for summarizer


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


def _get_research_config(db_source: str) -> Dict[str, Any]:
    """Load research configuration from iris_database_registry.

    Args:
        db_source: Database source identifier.

    Returns:
        Research configuration dict with batch_size, max_selected_files, etc.

    Raises:
        MetadataSubagentError: If configuration cannot be loaded.
    """
    from .database_metadata import DatabaseMetadataCache

    try:
        research_config = DatabaseMetadataCache().get_research_config(db_source)
    except Exception as exc:
        raise MetadataSubagentError(
            f"Failed to load research_config for {db_source}: {exc}"
        ) from exc

    required_fields = [
        "batch_size",
        "max_selected_files",
        "top_chunks_in_catalog_selection",
        "top_chunks_in_metadata_research",
        "page_threshold_for_full_content",
        "enable_db_wide_deep_research",
        "metadata_context_fields",
    ]
    missing = [field for field in required_fields if field not in research_config]
    if missing:
        raise MetadataSubagentError(
            f"Missing required config fields for {db_source}: {missing}"
        )

    return research_config


def fetch_all_document_metadata(
    db_source: str,
    query_embedding: List[float],
    top_chunks_per_doc: int,
) -> List[DocumentMetadata]:
    """Fetch metadata and top chunks for every document in a source.

    Args:
        db_source: Database source to query.
        query_embedding: Query embedding vector for similarity ranking.
        top_chunks_per_doc: Number of top chunks per document.

    Returns:
        Documents ordered by similarity score.

    Raises:
        MetadataSubagentError: If the database query fails.
    """
    logger.info("Fetching all documents for %s", db_source)

    try:
        documents: List[DocumentMetadata] = []
        with get_database_session() as session:
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            doc_rows = (
                session.execute(
                    text(
                        """
                    SELECT
                        m.id,
                        m.document_name,
                        m.document_summary,
                        m.document_type,
                        m.page_count,
                        m.file_name,
                        1 - (m.summary_embedding <=> CAST(:embedding AS halfvec))
                            AS similarity_score,
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
                .mappings()
                .all()
            )
            logger.info("Found %d documents in %s", len(doc_rows), db_source)

            for idx, row in enumerate(doc_rows, 1):
                doc_id = str(row["id"])

                chunk_rows = (
                    session.execute(
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
                            1 - (c.chunk_embedding <=> CAST(:embedding AS halfvec))
                                AS chunk_similarity
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
                    .mappings()
                    .all()
                )

                top_chunks = [
                    {
                        "chunk_id": str(chunk_row["id"]),
                        "chunk_number": chunk_row["chunk_number"],
                        "chunk_content": chunk_row["chunk_content"],
                        "primary_section_name": chunk_row["primary_section_name"],
                        "subsection_name": chunk_row["subsection_name"],
                        "hierarchy_path": chunk_row["hierarchy_path"],
                        "page_number": chunk_row["page_number"],
                        "similarity": float(chunk_row["chunk_similarity"] or 0.0),
                    }
                    for chunk_row in chunk_rows
                ]

                documents.append(
                    {
                        "document_id": doc_id,
                        "document_name": row["document_name"],
                        "document_index": idx,
                        "document_summary": row["document_summary"] or "",
                        "document_type": row["document_type"],
                        "page_count": row["page_count"],
                        "chunk_count": row["chunk_count"] or 0,
                        "file_name": row["file_name"],
                        "similarity_score": float(row["similarity_score"]),
                        "top_chunks": top_chunks,
                    }
                )
        return documents
    except Exception as exc:
        logger.error(
            "Error fetching documents for %s: %s", db_source, exc, exc_info=True
        )
        raise MetadataSubagentError(
            f"Failed to fetch documents for {db_source}: {exc}"
        ) from exc


def _format_batch_documents(
    documents: List[DocumentMetadata],
    metadata_context_fields: Optional[List[str]] = None,
) -> str:
    """Format a batch of documents for LLM processing using XML.

    Args:
        documents: Documents to include in the batch prompt.
        metadata_context_fields: Which metadata fields to include. Valid values:
            'document_summary', 'document_description', 'document_usage'.
            Defaults to ['document_summary'] if not specified.

    Returns:
        XML formatted string for the LLM prompt.
    """
    if metadata_context_fields is None:
        metadata_context_fields = ["document_summary"]

    parts: List[str] = []

    for i, doc in enumerate(documents, 1):
        parts.append(f"<document index=\"{i}\">")
        parts.append(f"  <document_id>{doc['document_id']}</document_id>")
        parts.append(f"  <document_name>{doc['document_name']}</document_name>")
        parts.append(f"  <type>{doc.get('document_type', 'Unknown')}</type>")
        parts.append(f"  <pages>{doc.get('page_count', 'Unknown')}</pages>")

        # Include configured metadata fields
        if "document_summary" in metadata_context_fields and doc.get("document_summary"):
            parts.append(f"  <summary>{doc['document_summary']}</summary>")
        if "document_description" in metadata_context_fields and doc.get("document_description"):
            parts.append(f"  <description>{doc['document_description']}</description>")
        if "document_usage" in metadata_context_fields and doc.get("document_usage"):
            parts.append(f"  <usage>{doc['document_usage']}</usage>")

        if doc.get("top_chunks"):
            parts.append("  <excerpts>")
            for chunk in doc["top_chunks"]:
                page_num = chunk.get("page_number", "?")
                location = ""
                if chunk.get("hierarchy_path"):
                    location = chunk["hierarchy_path"]
                elif chunk.get("primary_section_name"):
                    location = chunk["primary_section_name"]
                    if chunk.get("subsection_name"):
                        location += f" > {chunk['subsection_name']}"

                parts.append(f"    <excerpt page=\"{page_num}\" location=\"{location}\">")
                content = chunk.get("chunk_content", "")
                # Escape XML special characters in content
                content = (
                    content.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                parts.append(f"      {content}")
                parts.append("    </excerpt>")
            parts.append("  </excerpts>")

        parts.append("</document>")
        parts.append("")

    return "\n".join(parts)


def select_relevant_files_from_batch(
    research_statement: str,
    batch_documents: List[DocumentMetadata],
    batch_number: int,
    total_batches: int,
    ctx: MetadataContext,
    metadata_context_fields: Optional[List[str]] = None,
) -> Tuple[BatchSelection, Optional[Dict[str, Any]]]:
    """Select relevant files from a batch via LLM tool call.

    Args:
        research_statement: The research query.
        batch_documents: Documents in this batch.
        batch_number: Current batch number (1-indexed).
        total_batches: Total number of batches.
        ctx: Context with token, process_monitor, etc.
        metadata_context_fields: Which metadata fields to include in document context.

    Returns:
        Batch selection and optional usage details.

    Raises:
        MetadataSubagentError: If the LLM does not return a valid selection.
    """
    logger.info("Selecting files from batch %d of %d", batch_number, total_batches)
    usage_details = None

    try:
        system_prompt, tools, user_template = fetch_prompt_with_context(
            "subagent", "catalog_batch_selection"
        )

        formatted_docs = _format_batch_documents(batch_documents, metadata_context_fields)

        user_prompt = (
            user_template.replace("{{research_statement}}", research_statement)
            .replace("{{batch_number}}", str(batch_number))
            .replace("{{total_batches}}", str(total_batches))
            .replace("{{batch_documents}}", formatted_docs)
        )

        model_config = config.get_model_settings(MODEL_CAPABILITY)

        result = execute_llm_call(
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

        process_monitor = ctx.get("process_monitor")
        stage_name = ctx.get("stage_name")
        if usage_details and process_monitor and stage_name:
            process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)

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
                f"Unexpected tool call '{tool_call.function.name}' "
                f"for batch {batch_number}"
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


def process_catalog_file_selection(
    research_statement: str,
    db_source: str,
    all_documents: List[DocumentMetadata],
    batch_size: int,
    max_selected_files: int,
    ctx: MetadataContext,
    metadata_context_fields: Optional[List[str]] = None,
) -> Tuple[List[str], str]:
    """Batch documents and select relevant files for deep research.

    Args:
        research_statement: The research query.
        db_source: Database being queried.
        all_documents: All documents fetched from database.
        batch_size: Number of documents per batch.
        max_selected_files: Maximum number of files to select for deep research.
        ctx: Context with token, process_monitor, etc.
        metadata_context_fields: Which metadata fields to include in document context.

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

    batches = [
        all_documents[i : i + batch_size]
        for i in range(0, len(all_documents), batch_size)
    ]
    total_batches = len(batches)
    logger.info(
        "Created %d batches of up to %d documents each", total_batches, batch_size
    )

    all_selected_ids: List[str] = []
    all_reasoning: List[str] = []

    for batch_num, batch_docs in enumerate(batches, 1):
        selection, _ = select_relevant_files_from_batch(
            research_statement=research_statement,
            batch_documents=batch_docs,
            batch_number=batch_num,
            total_batches=total_batches,
            ctx=ctx,
            metadata_context_fields=metadata_context_fields,
        )
        all_selected_ids.extend(selection["selected_ids"])
        if selection["reasoning"]:
            all_reasoning.append(f"Batch {batch_num}: {selection['reasoning']}")

    deduped_ids: List[str] = []
    seen_ids: Set[str] = set()
    for doc_id in all_selected_ids:
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        deduped_ids.append(doc_id)

    if len(deduped_ids) > max_selected_files:
        logger.info(
            "Limiting selected files from %d to %d (max_selected_files)",
            len(deduped_ids),
            max_selected_files,
        )
        deduped_ids = deduped_ids[:max_selected_files]

    combined_reasoning = (
        " | ".join(all_reasoning) if all_reasoning else "File selection"
    )

    logger.info(
        "Catalog selection complete: %d files selected for %s",
        len(all_selected_ids),
        db_source,
    )

    return deduped_ids, combined_reasoning


def _validate_unified_decisions(
    raw_decisions: List[Dict[str, Any]],
    valid_doc_ids: Set[str],
    batch_documents: List[DocumentMetadata],
) -> List[DocumentDecision]:
    """Validate and normalize 3-way decisions from the LLM response.

    Args:
        raw_decisions: Raw decisions from LLM response.
        valid_doc_ids: Document IDs that were sent to the LLM.
        batch_documents: Documents in the current batch.

    Returns:
        Validated list of per-document decisions.
    """
    validated: List[DocumentDecision] = []
    seen_ids: Set[str] = set()

    valid_statuses = {"answered", "irrelevant", "needs_deep_research"}

    for d in raw_decisions:
        doc_id = d.get("document_id", "")
        status = d.get("status", "")

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

        finding = d.get("finding")
        page_reference = d.get("page_reference") if status == "answered" else None

        # If status is "answered" but no finding provided, switch to needs_deep_research
        if status == "answered" and not finding:
            logger.warning(
                "Doc %s marked 'answered' but no finding provided, "
                "switching to needs_deep_research",
                doc_id,
            )
            status = "needs_deep_research"
            finding = "No finding provided - requires full document research"
            page_reference = None
        elif status == "needs_deep_research" and not finding:
            finding = "No finding provided"
        elif status == "irrelevant" and not finding:
            finding = "Not relevant to query"

        validated.append(
            {
                "document_id": doc_id,
                "status": status,
                "finding": finding,
                "page_reference": page_reference,
            }
        )

    for doc in batch_documents:
        if doc["document_id"] not in seen_ids:
            logger.warning(
                "Document %s missing from LLM response, "
                "defaulting to needs_deep_research",
                doc["document_id"],
            )
            validated.append(
                {
                    "document_id": doc["document_id"],
                    "status": "needs_deep_research",
                    "finding": "No finding provided",
                    "page_reference": None,
                }
            )

    return validated


def _build_findings_from_decisions(
    decisions: List[DocumentDecision],
    documents: List[DocumentMetadata],
    db_source: str,
) -> FindingsList:
    """Build unified findings list from metadata decisions.

    Args:
        decisions: Per-document decisions with 3-way status.
        documents: Full document metadata list.
        db_source: Database identifier.

    Returns:
        List of Finding objects in unified format.
    """
    doc_lookup = {doc["document_id"]: doc for doc in documents}
    doc_order = {
        doc["document_id"]: doc.get("document_index", idx)
        for idx, doc in enumerate(documents, 1)
    }

    relevant_decisions = [
        d
        for d in decisions
        if d.get("status") in {"answered", "needs_deep_research"}
        and d.get("finding")
    ]

    sorted_decisions = sorted(
        relevant_decisions,
        key=lambda d: doc_order.get(d.get("document_id", ""), float("inf")),
    )

    findings: FindingsList = []

    for decision in sorted_decisions:
        doc_id = decision["document_id"]
        doc = doc_lookup.get(doc_id)

        if not doc:
            logger.warning("Document not found for decision: %s", doc_id)
            continue

        findings.append({
            "document_id": doc_id,
            "document_name": doc["document_name"],
            "file_name": doc.get("file_name") or doc["document_name"],
            "file_link": doc.get("file_name") or "",
            "page": decision.get("page_reference"),
            "finding": decision.get("finding", ""),
            "source": "metadata",
            "db_source": db_source,
        })

    return findings


def _format_unified_response(
    decisions: List[DocumentDecision],
    documents: List[DocumentMetadata],
) -> str:
    """Format decisions into structured research response text.

    Args:
        decisions: Per-document decisions.
        documents: Full document metadata list.

    Returns:
        Formatted research response string.
    """
    doc_lookup = {doc["document_id"]: doc for doc in documents}
    doc_order = {
        doc["document_id"]: doc.get("document_index", idx)
        for idx, doc in enumerate(documents, 1)
    }

    sorted_decisions = sorted(
        decisions,
        key=lambda d: doc_order.get(d.get("document_id", ""), float("inf")),
    )

    lines: List[str] = ["File # | Filename | Status | Finding | Page"]

    for decision in sorted_decisions:
        doc_id = decision.get("document_id")
        doc = doc_lookup.get(doc_id)
        if not doc:
            logger.warning("Document not found for formatting: %s", doc_id)
            continue

        file_index = doc_order.get(doc_id)
        index_label = str(file_index) if file_index is not None else "-"

        filename = doc.get("file_name") or doc.get("document_name") or doc_id or "-"
        status = decision.get("status", "")
        finding = decision.get("finding") or ""
        page_ref = decision.get("page_reference")
        page_label = str(page_ref) if page_ref is not None else "-"

        lines.append(
            f"File {index_label} | {filename} | {status} | {finding} | {page_label}"
        )

    if len(lines) == 1:
        return ""

    return "\n".join(lines)


def process_batch_unified(
    research_statement: str,
    batch_documents: List[DocumentMetadata],
    batch_number: int,
    total_batches: int,
    ctx: MetadataContext,
    metadata_context_fields: Optional[List[str]] = None,
) -> Tuple[UnifiedBatchResult, Optional[Dict[str, Any]]]:
    """Run LLM to produce per-document decisions for a batch.

    Args:
        research_statement: The research query.
        batch_documents: Documents in this batch.
        batch_number: Current batch number (1-indexed).
        total_batches: Total number of batches.
        ctx: Context with token, process_monitor, etc.
        metadata_context_fields: Which metadata fields to include in document context.

    Returns:
        Tuple of (UnifiedBatchResult, usage_details).

    Raises:
        MetadataSubagentError: If the LLM call fails or responds unexpectedly.
    """
    logger.info(
        "Processing unified batch %d of %d (%d documents)",
        batch_number,
        total_batches,
        len(batch_documents),
    )
    usage_details = None
    valid_doc_ids: Set[str] = {doc["document_id"] for doc in batch_documents}

    try:
        system_prompt, tools, user_template = fetch_prompt_with_context(
            "subagent", "metadata_unified_findings"
        )

        formatted_docs = _format_batch_documents(batch_documents, metadata_context_fields)

        user_prompt = (
            user_template.replace("{{research_statement}}", research_statement)
            .replace("{{batch_number}}", str(batch_number))
            .replace("{{total_batches}}", str(total_batches))
            .replace("{{document_count}}", str(len(batch_documents)))
            .replace("{{batch_documents}}", formatted_docs)
        )

        model_config = config.get_model_settings(MODEL_CAPABILITY)

        result = execute_llm_call(
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

        process_monitor = ctx.get("process_monitor")
        stage_name = ctx.get("stage_name")
        if usage_details and process_monitor and stage_name:
            process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)

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
                f"Unexpected tool call '{tool_call.function.name}' "
                f"for unified batch {batch_number}"
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


def execute_unified_metadata_query(
    research_statement: str,
    db_source: str,
    query_context: Optional[MetadataContext] = None,
    mode: str = "metadata_research",
) -> UnifiedMetadataResult:
    """Query metadata and branch into file selection or metadata research.

    Args:
        research_statement: The research query/statement.
        db_source: Database source to query.
        query_context: Context dict containing OAuth token, process tracking, and
            required `query_embedding`.
        mode: "file_selection" (select files only) or "metadata_research" (answer if
            possible from metadata).

    Returns:
        UnifiedMetadataResult containing answered findings and document IDs for deep
        research.

    Raises:
        MetadataSubagentError: If the mode, config, or inputs are invalid.
    """
    ctx = query_context or {}

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

    query_embedding = ctx.get("query_embedding")
    if query_embedding is None:
        raise MetadataSubagentError(
            f"No query_embedding provided for {db_source}. "
            "Query embedding must be pre-computed by planner."
        )

    research_config = _get_research_config(db_source)
    batch_size = research_config["batch_size"]
    max_selected_files = research_config["max_selected_files"]
    metadata_context_fields = research_config["metadata_context_fields"]

    top_chunks = (
        research_config["top_chunks_in_catalog_selection"]
        if mode == "file_selection"
        else research_config["top_chunks_in_metadata_research"]
    )

    logger.info(
        "Config for %s (mode=%s): batch_size=%d, top_chunks=%d, max_selected_files=%d, "
        "metadata_context_fields=%s",
        db_source,
        mode,
        batch_size,
        top_chunks,
        max_selected_files,
        metadata_context_fields,
    )

    all_documents = fetch_all_document_metadata(db_source, query_embedding, top_chunks)

    for idx, doc in enumerate(all_documents, 1):
        doc["document_index"] = doc.get("document_index", idx)

    if not all_documents:
        return {
            "answered_findings": [],
            "needs_research_doc_ids": [],
            "irrelevant_count": 0,
            "answered_response": f"No documents found in {db_source}.",
            "findings": [],
        }

    if mode == "file_selection":
        logger.info(
            "File selection mode: selecting files from %d documents",
            len(all_documents),
        )

        selected_ids, _reasoning = process_catalog_file_selection(
            research_statement=research_statement,
            db_source=db_source,
            all_documents=all_documents,
            batch_size=batch_size,
            max_selected_files=max_selected_files,
            ctx=ctx,
            metadata_context_fields=metadata_context_fields,
        )

        logger.info(
            "File selection complete for %s: %d files selected for deep research",
            db_source,
            len(selected_ids),
        )

        return {
            "answered_findings": [],
            "needs_research_doc_ids": selected_ids,
            "irrelevant_count": len(all_documents) - len(selected_ids),
            "answered_response": "",
            "findings": [],  # File selection mode has no metadata findings
        }

    logger.info(
        "Metadata research mode: processing %d documents with 3-way decisions",
        len(all_documents),
    )

    batches = [
        all_documents[i : i + batch_size]
        for i in range(0, len(all_documents), batch_size)
    ]
    total_batches = len(batches)
    logger.info("Created %d batches for sequential processing", total_batches)

    all_decisions: List[DocumentDecision] = []

    for batch_num, batch_docs in enumerate(batches, 1):
        try:
            batch_result, _ = process_batch_unified(
                research_statement,
                batch_docs,
                batch_num,
                total_batches,
                ctx,
                metadata_context_fields=metadata_context_fields,
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

    answered_findings = [d for d in all_decisions if d.get("status") == "answered"]
    needs_research = [
        d for d in all_decisions if d.get("status") == "needs_deep_research"
    ]
    irrelevant = [d for d in all_decisions if d.get("status") == "irrelevant"]

    needs_research_doc_ids = [d["document_id"] for d in needs_research]

    logger.info(
        "Metadata research complete for %s: "
        "%d answered, %d need research, %d irrelevant",
        db_source,
        len(answered_findings),
        len(needs_research),
        len(irrelevant),
    )

    answered_response = _format_unified_response(all_decisions, all_documents)
    findings = _build_findings_from_decisions(
        all_decisions, all_documents, db_source
    )

    return {
        "answered_findings": answered_findings,
        "needs_research_doc_ids": needs_research_doc_ids,
        "irrelevant_count": len(irrelevant),
        "answered_response": answered_response,
        "findings": findings,
    }
