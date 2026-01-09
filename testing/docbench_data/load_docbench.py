#!/usr/bin/env python3
"""
DocBench Document Loader for IRIS Test Tables.

Loads DocBench benchmark documents into iris_test_* tables for RAG evaluation.
Processes PDFs, generates embeddings, and creates test data for retrieval testing.

Usage:
    python testing/docbench_data/load_docbench.py
    python testing/docbench_data/load_docbench.py --domain academia --limit 5
    python testing/docbench_data/load_docbench.py --dry-run

Prerequisites:
    - PostgreSQL running with test tables created
    - OPENAI_API_KEY environment variable set
    - DocBench data downloaded to testing/docbench_data/data/
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

# DocBench domain mapping: folder ranges -> db_source
DOMAIN_MAPPING = {
    "academia": {"start": 0, "end": 48, "db_source": "test_docbench_academia"},
    "finance": {"start": 49, "end": 88, "db_source": "test_docbench_finance"},
    "government": {"start": 89, "end": 132, "db_source": "test_docbench_government"},
    "laws": {"start": 133, "end": 178, "db_source": "test_docbench_laws"},
    "news": {"start": 179, "end": 228, "db_source": "test_docbench_news"},
}

# Database configuration
DB_CONFIG = {
    "host": os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost"),
    "port": os.getenv("VECTOR_POSTGRES_DB_PORT", "34532"),
    "dbname": os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance"),
    "user": os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres")),
    "password": os.getenv("VECTOR_POSTGRES_DB_PASSWORD", ""),
}

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
EMBEDDING_BATCH_SIZE = 100

# Summary configuration
SUMMARY_MAX_PAGES = 100
SUMMARY_SPLIT_PAGES = 50  # First N and last N pages if over max

# Rate limiting
API_DELAY_SECONDS = 0.3

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Database Operations
# =============================================================================


def get_db_connection():
    """Get PostgreSQL connection with pgvector support."""
    import psycopg2
    import psycopg2.extras
    from pgvector.psycopg2 import register_vector

    # Register UUID adapter
    psycopg2.extras.register_uuid()

    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )
    register_vector(conn)
    return conn


def ensure_registry_entry(conn, db_source: str, domain: str) -> None:
    """Ensure database registry entry exists for the domain."""
    domain_info = {
        "academia": {
            "name": "DocBench Academia",
            "summary": "NLP research papers from ACL, EMNLP, and other venues",
            "description": "Academic papers covering natural language processing, machine learning, and computational linguistics research.",
        },
        "finance": {
            "name": "DocBench Finance",
            "summary": "Financial reports, SEC filings, and earnings documents",
            "description": "Corporate financial documents including 10-K filings, annual reports, and quarterly earnings statements.",
        },
        "government": {
            "name": "DocBench Government",
            "summary": "Federal agency reports and policy documents",
            "description": "Government publications including agency reports, policy analyses, and regulatory documents.",
        },
        "laws": {
            "name": "DocBench Laws",
            "summary": "Legal documents and court filings",
            "description": "Legal materials including court decisions, legal briefs, and regulatory filings.",
        },
        "news": {
            "name": "DocBench News",
            "summary": "News articles and press releases",
            "description": "Journalism and press materials covering various topics and events.",
        },
    }

    info = domain_info.get(domain, {})
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iris_test_database_registry
            (db_source, db_name, db_summary, db_description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (db_source) DO UPDATE SET
                db_name = EXCLUDED.db_name,
                db_summary = EXCLUDED.db_summary,
                db_description = EXCLUDED.db_description,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                db_source,
                info.get("name", f"DocBench {domain.title()}"),
                info.get("summary", f"DocBench {domain} documents"),
                info.get("description", f"DocBench benchmark documents from {domain} domain."),
            ),
        )
    conn.commit()


def check_file_changed(conn, db_source: str, doc_name: str, file_hash: str) -> bool:
    """Check if file has changed since last load."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT file_hash FROM iris_test_document_metadata
            WHERE db_source = %s AND document_name = %s
            """,
            (db_source, doc_name),
        )
        result = cur.fetchone()
        if result is None:
            return True  # New file
        return result[0] != file_hash  # Changed if hash different


def upsert_document(
    conn,
    db_source: str,
    doc_name: str,
    summary: str,
    summary_embedding: Optional[List[float]],
    page_count: int,
    file_path: str,
    file_hash: str,
    file_size: int,
) -> uuid.UUID:
    """Insert or update document metadata, returning document ID."""
    doc_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iris_test_document_metadata (
                id, db_source, document_name, document_summary, summary_embedding,
                page_count, file_name, file_path, file_size, file_type, file_hash
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (db_source, document_name) DO UPDATE SET
                document_summary = EXCLUDED.document_summary,
                summary_embedding = EXCLUDED.summary_embedding,
                page_count = EXCLUDED.page_count,
                file_path = EXCLUDED.file_path,
                file_size = EXCLUDED.file_size,
                file_hash = EXCLUDED.file_hash,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (
                doc_id,
                db_source,
                doc_name,
                summary,
                summary_embedding,
                page_count,
                Path(file_path).name,
                file_path,
                file_size,
                Path(file_path).suffix.lower(),
                file_hash,
            ),
        )
        result = cur.fetchone()
        return result[0] if result else doc_id


def delete_document_chunks(conn, doc_id: uuid.UUID) -> None:
    """Delete existing chunks for a document before re-inserting."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM iris_test_document_chunks WHERE document_id = %s",
            (doc_id,),
        )


def insert_chunks(
    conn,
    doc_id: uuid.UUID,
    db_source: str,
    pages: List[str],
    embeddings: Optional[List[List[float]]],
    file_name: str,
) -> int:
    """Insert document chunks (one per page)."""
    if not pages:
        return 0

    with conn.cursor() as cur:
        for i, page_text in enumerate(pages):
            page_num = i + 1
            embedding = embeddings[i] if embeddings and i < len(embeddings) else None
            cur.execute(
                """
                INSERT INTO iris_test_document_chunks (
                    document_id, db_source, chunk_number, chunk_content,
                    chunk_embedding, page_number, file_name, source_filename
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id,
                    db_source,
                    page_num,
                    page_text,
                    embedding,
                    page_num,
                    file_name,
                    file_name,
                ),
            )
    return len(pages)


def insert_qa_pairs(
    conn, db_source: str, doc_name: str, folder_id: int, qa_data: List[Dict]
) -> int:
    """Insert QA pairs for a document."""
    if not qa_data:
        return 0

    with conn.cursor() as cur:
        for i, qa in enumerate(qa_data):
            question_id = f"{folder_id}_{i}"
            question_type = qa.get("type", "unknown")
            is_answerable = question_type not in ("unanswerable", "una-web")

            cur.execute(
                """
                INSERT INTO iris_test_qa_pairs (
                    db_source, document_name, question_id, question,
                    question_type, gold_answer, evidence_text, is_answerable
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (db_source, question_id) DO UPDATE SET
                    question = EXCLUDED.question,
                    gold_answer = EXCLUDED.gold_answer,
                    evidence_text = EXCLUDED.evidence_text,
                    question_type = EXCLUDED.question_type
                """,
                (
                    db_source,
                    doc_name,
                    question_id,
                    qa.get("question", ""),
                    question_type,
                    qa.get("answer", ""),
                    qa.get("evidence", ""),
                    is_answerable,
                ),
            )
    return len(qa_data)


# =============================================================================
# Document Processing
# =============================================================================


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _sanitize_text(text: str) -> str:
    """Remove NUL characters and other problematic bytes from text."""
    # Remove NUL characters (cause PostgreSQL errors)
    text = text.replace("\x00", "")
    # Remove other control characters except newlines and tabs
    text = "".join(c if c >= " " or c in "\n\t\r" else " " for c in text)
    return text


def extract_pdf_pages(file_path: str) -> List[str]:
    """Extract text from PDF file, one string per page.

    Uses pymupdf4llm for LLM-optimized Markdown extraction.
    Falls back to basic PyMuPDF if pymupdf4llm fails.
    """
    pages = []

    # Try pymupdf4llm first (best for LLM/RAG)
    try:
        import pymupdf4llm

        page_chunks = pymupdf4llm.to_markdown(file_path, page_chunks=True)
        for chunk in page_chunks:
            text = chunk.get("text", "") or ""
            text = _sanitize_text(text)
            pages.append(text.strip())
        return pages
    except Exception as e:
        logger.warning(f"pymupdf4llm failed for {file_path}: {e}, trying fitz")

    # Fallback to basic PyMuPDF
    try:
        import fitz

        doc = fitz.open(file_path)
        for page in doc:
            text = page.get_text() or ""
            text = _sanitize_text(text)
            pages.append(text.strip())
        doc.close()
    except Exception as e2:
        logger.warning(f"Error extracting PDF {file_path}: {e2}")
        return []

    return pages


def extract_docx_pages(file_path: str) -> List[str]:
    """Extract text from DOCX file."""
    from docx import Document

    try:
        doc = Document(file_path)
        # DOCX doesn't have pages, treat whole doc as one "page"
        full_text = "\n".join([p.text for p in doc.paragraphs])
        # Split into ~3000 char chunks to simulate pages
        chunk_size = 3000
        pages = []
        for i in range(0, len(full_text), chunk_size):
            pages.append(full_text[i : i + chunk_size])
        return pages if pages else [""]
    except Exception as e:
        logger.warning(f"Error extracting DOCX {file_path}: {e}")
        return []


def extract_document_pages(file_path: str) -> List[str]:
    """Extract pages from document based on file type."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_pages(file_path)
    elif suffix in (".docx", ".doc"):
        return extract_docx_pages(file_path)
    else:
        logger.warning(f"Unsupported file type: {suffix}")
        return []


def load_qa_file(qa_path: str) -> List[Dict]:
    """Load QA pairs from JSONL file."""
    qa_pairs = []
    try:
        with open(qa_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    qa_pairs.append(json.loads(line))
    except Exception as e:
        logger.warning(f"Error loading QA file {qa_path}: {e}")
    return qa_pairs


# =============================================================================
# LLM Operations
# =============================================================================


def get_openai_client():
    """Get OpenAI client."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def generate_document_summary(pages: List[str], client) -> str:
    """Generate document summary using LLM."""
    if not pages:
        return "Empty document."

    # Select pages for summary
    if len(pages) <= SUMMARY_MAX_PAGES:
        selected_pages = pages
    else:
        # First N and last N pages
        first = pages[:SUMMARY_SPLIT_PAGES]
        last = pages[-SUMMARY_SPLIT_PAGES:]
        selected_pages = first + ["[... middle pages omitted ...]"] + last

    # Combine pages
    page_texts = []
    for i, text in enumerate(selected_pages):
        if text and text != "[... middle pages omitted ...]":
            page_texts.append(f"[Page {i+1}]\n{text[:2000]}")  # Truncate long pages
        elif text:
            page_texts.append(text)

    combined = "\n\n".join(page_texts)[:30000]  # Limit total context

    time.sleep(API_DELAY_SECONDS)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert document summarizer. Create a comprehensive summary of the document that captures its main topics, purpose, and key information. The summary should be 2-4 paragraphs.",
                },
                {
                    "role": "user",
                    "content": f"Please summarize the following document:\n\n{combined}",
                },
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Error generating summary: {e}")
        # Fallback: use first page
        return pages[0][:1000] if pages else "Document summary unavailable."


def generate_embeddings_batch(texts: List[str], client) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []

    # Truncate long texts
    truncated = [t[:8000] if t else "" for t in texts]

    time.sleep(API_DELAY_SECONDS)

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=truncated,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.warning(f"Error generating embeddings: {e}")
        return []


# =============================================================================
# Main Processing
# =============================================================================


def discover_documents(data_dir: Path, domain: Optional[str] = None) -> List[Dict]:
    """Discover documents in the data directory."""
    documents = []

    for domain_name, info in DOMAIN_MAPPING.items():
        if domain and domain != domain_name:
            continue

        for folder_id in range(info["start"], info["end"] + 1):
            folder_path = data_dir / str(folder_id)
            if not folder_path.exists():
                continue

            # Find PDF/DOCX file
            doc_files = list(folder_path.glob("*.pdf")) + list(folder_path.glob("*.docx"))
            if not doc_files:
                continue

            doc_file = doc_files[0]

            # Find QA file
            qa_files = list(folder_path.glob("*_qa.jsonl"))
            qa_file = qa_files[0] if qa_files else None

            documents.append({
                "folder_id": folder_id,
                "domain": domain_name,
                "db_source": info["db_source"],
                "doc_path": str(doc_file),
                "qa_path": str(qa_file) if qa_file else None,
            })

    return documents


def process_document(
    doc_info: Dict,
    conn,
    client,
    skip_embeddings: bool = False,
    force: bool = False,
) -> Dict[str, int]:
    """Process a single document and load into database."""
    doc_path = doc_info["doc_path"]
    db_source = doc_info["db_source"]
    doc_name = Path(doc_path).name
    folder_id = doc_info["folder_id"]

    stats = {"pages": 0, "chunks": 0, "qa_pairs": 0, "skipped": False}

    # Calculate file hash
    file_hash = calculate_file_hash(doc_path)
    file_size = os.path.getsize(doc_path)

    # Check if already processed (unless force)
    if not force and not check_file_changed(conn, db_source, doc_name, file_hash):
        stats["skipped"] = True
        return stats

    # Extract pages
    pages = extract_document_pages(doc_path)
    if not pages:
        logger.warning(f"No content extracted from {doc_path}")
        return stats

    stats["pages"] = len(pages)

    # Generate summary
    summary = generate_document_summary(pages, client)

    # Generate embeddings
    summary_embedding = None
    chunk_embeddings = None

    if not skip_embeddings:
        # Summary embedding
        summary_embeds = generate_embeddings_batch([summary], client)
        summary_embedding = summary_embeds[0] if summary_embeds else None

        # Chunk embeddings (batch by EMBEDDING_BATCH_SIZE)
        chunk_embeddings = []
        for i in range(0, len(pages), EMBEDDING_BATCH_SIZE):
            batch = pages[i : i + EMBEDDING_BATCH_SIZE]
            embeds = generate_embeddings_batch(batch, client)
            chunk_embeddings.extend(embeds)

    # Upsert document
    doc_id = upsert_document(
        conn,
        db_source,
        doc_name,
        summary,
        summary_embedding,
        len(pages),
        doc_path,
        file_hash,
        file_size,
    )

    # Delete old chunks and insert new
    delete_document_chunks(conn, doc_id)
    stats["chunks"] = insert_chunks(
        conn, doc_id, db_source, pages, chunk_embeddings, doc_name
    )

    # Load QA pairs
    if doc_info.get("qa_path"):
        qa_data = load_qa_file(doc_info["qa_path"])
        stats["qa_pairs"] = insert_qa_pairs(conn, db_source, doc_name, folder_id, qa_data)

    conn.commit()
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load DocBench data into IRIS test tables")
    parser.add_argument("--domain", choices=list(DOMAIN_MAPPING.keys()), help="Single domain to load")
    parser.add_argument("--limit", type=int, help="Limit documents per domain")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation")
    parser.add_argument("--force", action="store_true", help="Force reload even if unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Preview without database changes")
    args = parser.parse_args()

    # Find data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("DocBench Document Loader")
    logger.info("=" * 60)
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Database: {DB_CONFIG['dbname']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    # Discover documents
    documents = discover_documents(data_dir, args.domain)
    logger.info(f"Found {len(documents)} documents")

    if args.limit:
        # Group by domain and limit each
        by_domain = {}
        for doc in documents:
            by_domain.setdefault(doc["domain"], []).append(doc)
        documents = []
        for domain_docs in by_domain.values():
            documents.extend(domain_docs[: args.limit])
        logger.info(f"Limited to {len(documents)} documents")

    if args.dry_run:
        logger.info("\n--- DRY RUN ---")
        for doc in documents[:10]:
            logger.info(f"  {doc['domain']}: {Path(doc['doc_path']).name}")
        if len(documents) > 10:
            logger.info(f"  ... and {len(documents) - 10} more")
        return

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False
        logger.info("Install tqdm for progress bar: pip install tqdm")

    # Initialize
    client = get_openai_client()
    conn = get_db_connection()

    # Ensure registry entries exist
    domains_to_process = set(doc["domain"] for doc in documents)
    for domain in domains_to_process:
        db_source = DOMAIN_MAPPING[domain]["db_source"]
        ensure_registry_entry(conn, db_source, domain)

    # Process documents
    total_stats = {"pages": 0, "chunks": 0, "qa_pairs": 0, "processed": 0, "skipped": 0}

    iterator = tqdm(documents, desc="Processing") if use_tqdm else documents
    for doc_info in iterator:
        try:
            stats = process_document(
                doc_info,
                conn,
                client,
                skip_embeddings=args.skip_embeddings,
                force=args.force,
            )

            if stats["skipped"]:
                total_stats["skipped"] += 1
            else:
                total_stats["processed"] += 1
                total_stats["pages"] += stats["pages"]
                total_stats["chunks"] += stats["chunks"]
                total_stats["qa_pairs"] += stats["qa_pairs"]

            if not use_tqdm:
                status = "skipped" if stats["skipped"] else f"{stats['pages']} pages"
                logger.info(f"  {Path(doc_info['doc_path']).name}: {status}")

        except Exception as e:
            logger.error(f"Error processing {doc_info['doc_path']}: {e}")
            continue

    conn.close()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("LOADING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Documents processed: {total_stats['processed']}")
    logger.info(f"Documents skipped (unchanged): {total_stats['skipped']}")
    logger.info(f"Total pages/chunks: {total_stats['chunks']}")
    logger.info(f"Total QA pairs: {total_stats['qa_pairs']}")


if __name__ == "__main__":
    main()
