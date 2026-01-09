"""
Database Router Module.

Routes database queries using the Cascading Retrieval Architecture with three paths:

**Path A - Selective (non-DB-wide queries):**
    - Mode: file_selection (top 1 chunk per file)
    - LLM selects files from catalog (binary yes/no)
    - Deep research ALL selected files
    - Used for targeted research queries

**Path B - DB-wide + Deep Research Approved:**
    - Mode: metadata_research (top 3 chunks per file)
    - LLM makes 3-way decisions: answered/irrelevant/needs_deep_research
    - Deep research only files that NEED it
    - Used for comprehensive research with user approval

**Path C - DB-wide + Metadata Only:**
    - Mode: metadata_research (top 3 chunks per file)
    - LLM makes 3-way decisions
    - NO deep research - files that need it noted as "requires deeper analysis"
    - Used for quick overview without extended processing

Path selection is based on clarifier flags:
    - is_db_wide: True if query requires checking ALL files
    - deep_research_approved: True if user approved extended research

Functions:
    route_query_cascading: Route query using path-dependent cascading retrieval
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from .database_metadata import DatabaseMetadataRepository, get_available_databases
from .file_research_subagent import query_file_research_sync
from .metadata_subagent import query_metadata_unified


class DatabaseRouterError(Exception):
    """Exception raised for database router errors."""


MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]

FileLink = Dict[str, str]
PageSectionRefs = Dict[int, List[int]]
SectionContentMap = Dict[str, str]
ReferenceIndex = Dict[str, Dict[str, Any]]
SubagentResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[FileLink]],
    Optional[PageSectionRefs],
    Optional[SectionContentMap],
    Optional[ReferenceIndex],
]

QueryContext = Dict[str, Any]

logger = logging.getLogger(__name__)


def _merge_file_research_response(
    file_research_result: Dict[str, Any],
    start_ref_num: int,
) -> Tuple[str, ReferenceIndex, List[FileLink]]:
    """
    Format file research result and build reference index starting at given number.

    Args:
        file_research_result: Result from file research subagent.
        start_ref_num: Starting reference number for merging.

    Returns:
        Tuple of (formatted_text, reference_index, file_links).
    """
    research_documents = file_research_result.get("documents", {})
    file_ref_index = file_research_result.get("reference_index", {})

    detailed_parts: List[str] = []
    file_links: List[FileLink] = []
    merged_ref_index: ReferenceIndex = {}

    # Re-number the reference index starting from start_ref_num
    old_to_new_ref: Dict[str, str] = {}
    new_ref_num = start_ref_num

    numeric_ref_entries: Dict[str, Dict[str, Any]] = {}
    for ref_key, ref_value in file_ref_index.items():
        ref_key_str = str(ref_key)
        if ref_key_str.isdigit():
            numeric_ref_entries[ref_key_str] = ref_value
        else:
            logger.warning(
                "Skipping non-numeric reference key from file research: %s", ref_key
            )

    for old_key in sorted(numeric_ref_entries.keys(), key=lambda x: int(x)):
        new_key = str(new_ref_num)
        old_to_new_ref[old_key] = new_key
        merged_ref_index[new_key] = numeric_ref_entries[old_key]
        new_ref_num += 1

    for doc_name, page_data in research_documents.items():
        detailed_parts.append(f"\n## {doc_name}\n")

        for _, page_research in page_data.items():
            page_num = page_research.get("page_number", 0)
            content = page_research.get("research_content", "")
            file_link = page_research.get("file_link", "")

            # Replace old REF numbers with new ones
            for old_ref in sorted(
                old_to_new_ref.keys(), key=lambda x: int(x), reverse=True
            ):
                new_ref = old_to_new_ref[old_ref]
                content = content.replace(f"[REF:{old_ref}]", f"[REF:{new_ref}]")

            detailed_parts.append(f"**Page {page_num}:**\n{content}\n")

            if file_link and not any(
                fl.get("document_name") == doc_name for fl in file_links
            ):
                file_links.append(
                    {
                        "file_link": file_link,
                        "document_name": doc_name,
                    }
                )

    return "\n".join(detailed_parts), merged_ref_index, file_links


def route_query_cascading(
    database: str,
    token: Optional[str] = None,
    process_monitor: Optional[Any] = None,
    query_stage_name: Optional[str] = None,
    query_context: Optional[QueryContext] = None,
) -> SubagentResult:
    """
    Route a database query using the cascading retrieval architecture.

    Three processing paths based on query type (from clarifier):

    **Path A - Selective (non-DB-wide, is_db_wide=False):**
        - Mode: file_selection (top 1 chunk per file)
        - LLM selects files from catalog
        - Deep research ALL selected files
        - Used for targeted research queries

    **Path B - DB-wide + Deep Research Approved (is_db_wide=True, deep_research_approved=True):**
        - Mode: metadata_research (top 3 chunks per file)
        - LLM makes 3-way decisions: answered/irrelevant/needs_deep_research
        - Deep research only files that NEED it
        - Used for comprehensive research with user approval

    **Path C - DB-wide + Metadata Only (is_db_wide=True, deep_research_approved=False):**
        - Mode: metadata_research (top 3 chunks per file)
        - LLM makes 3-way decisions
        - NO deep research - files that need it noted as "requires deeper analysis"
        - Used for quick overview without extended processing

    Args:
        database: The database identifier (e.g., 'internal_capm', 'external_ey').
        token: Authentication token for API access.
        process_monitor: Process monitor instance for tracking.
        query_stage_name: The specific stage name for this query instance.
        query_context: Context dict containing:
            - research_statement: The research query/statement
            - query_embedding: Pre-computed query embedding from planner
            - is_db_wide: True if query requires checking ALL files (from clarifier)
            - deep_research_approved: True if user approved extended research

    Returns:
        SubagentResult tuple containing:
            - Query results dict with detailed_research, status_summary
            - Optional list of document IDs
            - Optional list of file links with document names
            - Optional page/section references
            - Optional section content map
            - Optional reference index (merged from metadata + file research)
    """
    if query_context is None:
        raise DatabaseRouterError("query_context is required for cascading retrieval")

    research_statement = query_context.get("research_statement", "")
    query_embedding = query_context.get("query_embedding")
    is_db_wide = query_context.get("is_db_wide", False)
    deep_research_approved = query_context.get("deep_research_approved", False)

    # Check if this database allows DB-wide deep research (from registry config)
    try:
        research_config = DatabaseMetadataRepository().get_research_config(database)
        enable_db_wide_deep_research = research_config.get(
            "enable_db_wide_deep_research", True
        )
    except Exception as exc:
        logger.warning(
            "Could not load research_config for %s, defaulting to enable_db_wide_deep_research=True: %s",
            database,
            exc,
        )
        enable_db_wide_deep_research = True

    # Determine processing path
    # Path A: Selective (non-DB-wide) -> file_selection mode -> deep research ALL selected
    # Path B: DB-wide + approved + enabled -> metadata_research mode -> deep research flagged files
    # Path C: DB-wide + (not approved OR not enabled) -> metadata_research mode -> no deep research
    if is_db_wide:
        if deep_research_approved and enable_db_wide_deep_research:
            path = "B"  # DB-wide + deep research approved + enabled
            mode = "metadata_research"
        else:
            path = "C"  # DB-wide + metadata only (no deep research)
            mode = "metadata_research"
    else:
        path = "A"  # Selective (file selection → deep research ALL)
        mode = "file_selection"

    logger.info(
        "Cascading query to %s: Path %s (is_db_wide=%s, deep_research_approved=%s, "
        "enable_db_wide_deep_research=%s, mode=%s)",
        database,
        path,
        is_db_wide,
        deep_research_approved,
        enable_db_wide_deep_research,
        mode,
    )
    stage_name = query_stage_name or f"db_cascading_{database}"

    if database not in get_available_databases():
        logger.error("Unknown database: %s", database)
        if process_monitor:
            process_monitor.add_stage_details(
                stage_name, error=f"Unknown database: {database}"
            )
        raise DatabaseRouterError(f"Unknown database: {database}")

    try:
        # =================================================================
        # Stage 1: Metadata Processing (mode-dependent)
        # =================================================================
        logger.info("Stage 1: Metadata query for %s (mode=%s)", database, mode)

        unified_result = query_metadata_unified(
            research_statement=research_statement,
            db_source=database,
            query_context={
                "token": token,
                "process_monitor": process_monitor,
                "stage_name": f"{stage_name}_metadata",
                "query_embedding": query_embedding,
            },
            mode=mode,
        )

        answered_response = unified_result.get("answered_response", "")
        answered_reference_index = unified_result.get("answered_reference_index", {})
        needs_research_doc_ids = unified_result.get("needs_research_doc_ids", [])
        answered_count = len(unified_result.get("answered_findings", []))
        irrelevant_count = unified_result.get("irrelevant_count", 0)

        logger.info(
            "Stage 1 complete (Path %s): %d answered, %d need research, %d irrelevant",
            path,
            answered_count,
            len(needs_research_doc_ids),
            irrelevant_count,
        )

        if process_monitor:
            process_monitor.add_stage_details(
                f"{stage_name}_metadata",
                path=path,
                mode=mode,
                answered_count=answered_count,
                needs_research_count=len(needs_research_doc_ids),
                irrelevant_count=irrelevant_count,
            )

        # Initialize response components from metadata
        combined_parts: List[str] = []
        combined_ref_index: ReferenceIndex = dict(answered_reference_index)
        all_file_links: List[FileLink] = []
        all_doc_ids: List[str] = []

        # Add metadata response if any documents were answered (Path B/C only)
        if answered_response:
            combined_parts.append(answered_response)
            # Collect doc IDs from answered findings
            for finding in unified_result.get("answered_findings", []):
                doc_id = finding.get("document_id")
                if doc_id and doc_id not in all_doc_ids:
                    all_doc_ids.append(doc_id)

        # =================================================================
        # Stage 2: File Research (path-dependent)
        # =================================================================
        # Path A: Deep research ALL selected files
        # Path B: Deep research only files that NEED it
        # Path C: NO deep research (metadata only)

        if path == "C":
            # Path C: Metadata only - no deep research
            if needs_research_doc_ids:
                logger.info(
                    "Path C: Skipping deep research for %d documents in %s (metadata only)",
                    len(needs_research_doc_ids),
                    database,
                )
                # Note which files would have needed deeper analysis
                combined_parts.append(
                    f"\n\n*Note: {len(needs_research_doc_ids)} document(s) may contain "
                    "additional relevant information that requires deeper analysis.*"
                )
        elif needs_research_doc_ids:
            # Path A or B: Deep research needed
            research_label = "ALL selected" if path == "A" else "flagged"
            logger.info(
                "Stage 2: Deep research on %d %s documents in %s",
                len(needs_research_doc_ids),
                research_label,
                database,
            )

            file_research_result = query_file_research_sync(
                research_statement=research_statement,
                document_ids=needs_research_doc_ids,
                db_source=database,
                research_context={
                    "token": token,
                    "process_monitor": process_monitor,
                    "stage_name": f"{stage_name}_file_research",
                    "query_embedding": query_embedding,  # For similarity-based chunk retrieval
                },
            )

            if process_monitor:
                process_monitor.add_stage_details(
                    f"{stage_name}_file_research",
                    documents_researched=len(needs_research_doc_ids),
                    research_type=research_label,
                )

            # Merge file research with continuing reference numbers
            start_ref_num = len(combined_ref_index) + 1
            file_text, file_refs, file_links = _merge_file_research_response(
                file_research_result, start_ref_num
            )

            if file_text.strip():
                if path == "A":
                    # Path A: File research is the primary content
                    combined_parts.append(file_text)
                else:
                    # Path B: File research supplements metadata findings
                    combined_parts.append(
                        "\n---\n**Additional Deep Research:**\n" + file_text
                    )

            combined_ref_index.update(file_refs)
            all_file_links.extend(file_links)
            all_doc_ids.extend(needs_research_doc_ids)
        else:
            logger.info("No file research needed for %s", database)

        # =================================================================
        # Build Final Response
        # =================================================================
        if not combined_parts:
            detailed_research = f"No relevant information found in {database}."
        else:
            detailed_research = "\n\n".join(combined_parts)

        # Build status summary based on path
        status_parts = []
        if path == "A":
            if needs_research_doc_ids:
                status_parts.append(f"{len(needs_research_doc_ids)} files researched")
            if irrelevant_count > 0:
                status_parts.append(f"{irrelevant_count} not relevant")
        else:
            # Path B or C
            if answered_count > 0:
                status_parts.append(f"{answered_count} answered from metadata")
            if path == "B" and needs_research_doc_ids:
                status_parts.append(f"{len(needs_research_doc_ids)} from deep research")
            elif path == "C" and needs_research_doc_ids:
                status_parts.append(
                    f"{len(needs_research_doc_ids)} need deeper analysis"
                )
            if irrelevant_count > 0:
                status_parts.append(f"{irrelevant_count} not relevant")

        status_summary = (
            f"✓ {database}: " + ", ".join(status_parts)
            if status_parts
            else f"✓ Queried {database}"
        )

        return (
            {
                "detailed_research": detailed_research,
                "status_summary": status_summary,
            },
            all_doc_ids if all_doc_ids else None,
            all_file_links if all_file_links else None,
            None,
            None,
            combined_ref_index if combined_ref_index else None,
        )

    except Exception as exc:
        error_msg = f"Error in cascading query for {database}: {exc}"
        logger.error(error_msg, exc_info=True)

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)

        raise DatabaseRouterError(error_msg) from exc
