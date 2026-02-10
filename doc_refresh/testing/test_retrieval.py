#!/usr/bin/env python3
"""
Deep Research Retrieval Testing for Doc Refresh.

Tests within-document retrieval with dynamic expansion from chunks to
subsections to primary sections based on page count limits.

Usage:
    python -m doc_refresh.testing.test_retrieval
    python -m doc_refresh.testing.test_retrieval --top-k 5 --evaluate
    python -m doc_refresh.testing.test_retrieval --evaluate --no-expansion
    python -m doc_refresh.testing.test_retrieval --subsection-limit 3 --section-limit 5
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doc_refresh.utils.logging_format import configure_root_logger
from doc_refresh.utils.env_config import config
from doc_refresh.connections.llm import calculate_token_cost, execute_llm_call
from doc_refresh.connections.oauth import fetch_oauth_token

# Configure logging
configure_root_logger(logging.INFO)
logger = logging.getLogger(__name__)


# QA data mapping: folder_id -> (pdf_name, qa_file_path)
QA_DATA_MAP = {
    0: ("P19-1598.pdf", "testing/docbench_data/data/0/0_qa.jsonl"),
    1: ("W18-4401.pdf", "testing/docbench_data/data/1/1_qa.jsonl"),
    2: ("P19-1164.pdf", "testing/docbench_data/data/2/2_qa.jsonl"),
    3: ("D19-1539.pdf", "testing/docbench_data/data/3/3_qa.jsonl"),
    4: ("W18-5713.pdf", "testing/docbench_data/data/4/4_qa.jsonl"),
    5: ("C18-1117.pdf", "testing/docbench_data/data/5/5_qa.jsonl"),
    6: ("2020.acl-main.408.pdf", "testing/docbench_data/data/6/6_qa.jsonl"),
    7: ("N19-1170.pdf", "testing/docbench_data/data/7/7_qa.jsonl"),
    8: ("P19-1416.pdf", "testing/docbench_data/data/8/8_qa.jsonl"),
    9: ("D18-1334.pdf", "testing/docbench_data/data/9/9_qa.jsonl"),
    10: ("N18-2084.pdf", "testing/docbench_data/data/10/10_qa.jsonl"),
    11: ("D18-1360.pdf", "testing/docbench_data/data/11/11_qa.jsonl"),
    12: ("P19-1459.pdf", "testing/docbench_data/data/12/12_qa.jsonl"),
    13: ("2020.acl-main.45.pdf", "testing/docbench_data/data/13/13_qa.jsonl"),
    14: ("P19-1033.pdf", "testing/docbench_data/data/14/14_qa.jsonl"),
    15: ("P18-1125.pdf", "testing/docbench_data/data/15/15_qa.jsonl"),
    16: ("2020.acl-main.423.pdf", "testing/docbench_data/data/16/16_qa.jsonl"),
    17: ("N19-1421.pdf", "testing/docbench_data/data/17/17_qa.jsonl"),
    18: ("D18-1003.pdf", "testing/docbench_data/data/18/18_qa.jsonl"),
    19: ("D18-1034.pdf", "testing/docbench_data/data/19/19_qa.jsonl"),
}


def _get_auth_token() -> str:
    """Return an auth token from environment or OAuth."""
    return config.OPENAI_API_KEY or fetch_oauth_token()


def _get_model_costs(model_name: str) -> Tuple[float, float]:
    """Return prompt/completion costs for a given model."""
    if model_name == config.MODEL_SMALL:
        capability = "small"
    elif model_name == config.MODEL_LARGE:
        capability = "large"
    else:
        capability = "embedding"
    settings = config.get_model_settings(capability)
    return settings["prompt_token_cost"], settings["completion_token_cost"]


def call_llm(
    auth_token: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    **kwargs: Any,
):
    """Compatibility wrapper using the shared LLM connector."""
    model_name = model or config.MODEL_LARGE
    prompt_cost, completion_cost = _get_model_costs(model_name)
    return execute_llm_call(
        auth_token,
        prompt_token_cost=prompt_cost,
        completion_token_cost=completion_cost,
        messages=messages,
        model=model_name,
        **kwargs,
    )


def create_embedding(
    auth_token: str,
    text: Any,
    model: Optional[str] = None,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    """Compatibility wrapper to generate embeddings."""
    embedding_model = model or config.MODEL_EMBEDDING
    response = execute_llm_call(
        auth_token,
        is_embedding=True,
        input=text,
        model=embedding_model,
        timeout=config.REQUEST_TIMEOUT,
    )
    token_count = 0
    if hasattr(response, "usage") and response.usage:
        token_count = getattr(response.usage, "total_tokens", 0) or 0
    prompt_cost, _ = _get_model_costs(config.MODEL_EMBEDDING)
    cost = calculate_token_cost(token_count, 0, prompt_cost, 0)
    embeddings = [item.embedding for item in response.data]
    return embeddings, {
        "model": embedding_model,
        "token_count": token_count,
        "cost": cost,
        "embedding_count": len(embeddings),
    }


# --- Data Classes ---


@dataclass
class QAPair:
    """Question-Answer pair from test data."""

    question: str
    answer: str
    qa_type: str  # text-only, multimodal-t, meta-data
    evidence: str
    document: str


@dataclass
class ChunkResult:
    """Single chunk from similarity search."""

    chunk_id: str
    document_name: str
    page_number: int
    primary_section_number: Optional[int]
    primary_section_name: Optional[str]
    subsection_number: Optional[int]
    subsection_name: Optional[str]
    hierarchy_path: Optional[str]
    chunk_content: str
    similarity: float
    primary_section_page_count: Optional[int]
    subsection_page_count: Optional[int]


def format_chunk_for_llm(
    chunk: "ChunkResult",
    include_hierarchy: bool = True,
) -> str:
    """
    Format a single chunk into standardized LLM context format.

    Format (with hierarchy):
        Page Number _ Start: X
        Page Hierarchy Path: Y
        Page Content:
        [content]
        Page Number _ End: X

    Format (without hierarchy):
        Page Number _ Start: X
        Page Content:
        [content]
        Page Number _ End: X

    Args:
        chunk: The chunk to format
        include_hierarchy: Whether to include hierarchy path header

    Returns:
        Formatted string for LLM context
    """
    page_num = chunk.page_number or 0

    if include_hierarchy:
        hierarchy = chunk.hierarchy_path or chunk.primary_section_name or "Unknown"
        return f"""Page Number _ Start: {page_num}
Page Hierarchy Path: {hierarchy}
Page Content:
{chunk.chunk_content}
Page Number _ End: {page_num}"""
    else:
        return f"""Page Number _ Start: {page_num}
Page Content:
{chunk.chunk_content}
Page Number _ End: {page_num}"""


def format_chunks_for_llm(
    chunks: List["ChunkResult"],
    include_hierarchy: bool = True,
) -> str:
    """
    Format multiple chunks into standardized LLM context format.

    Chunks are sorted by page number and separated by dividers.

    Args:
        chunks: List of chunks to format
        include_hierarchy: Whether to include hierarchy path on each chunk

    Returns:
        Combined formatted string for LLM context
    """
    sorted_chunks = sorted(chunks, key=lambda c: c.page_number or 0)
    formatted = [format_chunk_for_llm(c, include_hierarchy) for c in sorted_chunks]
    return "\n\n" + "=" * 60 + "\n\n".join(formatted) + "\n\n" + "=" * 60


def format_chunks_by_expansion_type(
    chunks: List["ChunkResult"],
    expansion_type: str,
) -> str:
    """
    Format chunks with hierarchy path conditional on expansion type.

    Hierarchy inclusion rules:
    - "full_document" or "primary_section": No hierarchy on each page
      (full context is clear from the structure)
    - "subsection_with_neighbors": Hierarchy at start of each subsection
      (helps locate within section)
    - "chunk_with_neighbors" or "none": Hierarchy on each chunk
      (individual chunks need context)
    - "gap_fill": Hierarchy on each chunk (context needed)

    Args:
        chunks: List of chunks to format (should be from same expansion context)
        expansion_type: The type of expansion used

    Returns:
        Formatted string for LLM context
    """
    sorted_chunks = sorted(chunks, key=lambda c: c.page_number or 0)

    if expansion_type in ("full_document", "primary_section"):
        # Full document/section: no hierarchy on each page
        return format_chunks_for_llm(sorted_chunks, include_hierarchy=False)

    elif expansion_type == "subsection_with_neighbors":
        # Subsection expansion: add hierarchy at start of each subsection
        formatted_parts = []
        current_subsection = None

        for chunk in sorted_chunks:
            subsection_key = (
                chunk.primary_section_number,
                chunk.subsection_number,
            )
            if subsection_key != current_subsection:
                # New subsection - include hierarchy
                current_subsection = subsection_key
                formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=True))
            else:
                # Same subsection - no hierarchy
                formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=False))

        return "\n\n" + "=" * 60 + "\n\n".join(formatted_parts) + "\n\n" + "=" * 60

    else:
        # Chunk-level or gap fill: hierarchy on each chunk
        return format_chunks_for_llm(sorted_chunks, include_hierarchy=True)


@dataclass
class ExpandedContext:
    """Context after expansion logic applied."""

    seed_chunk: ChunkResult
    expansion_type: str  # "none", "subsection", "primary_section", "full_document", etc.
    expanded_chunks: List[ChunkResult]
    total_pages: int

    @property
    def combined_content(self) -> str:
        """Combine all chunk contents in page order (raw format)."""
        sorted_chunks = sorted(self.expanded_chunks, key=lambda c: c.page_number)
        return "\n\n---\n\n".join(c.chunk_content for c in sorted_chunks)

    @property
    def formatted_content(self) -> str:
        """
        Combine all chunk contents in standardized LLM format.

        Uses expansion-type-aware formatting for conditional hierarchy inclusion.
        """
        return format_chunks_by_expansion_type(self.expanded_chunks, self.expansion_type)


@dataclass
class RetrievalResult:
    """Full retrieval result for a question."""

    question: str
    answer: str
    qa_type: str
    document_name: str
    # Raw retrieval
    top_k_chunks: List[ChunkResult]
    # After expansion
    expanded_contexts: List[ExpandedContext]
    total_pages_retrieved: int
    # Evaluation
    evidence_found: bool
    llm_explanation: str


# --- Helper Functions ---


def load_qa_pairs(qa_file_path: str, document_name: str) -> List[QAPair]:
    """Load QA pairs from JSONL file."""
    qa_pairs = []
    base_path = Path(__file__).parent.parent.parent
    full_path = base_path / qa_file_path

    if not full_path.exists():
        logger.warning(f"QA file not found: {full_path}")
        return qa_pairs

    with open(full_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                qa_pairs.append(
                    QAPair(
                        question=data["question"],
                        answer=data["answer"],
                        qa_type=data.get("type", "unknown"),
                        evidence=data.get("evidence", ""),
                        document=document_name,
                    )
                )
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse QA line: {e}")

    logger.info(f"Loaded {len(qa_pairs)} QA pairs from {qa_file_path}")
    return qa_pairs


def load_selected_qa_pairs() -> List[QAPair]:
    """Load pre-selected QA pairs from the curated JSON file."""
    qa_pairs = []
    selected_path = Path(__file__).parent / "selected_qa_pairs.json"

    if not selected_path.exists():
        logger.warning(f"Selected QA file not found: {selected_path}")
        return qa_pairs

    with open(selected_path, "r") as f:
        data = json.load(f)

    for item in data:
        qa_pairs.append(
            QAPair(
                question=item["question"],
                answer=item["answer"],
                qa_type=item.get("type", "unknown"),
                evidence=item.get("evidence", ""),
                document=item["document_name"],
            )
        )

    logger.info(f"Loaded {len(qa_pairs)} selected QA pairs")
    return qa_pairs


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


# --- Retrieval Functions ---


def retrieve_chunks(
    query: str,
    document_name: str,
    top_k: int = 5,
    auth_token: str = "",
) -> List[ChunkResult]:
    """
    Retrieve top-K chunks from a single document using embedding similarity.

    Args:
        query: The question/query text
        document_name: Document to search within
        top_k: Number of results to return
        auth_token: Auth token for embedding API

    Returns:
        List of ChunkResult with most similar chunks
    """
    # Get embedding for query
    embeddings, _ = create_embedding(auth_token, query)
    query_embedding = embeddings[0]

    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count,
            1 - (c.chunk_embedding <=> %s::halfvec) as similarity
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.chunk_embedding IS NOT NULL
        ORDER BY c.chunk_embedding <=> %s::halfvec
        LIMIT %s
    """

    params = [str(query_embedding), document_name, str(query_embedding), top_k]

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=float(row["similarity"]),
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def get_subsection_chunks(
    document_name: str,
    primary_section_number: int,
    subsection_number: int,
) -> List[ChunkResult]:
    """Get all chunks from a specific subsection."""
    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.primary_section_number = %s
            AND c.subsection_number = %s
        ORDER BY c.page_number
    """

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name, primary_section_number, subsection_number])
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=0.0,  # Not from similarity search
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def get_primary_section_chunks(
    document_name: str,
    primary_section_number: int,
) -> List[ChunkResult]:
    """Get all chunks from a specific primary section."""
    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.primary_section_number = %s
        ORDER BY c.page_number
    """

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name, primary_section_number])
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=0.0,
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def get_neighboring_subsections(
    document_name: str,
    primary_section_number: int,
    subsection_number: int,
    subsection_limit: int = 3,
) -> List[ChunkResult]:
    """
    Get chunks from neighboring subsections (leading and trailing).

    Only includes neighbors if their page count is within the subsection_limit.

    Args:
        document_name: Document to search within
        primary_section_number: Primary section containing the subsection
        subsection_number: The current subsection number
        subsection_limit: Max pages for a neighbor to be included

    Returns:
        List of chunks from qualifying neighboring subsections
    """
    # Get all subsections in this primary section with their page counts
    sql = """
        SELECT DISTINCT
            c.subsection_number,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.primary_section_number = %s
            AND c.subsection_number IS NOT NULL
        ORDER BY c.subsection_number
    """

    neighbor_chunks = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name, primary_section_number])
            subsections = cur.fetchall()

            # Find leading and trailing subsection numbers
            subsection_nums = [s["subsection_number"] for s in subsections]
            subsection_pages = {
                s["subsection_number"]: s["subsection_page_count"] for s in subsections
            }

            if subsection_number not in subsection_nums:
                return []

            idx = subsection_nums.index(subsection_number)

            # Get leading subsection (if exists and within limit)
            if idx > 0:
                leading_num = subsection_nums[idx - 1]
                leading_pages = subsection_pages.get(leading_num)
                if leading_pages and leading_pages <= subsection_limit:
                    neighbor_chunks.extend(
                        get_subsection_chunks(
                            document_name, primary_section_number, leading_num
                        )
                    )

            # Get trailing subsection (if exists and within limit)
            if idx < len(subsection_nums) - 1:
                trailing_num = subsection_nums[idx + 1]
                trailing_pages = subsection_pages.get(trailing_num)
                if trailing_pages and trailing_pages <= subsection_limit:
                    neighbor_chunks.extend(
                        get_subsection_chunks(
                            document_name, primary_section_number, trailing_num
                        )
                    )
    finally:
        conn.close()

    return neighbor_chunks


def get_neighboring_chunks(
    document_name: str,
    page_number: int,
    neighbor_limit: int = 2,
) -> List[ChunkResult]:
    """
    Get neighboring chunks by page number (leading and trailing).

    Args:
        document_name: Document to search within
        page_number: The current page number
        neighbor_limit: Number of pages to include before and after

    Returns:
        List of chunks from neighboring pages
    """
    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.page_number >= %s
            AND c.page_number <= %s
            AND c.page_number != %s
        ORDER BY c.page_number
    """

    min_page = page_number - neighbor_limit
    max_page = page_number + neighbor_limit

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name, min_page, max_page, page_number])
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=0.0,
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def get_chunks_by_page_range(
    document_name: str,
    start_page: int,
    end_page: int,
) -> List[ChunkResult]:
    """
    Get all chunks within a page range (inclusive).

    Args:
        document_name: Document to search within
        start_page: First page number (inclusive)
        end_page: Last page number (inclusive)

    Returns:
        List of chunks from the specified page range
    """
    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
            AND c.page_number >= %s
            AND c.page_number <= %s
        ORDER BY c.page_number
    """

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name, start_page, end_page])
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=0.0,
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def get_document_page_count(document_name: str) -> int:
    """
    Get the total number of pages in a document.

    Args:
        document_name: Document to query

    Returns:
        Total number of pages (unique page numbers with chunks)
    """
    sql = """
        SELECT COUNT(DISTINCT c.page_number) as page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
    """

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name])
            row = cur.fetchone()
            return row["page_count"] if row else 0
    finally:
        conn.close()


def get_all_document_chunks(document_name: str) -> List[ChunkResult]:
    """
    Get all chunks from a document, ordered by page number.

    Args:
        document_name: Document to retrieve

    Returns:
        List of all chunks in the document
    """
    sql = """
        SELECT
            c.id as chunk_id,
            m.document_name,
            c.page_number,
            c.primary_section_number,
            c.primary_section_name,
            c.subsection_number,
            c.subsection_name,
            c.hierarchy_path,
            c.chunk_content,
            c.primary_section_page_count,
            c.subsection_page_count
        FROM iris_document_chunks c
        JOIN iris_document_metadata m ON c.document_id = m.id
        WHERE m.document_name = %s
        ORDER BY c.page_number
    """

    results = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, [document_name])
            rows = cur.fetchall()

            for row in rows:
                results.append(
                    ChunkResult(
                        chunk_id=str(row["chunk_id"]),
                        document_name=row["document_name"],
                        page_number=row["page_number"],
                        primary_section_number=row["primary_section_number"],
                        primary_section_name=row["primary_section_name"],
                        subsection_number=row["subsection_number"],
                        subsection_name=row["subsection_name"],
                        hierarchy_path=row["hierarchy_path"],
                        chunk_content=row["chunk_content"],
                        similarity=0.0,  # Not from similarity search
                        primary_section_page_count=row["primary_section_page_count"],
                        subsection_page_count=row["subsection_page_count"],
                    )
                )
    finally:
        conn.close()

    return results


def fill_page_gaps(
    document_name: str,
    existing_chunks: List[ChunkResult],
    gap_limit: int = 3,
) -> List[ChunkResult]:
    """
    Fill gaps between retrieved page ranges.

    If we have pages [4, 5, 9, 10] and gap_limit=3, the gap between 5 and 9
    is 3 pages (6, 7, 8), so we fill it in to get [4, 5, 6, 7, 8, 9, 10].

    Args:
        document_name: Document to search within
        existing_chunks: Already retrieved chunks
        gap_limit: Maximum gap size to fill (in pages)

    Returns:
        List of chunks that fill the gaps (does not include existing chunks)
    """
    if not existing_chunks:
        return []

    # Get unique page numbers, sorted
    existing_pages = sorted(set(c.page_number for c in existing_chunks))

    if len(existing_pages) < 2:
        return []

    # Find gaps to fill
    gap_chunks = []
    for i in range(len(existing_pages) - 1):
        current_page = existing_pages[i]
        next_page = existing_pages[i + 1]
        gap_size = next_page - current_page - 1

        # If gap is within limit, fill it
        if 0 < gap_size <= gap_limit:
            gap_start = current_page + 1
            gap_end = next_page - 1
            gap_chunks.extend(
                get_chunks_by_page_range(document_name, gap_start, gap_end)
            )

    return gap_chunks


def expand_chunk(
    chunk: ChunkResult,
    section_limit: int = 5,
    subsection_limit: int = 3,
    neighbor_limit: int = 2,
) -> ExpandedContext:
    """
    Expand a chunk to include related content using cascading logic.

    Expansion priority (cascading):
    1. If primary section is small (<= section_limit), expand to ENTIRE primary section
       → Complete topic coverage with all subsections
    2. Elif subsection is small (<= subsection_limit), expand to subsection + neighbors
       → Focused subtopic with leading/trailing subsection context
    3. Else expand to chunk + neighboring chunks
       → Minimal but with immediate page context

    Args:
        chunk: The seed chunk to expand
        section_limit: Expand to primary section if <= this many pages
        subsection_limit: Expand to subsection if <= this many pages
        neighbor_limit: Number of leading/trailing chunks to include in fallback

    Returns:
        ExpandedContext with expansion details and chunks
    """
    # LEVEL 1: Primary section expansion (complete topic coverage)
    # If the entire primary section fits, grab all of it
    if (
        chunk.primary_section_page_count is not None
        and chunk.primary_section_page_count > 0
        and chunk.primary_section_page_count <= section_limit
        and chunk.primary_section_number is not None
    ):
        expanded_chunks = get_primary_section_chunks(
            chunk.document_name,
            chunk.primary_section_number,
        )
        if expanded_chunks:
            return ExpandedContext(
                seed_chunk=chunk,
                expansion_type="primary_section",
                expanded_chunks=expanded_chunks,
                total_pages=len(expanded_chunks),
            )

    # LEVEL 2: Subsection + neighbors expansion (focused with context)
    # Primary section too large, but subsection fits - get it plus neighbors
    if (
        chunk.subsection_page_count is not None
        and chunk.subsection_page_count > 0
        and chunk.subsection_page_count <= subsection_limit
        and chunk.subsection_number is not None
        and chunk.primary_section_number is not None
    ):
        # Get the main subsection
        expanded_chunks = get_subsection_chunks(
            chunk.document_name,
            chunk.primary_section_number,
            chunk.subsection_number,
        )
        if expanded_chunks:
            # Also get neighboring subsections (if they're within limit)
            neighbor_chunks = get_neighboring_subsections(
                chunk.document_name,
                chunk.primary_section_number,
                chunk.subsection_number,
                subsection_limit,
            )
            # Combine and deduplicate by chunk_id
            all_chunks = expanded_chunks + neighbor_chunks
            seen_ids = set()
            unique_chunks = []
            for c in all_chunks:
                if c.chunk_id not in seen_ids:
                    seen_ids.add(c.chunk_id)
                    unique_chunks.append(c)
            # Sort by page number
            unique_chunks.sort(key=lambda c: c.page_number)

            return ExpandedContext(
                seed_chunk=chunk,
                expansion_type="subsection_with_neighbors",
                expanded_chunks=unique_chunks,
                total_pages=len(unique_chunks),
            )

    # LEVEL 3: Chunk + neighboring chunks (fallback)
    # Both primary section and subsection too large - get chunk with page neighbors
    neighbor_chunks = get_neighboring_chunks(
        chunk.document_name,
        chunk.page_number,
        neighbor_limit,
    )
    # Combine seed chunk with neighbors
    all_chunks = [chunk] + neighbor_chunks
    # Deduplicate and sort
    seen_ids = set()
    unique_chunks = []
    for c in all_chunks:
        if c.chunk_id not in seen_ids:
            seen_ids.add(c.chunk_id)
            unique_chunks.append(c)
    unique_chunks.sort(key=lambda c: c.page_number)

    expansion_type = "chunk_with_neighbors" if neighbor_chunks else "none"
    return ExpandedContext(
        seed_chunk=chunk,
        expansion_type=expansion_type,
        expanded_chunks=unique_chunks,
        total_pages=len(unique_chunks),
    )


def retrieve_with_expansion(
    query: str,
    document_name: str,
    top_k: int = 5,
    document_limit: int = 0,
    section_limit: int = 5,
    subsection_limit: int = 3,
    neighbor_limit: int = 2,
    gap_limit: int = 3,
    use_expansion: bool = True,
    auth_token: str = "",
) -> Tuple[List[ChunkResult], List[ExpandedContext], int, int]:
    """
    Full retrieval pipeline with cascading expansion and gap filling.

    Pipeline:
    0. If document is small (<= document_limit), return entire document
    1. Retrieve top-K chunks by vector similarity
    2. Expand each chunk (primary section → subsection+neighbors → chunk+neighbors)
    3. Fill gaps between retrieved page ranges

    Args:
        query: The question/query text
        document_name: Document to search within
        top_k: Number of chunks to retrieve
        document_limit: Load entire document if <= this many pages (0 = disabled)
        section_limit: Expand to primary section if <= this many pages
        subsection_limit: Expand to subsection if <= this many pages
        neighbor_limit: Number of leading/trailing chunks for fallback expansion
        gap_limit: Maximum gap size (in pages) to fill between retrieved ranges
        use_expansion: Whether to apply expansion logic
        auth_token: Auth token for embedding API

    Returns:
        Tuple of (top_k_chunks, expanded_contexts, total_unique_pages, gap_pages_filled)
    """
    # Step 0: Check if entire document should be loaded
    if document_limit > 0:
        doc_page_count = get_document_page_count(document_name)
        if doc_page_count > 0 and doc_page_count <= document_limit:
            # Document is small enough - load the entire thing
            all_chunks = get_all_document_chunks(document_name)
            if all_chunks:
                # Create a single "full_document" expansion context
                # Use the first chunk as a seed (for compatibility)
                context = ExpandedContext(
                    seed_chunk=all_chunks[0],
                    expansion_type="full_document",
                    expanded_chunks=all_chunks,
                    total_pages=len(all_chunks),
                )
                # Return: no top-k similarity needed, full document context
                return [], [context], len(all_chunks), 0

    # Step 1: Get top-K chunks by similarity
    top_k_chunks = retrieve_chunks(query, document_name, top_k, auth_token)

    if not use_expansion:
        # No expansion - return chunks as-is
        contexts = [
            ExpandedContext(
                seed_chunk=chunk,
                expansion_type="none",
                expanded_chunks=[chunk],
                total_pages=1,
            )
            for chunk in top_k_chunks
        ]
        return top_k_chunks, contexts, len(top_k_chunks), 0

    # Step 2: Expand each chunk using cascading logic
    expanded_contexts = []
    seen_chunk_ids = set()

    for chunk in top_k_chunks:
        # Skip if we've already included this chunk via expansion
        if chunk.chunk_id in seen_chunk_ids:
            continue

        # Expand the chunk using cascading logic
        context = expand_chunk(chunk, section_limit, subsection_limit, neighbor_limit)

        # Track chunk IDs to avoid duplicates
        new_chunk_ids = {c.chunk_id for c in context.expanded_chunks}
        seen_chunk_ids.update(new_chunk_ids)
        expanded_contexts.append(context)

    # Step 3: Gap filling
    # Collect all chunks from all expansions
    all_expanded_chunks = []
    for ctx in expanded_contexts:
        all_expanded_chunks.extend(ctx.expanded_chunks)

    # Fill gaps between page ranges
    gap_chunks = fill_page_gaps(document_name, all_expanded_chunks, gap_limit)

    # Add gap chunks to seen set and create gap context if any
    gap_pages_filled = 0
    if gap_chunks:
        # Deduplicate gap chunks
        unique_gap_chunks = []
        for c in gap_chunks:
            if c.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(c.chunk_id)
                unique_gap_chunks.append(c)

        if unique_gap_chunks:
            gap_pages_filled = len(unique_gap_chunks)
            # Add as a special "gap_fill" context
            gap_context = ExpandedContext(
                seed_chunk=unique_gap_chunks[0],  # Use first gap chunk as seed
                expansion_type="gap_fill",
                expanded_chunks=unique_gap_chunks,
                total_pages=len(unique_gap_chunks),
            )
            expanded_contexts.append(gap_context)

    # Calculate total unique pages
    total_pages = len(seen_chunk_ids)

    return top_k_chunks, expanded_contexts, total_pages, gap_pages_filled


# --- Evaluation Functions ---


def get_all_formatted_context(expanded_contexts: List[ExpandedContext]) -> str:
    """
    Collect all chunks from all contexts and format them using expansion-type-aware formatting.

    Each context is formatted according to its expansion type:
    - full_document/primary_section: No hierarchy path on each page
    - subsection_with_neighbors: Hierarchy at start of each subsection
    - chunk_with_neighbors/none/gap_fill: Hierarchy on each chunk

    Deduplicates by chunk_id across contexts.

    Args:
        expanded_contexts: List of expanded contexts from retrieval

    Returns:
        All chunks formatted in standardized LLM format
    """
    if not expanded_contexts:
        return ""

    # If there's only one context, use its formatted_content directly
    if len(expanded_contexts) == 1:
        return expanded_contexts[0].formatted_content

    # Multiple contexts: collect all unique chunks, tracking their expansion type
    # We'll use the most "complete" expansion type for deduplication
    # Priority: full_document > primary_section > subsection > chunk > gap_fill
    expansion_priority = {
        "full_document": 0,
        "primary_section": 1,
        "subsection_with_neighbors": 2,
        "chunk_with_neighbors": 3,
        "none": 4,
        "gap_fill": 5,
    }

    # Track chunk_id -> (chunk, expansion_type)
    chunk_map: Dict[str, Tuple[ChunkResult, str]] = {}

    for ctx in expanded_contexts:
        for chunk in ctx.expanded_chunks:
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = (chunk, ctx.expansion_type)
            else:
                # Keep the one with higher priority (lower number)
                existing_priority = expansion_priority.get(chunk_map[chunk.chunk_id][1], 99)
                new_priority = expansion_priority.get(ctx.expansion_type, 99)
                if new_priority < existing_priority:
                    chunk_map[chunk.chunk_id] = (chunk, ctx.expansion_type)

    # Sort all chunks by page number
    all_chunks_with_types = sorted(
        chunk_map.values(),
        key=lambda x: x[0].page_number or 0,
    )

    # Determine the dominant expansion type (most restrictive wins for formatting)
    # If any context is full_document, format without hierarchy
    # Otherwise use per-chunk logic
    expansion_types_present = {t for _, t in all_chunks_with_types}

    if "full_document" in expansion_types_present:
        # Full document context - no hierarchy on any page
        chunks = [c for c, _ in all_chunks_with_types]
        return format_chunks_for_llm(chunks, include_hierarchy=False)
    elif expansion_types_present == {"primary_section"}:
        # Only primary section - no hierarchy
        chunks = [c for c, _ in all_chunks_with_types]
        return format_chunks_for_llm(chunks, include_hierarchy=False)
    else:
        # Mixed expansion types - format each chunk with appropriate hierarchy
        # For subsection: hierarchy at start of each subsection
        # For chunk-level: hierarchy on each chunk
        formatted_parts = []
        current_subsection = None
        prev_expansion_type = None

        for chunk, exp_type in all_chunks_with_types:
            if exp_type in ("full_document", "primary_section"):
                # No hierarchy
                formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=False))
            elif exp_type == "subsection_with_neighbors":
                # Hierarchy at start of each subsection
                subsection_key = (chunk.primary_section_number, chunk.subsection_number)
                if subsection_key != current_subsection or prev_expansion_type != exp_type:
                    current_subsection = subsection_key
                    formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=True))
                else:
                    formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=False))
            else:
                # Chunk-level or gap fill - always include hierarchy
                formatted_parts.append(format_chunk_for_llm(chunk, include_hierarchy=True))

            prev_expansion_type = exp_type

        return "\n\n" + "=" * 60 + "\n\n".join(formatted_parts) + "\n\n" + "=" * 60


def evaluate_retrieval(
    qa_pair: QAPair,
    expanded_contexts: List[ExpandedContext],
    auth_token: str = "",
) -> Tuple[bool, str]:
    """
    Use LLM to evaluate if expanded context contains evidence for answer.

    Args:
        qa_pair: The QA pair being tested
        expanded_contexts: Expanded contexts from retrieval
        auth_token: Auth token for LLM API

    Returns:
        Tuple of (evidence_found, explanation)
    """
    # Build context using standardized format
    context = get_all_formatted_context(expanded_contexts)

    # Build evaluation prompt
    system_prompt = """You are evaluating retrieval quality for a document QA system.
Given a question, the expected answer, and retrieved document contexts, determine if
the retrieved content contains sufficient evidence to answer the question.

Respond with JSON:
{
  "evidence_found": true/false,
  "explanation": "Brief explanation of why evidence was/wasn't found"
}"""

    user_prompt = f"""Question: {qa_pair.question}

Expected Answer: {qa_pair.answer}

Retrieved Context:
{context}

Does the retrieved context contain evidence to answer the question?"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response, _ = call_llm(
            auth_token,
            messages=messages,
            model=config.MODEL_SMALL,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        evidence_found = result.get("evidence_found", False)
        explanation = result.get("explanation", "")
    except Exception as e:
        logger.warning(f"LLM evaluation failed: {e}")
        evidence_found = False
        explanation = f"Evaluation error: {e}"

    return evidence_found, explanation


# --- Main Test Function ---


def run_retrieval_test(
    top_k: int = 5,
    document_limit: int = 0,
    section_limit: int = 5,
    subsection_limit: int = 3,
    neighbor_limit: int = 2,
    gap_limit: int = 3,
    use_expansion: bool = True,
    evaluate: bool = False,
    filter_document: Optional[str] = None,
    use_selected: bool = False,
    auth_token: str = "",
) -> Dict[str, Any]:
    """
    Run retrieval test against all QA pairs.

    Args:
        top_k: Number of chunks to retrieve per query
        document_limit: Load entire document if <= this many pages (0 = disabled)
        section_limit: Expand to primary section if <= this many pages
        subsection_limit: Expand to subsection if <= this many pages
        neighbor_limit: Number of leading/trailing chunks for fallback expansion
        gap_limit: Maximum gap size (in pages) to fill between retrieved ranges
        use_expansion: Whether to apply expansion logic
        evaluate: Whether to use LLM to evaluate results
        filter_document: Only test this document (by name)
        use_selected: Use pre-selected QA pairs from selected_qa_pairs.json
        auth_token: Auth token for API calls

    Returns:
        Dict with test results and statistics
    """
    results = {
        "config": {
            "top_k": top_k,
            "document_limit": document_limit,
            "section_limit": section_limit,
            "subsection_limit": subsection_limit,
            "neighbor_limit": neighbor_limit,
            "gap_limit": gap_limit,
            "use_expansion": use_expansion,
            "use_selected": use_selected,
        },
        "total_questions": 0,
        "questions_by_type": {},
        "expansion_stats": {
            "full_document": 0,
            "none": 0,
            "primary_section": 0,
            "subsection_with_neighbors": 0,
            "chunk_with_neighbors": 0,
            "gap_fill": 0,
        },
        "gap_pages_filled": 0,
        "retrieval_results": [],
        "summary": {},
    }

    # Check which documents are in the database
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT document_name FROM iris_document_metadata")
            db_documents = {row["document_name"] for row in cur.fetchall()}
    finally:
        conn.close()

    logger.info(f"Documents in database: {db_documents}")

    # Load QA pairs
    all_qa_pairs: List[QAPair] = []

    if use_selected:
        # Use pre-selected QA pairs
        all_qa_pairs = load_selected_qa_pairs()
        # Filter to documents in database
        all_qa_pairs = [qa for qa in all_qa_pairs if qa.document in db_documents]
        # Filter by document if specified
        if filter_document:
            all_qa_pairs = [qa for qa in all_qa_pairs if qa.document == filter_document]
    else:
        # Load from JSONL files (original behavior)
        for folder_id, (doc_name, qa_path) in QA_DATA_MAP.items():
            if doc_name not in db_documents:
                logger.info(f"Skipping {doc_name} - not in database")
                continue
            if filter_document and doc_name != filter_document:
                continue

            qa_pairs = load_qa_pairs(qa_path, doc_name)
            all_qa_pairs.extend(qa_pairs)

    if not all_qa_pairs:
        logger.warning("No QA pairs to test")
        return results

    results["total_questions"] = len(all_qa_pairs)
    total_pages_retrieved = 0

    # Process each QA pair
    for qa_pair in all_qa_pairs:
        logger.info(f"\nTesting: {qa_pair.question[:60]}...")

        # Track by type
        if qa_pair.qa_type not in results["questions_by_type"]:
            results["questions_by_type"][qa_pair.qa_type] = {
                "total": 0,
                "evidence_found": 0,
            }
        results["questions_by_type"][qa_pair.qa_type]["total"] += 1

        # Retrieve with expansion and gap filling
        top_k_chunks, expanded_contexts, pages_retrieved, gap_filled = retrieve_with_expansion(
            query=qa_pair.question,
            document_name=qa_pair.document,
            top_k=top_k,
            document_limit=document_limit,
            section_limit=section_limit,
            subsection_limit=subsection_limit,
            neighbor_limit=neighbor_limit,
            gap_limit=gap_limit,
            use_expansion=use_expansion,
            auth_token=auth_token,
        )

        total_pages_retrieved += pages_retrieved
        results["gap_pages_filled"] += gap_filled

        # Track expansion types (handle any expansion type dynamically)
        for ctx in expanded_contexts:
            exp_type = ctx.expansion_type
            if exp_type not in results["expansion_stats"]:
                results["expansion_stats"][exp_type] = 0
            results["expansion_stats"][exp_type] += 1

        # Prepare result entry
        result_entry = {
            "question": qa_pair.question,
            "answer": qa_pair.answer,
            "type": qa_pair.qa_type,
            "document": qa_pair.document,
            "top_chunk_similarity": top_k_chunks[0].similarity if top_k_chunks else 0,
            "top_chunk_page": top_k_chunks[0].page_number if top_k_chunks else None,
            "top_chunk_section": top_k_chunks[0].primary_section_name
            if top_k_chunks
            else None,
            "pages_retrieved": pages_retrieved,
            "gap_pages_filled": gap_filled,
            "expansion_types": [ctx.expansion_type for ctx in expanded_contexts],
        }

        if evaluate:
            # Use LLM to evaluate
            evidence_found, explanation = evaluate_retrieval(
                qa_pair, expanded_contexts, auth_token
            )

            if evidence_found:
                results["questions_by_type"][qa_pair.qa_type]["evidence_found"] += 1

            result_entry["evidence_found"] = evidence_found
            result_entry["llm_explanation"] = explanation

            status = "FOUND" if evidence_found else "MISS"
            logger.info(f"  [{status}] Pages: {pages_retrieved}, {explanation[:60]}...")
        else:
            if top_k_chunks:
                logger.info(
                    f"  Top chunk: page {top_k_chunks[0].page_number}, "
                    f"similarity {top_k_chunks[0].similarity:.3f}, "
                    f"pages retrieved: {pages_retrieved}"
                )

        results["retrieval_results"].append(result_entry)

    # Calculate summary
    results["avg_pages_retrieved"] = (
        total_pages_retrieved / results["total_questions"]
        if results["total_questions"] > 0
        else 0
    )

    if evaluate:
        total_found = sum(
            t["evidence_found"] for t in results["questions_by_type"].values()
        )
        results["summary"] = {
            "total_questions": results["total_questions"],
            "evidence_found": total_found,
            "accuracy": total_found / results["total_questions"]
            if results["total_questions"] > 0
            else 0,
            "avg_pages_retrieved": results["avg_pages_retrieved"],
            "by_type": {
                qtype: {
                    "accuracy": data["evidence_found"] / data["total"]
                    if data["total"] > 0
                    else 0,
                    **data,
                }
                for qtype, data in results["questions_by_type"].items()
            },
        }

    return results


def print_results(results: Dict[str, Any]):
    """Print test results summary."""
    print("\n" + "=" * 70)
    print("DEEP RESEARCH RETRIEVAL TEST RESULTS")
    print("=" * 70)

    report_config = results.get("config", {})
    print(f"\nConfiguration:")
    doc_limit = report_config.get('document_limit', 0)
    doc_limit_str = f"Document limit: {doc_limit}" if doc_limit > 0 else "Document limit: disabled"
    print(
        f"  {doc_limit_str} | "
        f"Section limit: {report_config.get('section_limit', 5)} | "
        f"Subsection limit: {report_config.get('subsection_limit', 3)}"
    )
    print(
        f"  Top-K: {report_config.get('top_k', 5)} | "
        f"Gap limit: {report_config.get('gap_limit', 3)} | "
        f"Expansion: {'enabled' if report_config.get('use_expansion', True) else 'disabled'}"
    )

    print(f"\nTotal questions tested: {results['total_questions']}")

    if "summary" in results and results["summary"]:
        summary = results["summary"]
        print(
            f"\nEvidence Found: {summary['evidence_found']}/{summary['total_questions']} "
            f"({summary['accuracy']:.1%})"
        )
        print(f"Avg pages retrieved: {summary['avg_pages_retrieved']:.1f}")
        print(f"Total gap pages filled: {results.get('gap_pages_filled', 0)}")

        print("\nBy Question Type:")
        for qtype, data in summary.get("by_type", {}).items():
            print(
                f"  {qtype:15s}: {data['evidence_found']:3d}/{data['total']:3d} "
                f"({data['accuracy']:.1%})"
            )

    # Expansion stats
    exp_stats = results.get("expansion_stats", {})
    total_expansions = sum(exp_stats.values())
    if total_expansions > 0:
        print("\nExpansion Stats:")
        for exp_type in ["full_document", "primary_section", "subsection_with_neighbors", "chunk_with_neighbors", "gap_fill", "none"]:
            count = exp_stats.get(exp_type, 0)
            if count > 0:
                pct = count / total_expansions
                print(f"  {exp_type:25s}: {count:3d} ({pct:.1%})")

    # Show detailed results
    print("\n" + "-" * 70)
    print("Detailed Results:")
    for i, r in enumerate(results["retrieval_results"], 1):
        status = ""
        if "evidence_found" in r:
            status = "[FOUND]" if r["evidence_found"] else "[MISS] "
        print(f"\n{i}. {status} {r['question'][:65]}...")
        print(f"   Answer: {r['answer'][:65]}...")
        print(f"   Type: {r['type']}, Document: {r['document']}")
        print(
            f"   Top chunk: page {r['top_chunk_page']}, "
            f"section: {r.get('top_chunk_section', 'N/A')}, "
            f"similarity: {r['top_chunk_similarity']:.3f}"
        )
        gap_info = f", gap filled: {r.get('gap_pages_filled', 0)}" if r.get('gap_pages_filled', 0) > 0 else ""
        print(f"   Pages retrieved: {r['pages_retrieved']}{gap_info}, Expansions: {r['expansion_types']}")


def main():
    parser = argparse.ArgumentParser(
        description="Test deep research retrieval with expansion"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--document-limit",
        type=int,
        default=0,
        help="Load entire document if <= this many pages (0 = disabled, default: 0)",
    )
    parser.add_argument(
        "--section-limit",
        type=int,
        default=5,
        help="Expand to full primary section if <= this many pages (default: 5)",
    )
    parser.add_argument(
        "--subsection-limit",
        type=int,
        default=3,
        help="Expand to subsection + neighbors if <= this many pages (default: 3)",
    )
    parser.add_argument(
        "--neighbor-limit",
        type=int,
        default=2,
        help="Number of leading/trailing chunks for fallback expansion (default: 2)",
    )
    parser.add_argument(
        "--gap-limit",
        type=int,
        default=3,
        help="Maximum gap size (in pages) to fill between retrieved ranges (default: 3)",
    )
    parser.add_argument(
        "--no-expansion",
        action="store_true",
        help="Disable expansion (baseline comparison)",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Use LLM to evaluate if evidence was found",
    )
    parser.add_argument(
        "--document",
        type=str,
        default=None,
        help="Filter to specific document name",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "--use-selected",
        action="store_true",
        help="Use pre-selected QA pairs from selected_qa_pairs.json (excludes metadata questions)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("DEEP RESEARCH RETRIEVAL TEST (Cascading Expansion + Gap Fill)")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Top-K: {args.top_k}")
    doc_limit_str = f"{args.document_limit} pages (Level 0: full document)" if args.document_limit > 0 else "disabled"
    print(f"  Document limit: {doc_limit_str}")
    print(f"  Section limit: {args.section_limit} pages (Level 1: full primary section)")
    print(f"  Subsection limit: {args.subsection_limit} pages (Level 2: subsection + neighbors)")
    print(f"  Neighbor limit: {args.neighbor_limit} chunks (Level 3: chunk + neighbors)")
    print(f"  Gap limit: {args.gap_limit} pages (fill gaps between ranges)")
    print(f"  Expansion: {'disabled' if args.no_expansion else 'enabled'}")
    print(f"  Evaluate with LLM: {args.evaluate}")
    print(f"  Document filter: {args.document or 'All'}")
    print(f"  Use selected QAs: {args.use_selected}")

    # Get auth token from environment
    try:
        auth_token = _get_auth_token()
    except Exception as exc:
        print(f"ERROR: Could not obtain auth token: {exc}")
        sys.exit(1)

    results = run_retrieval_test(
        top_k=args.top_k,
        document_limit=args.document_limit,
        section_limit=args.section_limit,
        subsection_limit=args.subsection_limit,
        neighbor_limit=args.neighbor_limit,
        gap_limit=args.gap_limit,
        use_expansion=not args.no_expansion,
        evaluate=args.evaluate,
        filter_document=args.document,
        use_selected=args.use_selected,
        auth_token=auth_token,
    )

    print_results(results)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
