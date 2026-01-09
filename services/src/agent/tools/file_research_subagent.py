"""
File Research Subagent for Universal Cascading Retrieval Architecture.

Stage 2 of the cascading retrieval process:
1. Receive document IDs from Stage 1 (metadata subagent)
2. Fetch chunks using similarity search (query_embedding required)
3. Process documents in parallel - each document synthesized by LLM
4. Return page-based research findings with citations

Chunk Retrieval:
Similarity-based retrieval is REQUIRED. The query_embedding must be provided
in the context. Chunks are fetched by embedding similarity within each
document, then sorted by page order for coherent presentation.

This subagent is UNIVERSAL - works for ALL databases (internal and external)
by querying the unified document tables.

Functions:
    fetch_document_chunks: Fetch chunks using similarity search
    load_file_research_config: Load prompt configuration from PostgreSQL
    format_document_for_llm: Format document chunks for LLM prompt
    synthesize_single_document: LLM synthesis for a single document
    query_file_research_sync: Main entry point for Stage 2 file research

Classes:
    ChunkData: TypedDict for chunk data from database
    DocumentChunks: TypedDict for document with chunks
    PageResearch: TypedDict for page-level research findings
    DocumentResearch: TypedDict for document research output
    FileResearchResult: TypedDict for full subagent result
    FileResearchError: Exception for file research errors
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from sqlalchemy import text

from ...utils.env_config import config
from ...utils.prompt_loader import get_prompt
from ...connections.postgres import get_session
from ...connections.llm import call_llm
from .database_metadata import DatabaseMetadataRepository

logger = logging.getLogger(__name__)


class FileResearchError(Exception):
    """Exception raised for file research errors."""


MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.2
DEFAULT_MAX_CHUNKS_PER_FILE = 20
DEFAULT_MAX_PARALLEL_FILES = 5

SynthesisContext = Dict[str, Any]
ResearchContext = Dict[str, Any]


class ChunkData(TypedDict):
    """Chunk data from iris_document_chunks."""

    chunk_id: str
    chunk_number: int
    chunk_content: str
    primary_section_name: Optional[str]
    subsection_name: Optional[str]
    hierarchy_path: Optional[str]
    page_number: Optional[int]
    page_reference: Optional[str]


class DocumentChunks(TypedDict):
    """Document with all its chunks for research."""

    document_id: str
    document_name: str
    file_name: Optional[str]
    chunks: List[ChunkData]


class PageResearch(TypedDict):
    """Research finding for a specific page."""

    page_number: int
    research_content: str
    file_link: str
    file_name: str


class DocumentResearch(TypedDict):
    """Research output for a single document."""

    document_name: str
    file_link: str
    status_summary: str
    page_research: List[PageResearch]


class FileResearchResult(TypedDict):
    """Result structure from file research subagent."""

    documents: Dict[str, Dict[str, PageResearch]]
    status_summary: str
    reference_index: Dict[str, Dict[str, Any]]
    db_source: str


def fetch_document_chunks(
    document_ids: List[str],
    db_source: str,
    max_chunks_per_file: int = DEFAULT_MAX_CHUNKS_PER_FILE,
    query_embedding: List[float] = None,
) -> List[DocumentChunks]:
    """
    Fetch chunks for specified documents from iris_document_chunks.

    Uses similarity search to find the most relevant chunks within each
    document. Chunks are ordered by similarity to the query embedding,
    then sorted by page order for coherent presentation.

    Args:
        document_ids: List of document UUIDs to fetch chunks for.
        db_source: Database source for filtering.
        max_chunks_per_file: Maximum chunks to fetch per document.
        query_embedding: Embedding vector for similarity search (REQUIRED).

    Returns:
        List of DocumentChunks with all chunk data.

    Raises:
        FileResearchError: If query_embedding is not provided or document fetch fails.
    """
    if not query_embedding:
        raise FileResearchError(
            "query_embedding is required for chunk retrieval. "
            "Similarity-based search is mandatory - no fallback to sequential ordering."
        )

    logger.info(
        "Fetching chunks by similarity for %d documents from %s",
        len(document_ids),
        db_source,
    )

    documents: List[DocumentChunks] = []
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    try:
        with get_session() as session:
            for doc_id in document_ids:
                doc_result = session.execute(
                    text(
                        """
                        SELECT id, document_name, file_name
                        FROM iris_document_metadata
                        WHERE id = :doc_id AND db_source = :db_source
                    """
                    ),
                    {"doc_id": doc_id, "db_source": db_source},
                )
                doc_row = doc_result.mappings().first()

                if not doc_row:
                    raise FileResearchError(
                        f"Document {doc_id} not found in {db_source}"
                    )

                # Similarity-based retrieval (top-K by relevance)
                chunk_result = session.execute(
                    text(
                        """
                        SELECT
                            id,
                            chunk_number,
                            chunk_content,
                            primary_section_name,
                            subsection_name,
                            hierarchy_path,
                            page_number,
                            1 - (chunk_embedding <=> CAST(:embedding AS halfvec)) AS similarity
                        FROM iris_document_chunks
                        WHERE document_id = :doc_id
                          AND db_source = :db_source
                          AND chunk_embedding IS NOT NULL
                        ORDER BY chunk_embedding <=> CAST(:embedding AS halfvec)
                        LIMIT :limit
                    """
                    ),
                    {
                        "doc_id": doc_id,
                        "db_source": db_source,
                        "embedding": embedding_str,
                        "limit": max_chunks_per_file,
                    },
                )

                chunk_rows = chunk_result.mappings().all()

                # Sort by page_number for display
                # (keeps them in logical document order after filtering by relevance)
                chunk_rows = sorted(
                    chunk_rows,
                    key=lambda r: (r["page_number"] or 0, r["chunk_number"]),
                )

                chunks: List[ChunkData] = []
                for chunk_row in chunk_rows:
                    chunks.append(
                        {
                            "chunk_id": str(chunk_row["id"]),
                            "chunk_number": chunk_row["chunk_number"],
                            "chunk_content": chunk_row["chunk_content"],
                            "primary_section_name": chunk_row["primary_section_name"],
                            "subsection_name": chunk_row["subsection_name"],
                            "hierarchy_path": chunk_row["hierarchy_path"],
                            "page_number": chunk_row["page_number"],
                            "page_reference": chunk_row[
                                "hierarchy_path"
                            ],  # Use hierarchy_path
                        }
                    )

                documents.append(
                    {
                        "document_id": str(doc_row["id"]),
                        "document_name": doc_row["document_name"],
                        "file_name": doc_row["file_name"],
                        "chunks": chunks,
                    }
                )

            logger.info(
                "Retrieved chunks for %d documents from %s", len(documents), db_source
            )

    except FileResearchError:
        raise
    except Exception as exc:
        raise FileResearchError(
            f"Error fetching chunks for {db_source}: {exc}"
        ) from exc

    return documents


def load_file_research_config() -> Dict[str, Any]:
    """
    Load file research configuration from PostgreSQL.

    Returns:
        Configuration dictionary with system prompt, tools, and user_prompt.

    Raises:
        ValueError: If prompt not found in database.
        ValueError: If user_prompt not found in database.
    """
    prompt = get_prompt("subagent", "file_research")
    if not prompt:
        raise ValueError("Prompt not found: subagent/file_research")

    user_prompt = prompt.get("user_prompt")
    if not user_prompt:
        raise ValueError(
            "user_prompt not found in database for subagent/file_research. "
            "Please ensure the prompt is configured in the prompts table."
        )

    return {
        "system_prompt": prompt.get("system_prompt", ""),
        "user_prompt": user_prompt,
        "tools": (
            [prompt.get("tool_definition")] if prompt.get("tool_definition") else []
        ),
    }


def format_document_for_llm(document: DocumentChunks) -> str:
    """
    Format a document's chunks for LLM research synthesis.

    Args:
        document: Document with all its chunks.

    Returns:
        Formatted string for LLM prompt.
    """
    formatted = f"# {document['document_name']}\n\n"

    if not document["chunks"]:
        formatted += "No content available.\n"
        return formatted

    page_chunks: Dict[int, List[ChunkData]] = {}
    for chunk in document["chunks"]:
        page = chunk.get("page_number") or 0
        if page not in page_chunks:
            page_chunks[page] = []
        page_chunks[page].append(chunk)

    for page in sorted(page_chunks.keys()):
        chunks = page_chunks[page]
        formatted += f"\n## Page {page}\n\n"

        for chunk in chunks:
            if chunk.get("hierarchy_path"):
                formatted += f"*{chunk['hierarchy_path']}*\n\n"
            elif chunk.get("primary_section_name"):
                formatted += f"*{chunk['primary_section_name']}"
                if chunk.get("subsection_name"):
                    formatted += f" > {chunk['subsection_name']}"
                formatted += "*\n\n"

            formatted += f"{chunk['chunk_content']}\n\n"
            formatted += "---\n"

    return formatted


def _build_llm_messages(
    system_prompt: str,
    user_prompt: str,
) -> List[Dict[str, str]]:
    """
    Build message list for LLM call.

    Args:
        system_prompt: The system prompt content.
        user_prompt: The user prompt content from database.

    Returns:
        List of message dicts for LLM.
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _parse_tool_response(
    result: Any,
    file_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Parse LLM tool call response.

    Args:
        result: The result from call_llm (may be tuple or response object).
        file_name: File name for page research entries.

    Returns:
        Parsed arguments dict if tool call found, None otherwise.
    """
    if isinstance(result, tuple) and len(result) == 2:
        response, _ = result
    else:
        response = result

    if not (
        response
        and hasattr(response, "choices")
        and response.choices
        and response.choices[0].message
        and response.choices[0].message.tool_calls
    ):
        return None

    tool_call = response.choices[0].message.tool_calls[0]
    if tool_call.function.name != "extract_page_research":
        return None

    arguments = json.loads(tool_call.function.arguments)

    page_research: List[PageResearch] = []
    for page_item in arguments.get("page_research", []):
        page_research.append(
            {
                "page_number": page_item.get("page_number", 0),
                "research_content": page_item.get("research_content", ""),
                "file_link": file_name,
                "file_name": file_name,
            }
        )

    return {
        "page_research": page_research,
        "status_summary": arguments.get("status_summary"),
    }


def _track_llm_usage(
    result: Any,
    context: SynthesisContext,
) -> None:
    """
    Track LLM usage if process monitor available.

    Args:
        result: The result from call_llm.
        context: Synthesis context with process_monitor and stage_name.
    """
    process_monitor = context.get("process_monitor")
    stage_name = context.get("stage_name")

    if isinstance(result, tuple) and len(result) == 2:
        _, usage_details = result
        if usage_details and process_monitor and stage_name:
            process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)


def synthesize_single_document(
    research_statement: str,
    document: DocumentChunks,
    synthesis_context: Optional[SynthesisContext] = None,
) -> DocumentResearch:
    """
    Synthesize research findings for a single document using LLM.

    Args:
        research_statement: The research query.
        document: Document with chunks to analyze.
        synthesis_context: Optional context dict containing token, db_source,
            process_monitor, and stage_name.

    Returns:
        DocumentResearch with page-level findings.

    Raises:
        FileResearchError: If synthesis fails or no valid response from LLM.
    """
    ctx = synthesis_context or {}
    doc_name = document["document_name"]
    file_name = document.get("file_name") or doc_name
    logger.info(
        "Synthesizing research for %s from %s",
        doc_name,
        ctx.get("db_source", "unknown"),
    )

    if not document["chunks"]:
        raise FileResearchError(f"No content available for document {doc_name}")

    try:
        prompt_config = load_file_research_config()
        document_content = format_document_for_llm(document)

        system_prompt = (
            prompt_config.get("system_prompt", "")
            .replace("{{research_statement}}", research_statement)
            .replace("{{document_content}}", document_content)
            .replace("{{document_name}}", doc_name)
        )

        user_prompt = (
            prompt_config.get("user_prompt", "")
            .replace("{{research_statement}}", research_statement)
            .replace("{{document_content}}", document_content)
            .replace("{{document_name}}", doc_name)
        )

        model_config = config.get_model_config(MODEL_CAPABILITY)

        result = call_llm(
            oauth_token=ctx.get("token") or "placeholder_token",
            model=model_config["name"],
            messages=_build_llm_messages(system_prompt, user_prompt),
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            tools=prompt_config.get("tools", []),
            tool_choice={
                "type": "function",
                "function": {"name": "extract_page_research"},
            },
            stream=False,
            prompt_token_cost=model_config["prompt_token_cost"],
            completion_token_cost=model_config["completion_token_cost"],
        )

        _track_llm_usage(result, ctx)

        parsed = _parse_tool_response(result, file_name)
        if not parsed:
            raise FileResearchError(
                f"No valid tool response from LLM for document {doc_name}"
            )

        return {
            "document_name": doc_name,
            "file_link": file_name,
            "status_summary": parsed.get("status_summary") or f"Analyzed {doc_name}",
            "page_research": parsed.get("page_research", []),
        }

    except FileResearchError:
        raise
    except Exception as exc:
        raise FileResearchError(
            f"Error synthesizing research for {doc_name}: {exc}"
        ) from exc


def _build_structured_output(
    document_results: List[DocumentResearch],
) -> Tuple[Dict[str, Dict[str, PageResearch]], Dict[str, Dict[str, Any]]]:
    """
    Build structured output from document research results.

    Args:
        document_results: List of DocumentResearch dicts.

    Returns:
        Tuple of (structured_output, reference_index) dicts.
    """
    structured_output: Dict[str, Dict[str, PageResearch]] = {}
    reference_index: Dict[str, Dict[str, Any]] = {}
    ref_counter = 1

    for result in document_results:
        doc_name = result["document_name"]
        page_research = result.get("page_research", [])

        if page_research and not result["status_summary"].startswith("Error"):
            doc_output: Dict[str, PageResearch] = {}

            for page_item in sorted(
                page_research, key=lambda x: x.get("page_number", 0)
            ):
                page_number = page_item.get("page_number", 0)
                ref_key = str(ref_counter)

                file_link = page_item.get("file_link", "") or result.get(
                    "file_link", ""
                )
                file_name = page_item.get("file_name", "") or result.get(
                    "file_link", ""
                )
                content = page_item.get("research_content", "") or ""
                research_content = (
                    f"{content.rstrip()} [REF:{ref_key}]"
                    if content
                    else f"[REF:{ref_key}]"
                )

                doc_output[f"page_{page_number}"] = {
                    "page_number": page_number,
                    "research_content": research_content,
                    "file_link": file_link,
                    "file_name": file_name,
                }

                reference_index[ref_key] = {
                    "doc_name": doc_name,
                    "page": page_number,
                    "file_link": file_link,
                    "file_name": file_name,
                    "source_filename": doc_name,
                    "highlight_text": "",
                }

                ref_counter += 1

            if doc_output:
                structured_output[doc_name] = doc_output

    return structured_output, reference_index


def _build_status_summary(
    structured_output: Dict[str, Dict[str, PageResearch]],
    db_source: str,
) -> str:
    """
    Build status summary string.

    Args:
        structured_output: Dict of document research output.
        db_source: Database source identifier.

    Returns:
        Human-readable status summary.
    """
    if not structured_output:
        return f"No relevant information found in {db_source} documents"

    total_pages = sum(len(doc_data) for doc_data in structured_output.values())
    return (
        f"Found relevant information in {len(structured_output)} "
        f"document(s) across {total_pages} page(s)"
    )


def _process_documents_parallel(
    research_statement: str,
    documents: List[DocumentChunks],
    db_source: str,
    ctx: ResearchContext,
    research_config: Dict[str, Any],
) -> List[DocumentResearch]:
    """
    Process documents in parallel using ThreadPoolExecutor.

    Args:
        research_statement: The research query.
        documents: List of documents with chunks.
        db_source: Database source identifier.
        ctx: Research context with token, process_monitor, stage_name.
        research_config: Research configuration dict.

    Returns:
        List of DocumentResearch results.
    """
    synthesis_ctx: SynthesisContext = {
        "token": ctx.get("token"),
        "db_source": db_source,
        "process_monitor": ctx.get("process_monitor"),
        "stage_name": ctx.get("stage_name"),
    }

    max_parallel = research_config.get("max_parallel_files", DEFAULT_MAX_PARALLEL_FILES)
    results: List[DocumentResearch] = []

    with ThreadPoolExecutor(max_workers=min(len(documents), max_parallel)) as executor:
        future_to_doc = {
            executor.submit(
                synthesize_single_document,
                research_statement,
                doc,
                synthesis_ctx,
            ): doc
            for doc in documents
        }

        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                results.append(future.result())
                logger.info("Completed research for: %s", doc["document_name"])
            except Exception as exc:
                # Re-raise - no fallback to degraded results
                raise FileResearchError(
                    f"Failed to process document {doc.get('document_name')}: {exc}"
                ) from exc

    return results


def query_file_research_sync(
    research_statement: str,
    document_ids: List[str],
    db_source: str,
    research_context: Optional[ResearchContext] = None,
) -> FileResearchResult:
    """
    Stage 2: Deep research on selected documents.

    This is the main entry point for the File Research Subagent.

    Uses similarity-based chunk retrieval. The query_embedding MUST be provided
    in the research_context. Chunks are fetched by embedding similarity,
    then sorted by page order for coherent presentation.

    Args:
        research_statement: The research query/statement.
        document_ids: List of document UUIDs to research (from Stage 1).
        db_source: Database source (e.g., 'internal_capm', 'external_ey').
        research_context: Context dict containing:
            - token: OAuth token for API calls
            - process_monitor: For tracking
            - stage_name: For tracking
            - query_embedding: REQUIRED embedding for similarity-based retrieval

    Returns:
        FileResearchResult containing documents, status_summary, reference_index,
        and db_source.

    Raises:
        FileResearchError: If document_ids is empty, query_embedding missing,
            or any document fails to process.
    """
    ctx = research_context or {}
    query_embedding = ctx.get("query_embedding")

    if not document_ids:
        raise FileResearchError("No document_ids provided for file research")

    if not query_embedding:
        raise FileResearchError(
            "query_embedding is required in research_context for file research. "
            "Similarity-based retrieval is mandatory."
        )

    logger.info(
        "Starting file research for %d documents in %s",
        len(document_ids),
        db_source,
    )

    research_config = DatabaseMetadataRepository().get_research_config(db_source)

    documents = fetch_document_chunks(
        document_ids=document_ids,
        db_source=db_source,
        max_chunks_per_file=research_config.get(
            "max_chunks_per_file", DEFAULT_MAX_CHUNKS_PER_FILE
        ),
        query_embedding=query_embedding,
    )

    if not documents:
        raise FileResearchError(
            f"No content found for any of the {len(document_ids)} selected documents in {db_source}"
        )

    document_results = _process_documents_parallel(
        research_statement, documents, db_source, ctx, research_config
    )

    structured_output, reference_index = _build_structured_output(document_results)

    logger.info(
        "File research complete for %s: %s",
        db_source,
        _build_status_summary(structured_output, db_source),
    )

    return {
        "documents": structured_output,
        "status_summary": _build_status_summary(structured_output, db_source),
        "reference_index": reference_index,
        "db_source": db_source,
    }
