"""Unified types for the research retrieval system.

This module defines the core data structures used across metadata subagent,
file research subagent, database router, and summarizer.

The research flow produces Finding objects which are consolidated and
assigned reference IDs to become IndexedFinding objects for the summarizer.
"""

from typing import Dict, List, Literal, Optional, TypedDict


class Finding(TypedDict):
    """A single research finding from any source.

    This is the unified output format for both metadata and file research.
    Each finding represents one piece of information from one page of one document.

    Attributes:
        document_id: UUID of the source document.
        document_name: Human-readable document name.
        file_name: File name for display.
        file_link: Path or URL to the source file.
        page: Page number where the finding was extracted (None if not applicable).
        finding: The actual finding content/text.
        source: Whether this came from metadata (shallow) or file_research (deep).
        db_source: Database identifier (e.g., 'internal_capm').
    """

    document_id: str
    document_name: str
    file_name: str
    file_link: str
    page: Optional[int]
    finding: str
    source: Literal["metadata", "file_research"]
    db_source: str


class IndexedFinding(Finding):
    """Finding with assigned reference number for citation.

    This extends Finding with a ref_id that the summarizer uses for citations.
    The ref_id is assigned during consolidation across all databases.

    Attributes:
        ref_id: Reference number as string (e.g., "1", "2", "3").
    """

    ref_id: str


# Type aliases for clarity
FindingsList = List[Finding]
IndexedFindingsList = List[IndexedFinding]
FindingsByDatabase = Dict[str, FindingsList]
