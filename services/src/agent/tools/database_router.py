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
    route_query_with_cascading_retrieval: Route query using path-dependent cascading retrieval
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from .database_metadata import DatabaseMetadataCache, fetch_available_databases
from .file_research_subagent import execute_file_research_sync
from .metadata_subagent import execute_unified_metadata_query
from .research_types import Finding, FindingsList


class DatabaseRouterError(Exception):
    """Exception raised for database router errors."""


class DatabaseRouterResult(TypedDict):
    """Result structure from database router."""

    findings: FindingsList
    status_summary: str
    path: str
    needs_deeper_analysis_count: int  # For Path C: files that would need deep research


QueryContext = Dict[str, Any]

logger = logging.getLogger(__name__)


def route_query_with_cascading_retrieval(
    database: str,
    token: Optional[str] = None,
    process_monitor: Optional[Any] = None,
    query_stage_name: Optional[str] = None,
    query_context: Optional[QueryContext] = None,
) -> DatabaseRouterResult:
    """Route a database query using the cascading retrieval architecture.

    Paths:
        A (selective): File selection mode; deep-research all selected files.
        B (DB-wide + approved): Metadata mode; deep-research only flagged files.
        C (DB-wide + metadata only): Metadata mode; no deep research.

    Args:
        database: Database identifier (for example, 'internal_capm').
        token: Authentication token for downstream services.
        process_monitor: Optional monitor for reporting stage progress.
        query_stage_name: Optional stage name for instrumentation.
        query_context: Query metadata with `research_statement`, `query_embedding`,
            `is_db_wide`, and `deep_research_approved`.

    Returns:
        DatabaseRouterResult with unified findings list, status summary, and path info.

    Raises:
        DatabaseRouterError: If the query context is missing or the database is
            unknown, or when routing fails.
    """
    if query_context is None:
        raise DatabaseRouterError("query_context is required for cascading retrieval")

    research_statement = query_context.get("research_statement", "")
    query_embedding = query_context.get("query_embedding")
    is_db_wide = query_context.get("is_db_wide", False)
    deep_research_approved = query_context.get("deep_research_approved", False)

    research_config = DatabaseMetadataCache().get_research_config(database)
    enable_db_wide_deep_research = research_config["enable_db_wide_deep_research"]

    if is_db_wide:
        if deep_research_approved and enable_db_wide_deep_research:
            path = "B"
            mode = "metadata_research"
        else:
            path = "C"
            mode = "metadata_research"
    else:
        path = "A"
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

    if database not in fetch_available_databases():
        logger.error("Unknown database: %s", database)
        if process_monitor:
            process_monitor.add_stage_details(
                stage_name, error=f"Unknown database: {database}"
            )
        raise DatabaseRouterError(f"Unknown database: {database}")

    try:
        logger.info("Stage 1: Metadata query for %s (mode=%s)", database, mode)

        unified_result = execute_unified_metadata_query(
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

        # Get metadata findings and doc IDs needing deep research
        metadata_findings: FindingsList = unified_result.get("findings", [])
        needs_research_doc_ids = unified_result.get("needs_research_doc_ids", [])
        irrelevant_count = unified_result.get("irrelevant_count", 0)

        # Count metadata findings by status
        answered_count = sum(
            1 for f in metadata_findings if f.get("source") == "metadata"
        )

        logger.info(
            "Stage 1 complete (Path %s): %d metadata findings, %d need research, "
            "%d irrelevant",
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

        # Start with metadata findings
        combined_findings: FindingsList = []
        needs_deeper_analysis_count = 0

        if path == "B" and needs_research_doc_ids:
            # Path B: Keep metadata findings ONLY for docs NOT getting file research
            research_doc_ids_set = set(needs_research_doc_ids)
            combined_findings = [
                f
                for f in metadata_findings
                if f.get("document_id") not in research_doc_ids_set
            ]
            logger.info(
                "Path B: Keeping %d metadata findings for answered-only docs, "
                "%d docs will get file research",
                len(combined_findings),
                len(needs_research_doc_ids),
            )
        else:
            # Path A & C: Include all metadata findings
            combined_findings = list(metadata_findings)

        if path == "C":
            # Path C: No deep research, just note how many files would need it
            if needs_research_doc_ids:
                logger.info(
                    "Path C: Skipping deep research for %d documents in %s "
                    "(metadata only)",
                    len(needs_research_doc_ids),
                    database,
                )
                needs_deeper_analysis_count = len(needs_research_doc_ids)
        elif needs_research_doc_ids:
            # Path A or B: Execute file research
            research_label = "ALL selected" if path == "A" else "flagged"
            logger.info(
                "Stage 2: Deep research on %d %s documents in %s",
                len(needs_research_doc_ids),
                research_label,
                database,
            )

            file_research_result = execute_file_research_sync(
                research_statement=research_statement,
                document_ids=needs_research_doc_ids,
                db_source=database,
                research_context={
                    "token": token,
                    "process_monitor": process_monitor,
                    "stage_name": f"{stage_name}_file_research",
                    "query_embedding": query_embedding,
                },
            )

            if process_monitor:
                process_monitor.add_stage_details(
                    f"{stage_name}_file_research",
                    documents_researched=len(needs_research_doc_ids),
                    research_type=research_label,
                )

            # Add file research findings to combined list
            file_findings: FindingsList = file_research_result.get("findings", [])
            combined_findings.extend(file_findings)

            logger.info(
                "Stage 2 complete: %d file research findings added",
                len(file_findings),
            )
        else:
            logger.info("No file research needed for %s", database)

        # Build status summary
        status_parts = []
        if path == "A":
            if needs_research_doc_ids:
                status_parts.append(f"{len(needs_research_doc_ids)} files researched")
            if irrelevant_count > 0:
                status_parts.append(f"{irrelevant_count} not relevant")
        else:
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

        return {
            "findings": combined_findings,
            "status_summary": status_summary,
            "path": path,
            "needs_deeper_analysis_count": needs_deeper_analysis_count,
        }

    except Exception as exc:
        error_msg = f"Error in cascading query for {database}: {exc}"
        logger.error(error_msg, exc_info=True)

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)

        raise DatabaseRouterError(error_msg) from exc
