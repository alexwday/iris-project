#!/usr/bin/env python3
"""
Populate Unified Document Tables for Cascading Retrieval Architecture.

This script migrates data from existing tables to the new unified tables:
  - apg_catalog -> iris_document_metadata
  - apg_content -> iris_document_chunks
  - iris_semantic_search -> iris_document_chunks

Part of IRIS Enhancement: Universal Cascading Retrieval Architecture

Usage:
    python testing/populate_unified_tables.py

Prerequisites:
    - PostgreSQL running on port 34532
    - Database 'finance-dev' exists with new tables created
    - Existing tables populated with sample data
"""

import os
import subprocess
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Set environment variables BEFORE importing anything that might use config
current_user = subprocess.check_output(["whoami"]).decode().strip()
if os.getenv("VECTOR_POSTGRES_DB_USERNAME", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_USERNAME"] = current_user
if os.getenv("VECTOR_POSTGRES_DB_HOST", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
if os.getenv("VECTOR_POSTGRES_DB_PORT", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
if os.getenv("VECTOR_POSTGRES_DB_NAME", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"

# Default env values for local development
os.environ.setdefault("VECTOR_POSTGRES_DB_USERNAME", current_user)
os.environ.setdefault("VECTOR_POSTGRES_DB_HOST", "localhost")
os.environ.setdefault("VECTOR_POSTGRES_DB_PORT", "34532")
os.environ.setdefault("VECTOR_POSTGRES_DB_NAME", "finance-dev")
os.environ.setdefault("VECTOR_POSTGRES_DB_PASSWORD", "")
os.environ.setdefault("OPENAI_API_KEY", "sk-placeholder-for-db-operations")
os.environ.setdefault("RBC_ENVIRONMENT", "local")

import psycopg2
import psycopg2.extras
from psycopg2.extras import register_uuid

# Register UUID type adapter
register_uuid()

# For OpenAI embeddings
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def generate_embedding(
    text: str,
    model: str = "text-embedding-3-large",
    dimensions: int = 2000,
) -> Optional[List[float]]:
    """
    Generate embedding for text using OpenAI API.

    Args:
        text: Text to embed
        model: OpenAI embedding model name
        dimensions: Output embedding dimensions (OpenAI supports reduced dimensions)

    Returns:
        List of floats (embedding vector) or None if failed
    """
    if not HAS_OPENAI:
        print("  WARNING: OpenAI not available, skipping embedding generation")
        return None

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "sk-placeholder-for-db-operations":
        print("  WARNING: No valid OPENAI_API_KEY, skipping embedding generation")
        return None

    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=text[:8000],  # Truncate to avoid token limits
            model=model,
            dimensions=dimensions,  # Use 2000 dims to match database schema
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  WARNING: Failed to generate embedding: {e}")
        return None


def get_connection():
    """Get a database connection using environment variables."""
    return psycopg2.connect(
        host=os.environ["VECTOR_POSTGRES_DB_HOST"],
        port=os.environ["VECTOR_POSTGRES_DB_PORT"],
        dbname=os.environ["VECTOR_POSTGRES_DB_NAME"],
        user=os.environ["VECTOR_POSTGRES_DB_USERNAME"],
        password=os.environ.get("VECTOR_POSTGRES_DB_PASSWORD", ""),
    )


def migrate_apg_catalog_to_metadata(conn) -> Dict[str, uuid.UUID]:
    """
    Migrate documents from apg_catalog to iris_document_metadata.

    Returns:
        Dict mapping (db_source, document_name) to new UUID id
    """
    print("\n--- Migrating apg_catalog -> iris_document_metadata ---")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Fetch all records from apg_catalog
    cursor.execute("""
        SELECT
            document_source,
            document_name,
            document_type,
            document_description,
            document_usage,
            document_usage_embedding,
            file_name,
            file_path,
            file_size,
            file_type
        FROM apg_catalog
    """)
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} documents in apg_catalog")

    document_id_map = {}

    for row in rows:
        db_source = row["document_source"]
        doc_name = row["document_name"]

        # Generate summary from description + usage
        summary_parts = []
        if row["document_description"]:
            summary_parts.append(row["document_description"])
        if row["document_usage"]:
            summary_parts.append(f"Usage: {row['document_usage']}")
        document_summary = " ".join(summary_parts) or f"Document: {doc_name}"

        # Generate embedding for the summary
        summary_embedding = row["document_usage_embedding"]  # Try to reuse existing
        if summary_embedding is None:
            print(f"    Generating embedding for: {doc_name}")
            summary_embedding = generate_embedding(document_summary)

        # Get page count from apg_content sections
        cursor.execute(
            """
            SELECT COUNT(DISTINCT section_id) as section_count,
                   MAX(page_number) as max_page
            FROM apg_content
            WHERE document_source = %s AND document_name LIKE %s
        """,
            (db_source, f"{doc_name.rsplit('.', 1)[0]}%"),
        )
        content_info = cursor.fetchone()
        section_count = content_info["section_count"] or 0
        page_count = content_info["max_page"] or 0

        # Insert into iris_document_metadata
        new_id = uuid.uuid4()
        cursor.execute(
            """
            INSERT INTO iris_document_metadata (
                id, db_source, document_name, document_type,
                document_summary, summary_embedding,
                page_count, section_count,
                file_name, file_path, file_size, file_type,
                document_description, document_usage
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (db_source, document_name) DO UPDATE SET
                document_summary = EXCLUDED.document_summary,
                summary_embedding = EXCLUDED.summary_embedding,
                page_count = EXCLUDED.page_count,
                section_count = EXCLUDED.section_count,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """,
            (
                new_id,
                db_source,
                doc_name,
                row["document_type"],
                document_summary,
                summary_embedding,  # Generated or reused embedding
                page_count,
                section_count,
                row["file_name"],
                row["file_path"],
                row["file_size"],
                row["file_type"],
                row["document_description"],
                row["document_usage"],
            ),
        )
        result = cursor.fetchone()
        actual_id = result[0] if result else new_id
        document_id_map[(db_source, doc_name)] = actual_id

    conn.commit()
    print(f"  Migrated {len(document_id_map)} documents to iris_document_metadata")
    return document_id_map


def migrate_apg_content_to_chunks(conn, document_id_map: Dict[str, uuid.UUID]):
    """
    Migrate sections from apg_content to iris_document_chunks.
    """
    print("\n--- Migrating apg_content -> iris_document_chunks ---")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Fetch all records from apg_content
    cursor.execute("""
        SELECT
            document_source,
            document_name,
            section_id,
            section_name,
            section_summary,
            section_content,
            page_number
        FROM apg_content
        ORDER BY document_source, document_name, section_id
    """)
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} sections in apg_content")

    chunks_inserted = 0
    chunks_skipped = 0

    for row in rows:
        db_source = row["document_source"]
        doc_name_without_ext = row["document_name"]

        # Find matching document in metadata (try with common extensions)
        document_id = None
        for ext in ["", ".pdf", ".PDF", ".docx", ".xlsx"]:
            key = (db_source, f"{doc_name_without_ext}{ext}")
            if key in document_id_map:
                document_id = document_id_map[key]
                doc_name = f"{doc_name_without_ext}{ext}"
                break

        if not document_id:
            # Try exact match
            for key, doc_id in document_id_map.items():
                if key[0] == db_source and key[1].startswith(doc_name_without_ext):
                    document_id = doc_id
                    doc_name = key[1]
                    break

        if not document_id:
            chunks_skipped += 1
            continue

        # Insert into iris_document_chunks
        cursor.execute(
            """
            INSERT INTO iris_document_chunks (
                document_id, db_source, chunk_number,
                section_number, section_name,
                chunk_content, chunk_summary,
                page_number,
                file_name, source_filename
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s,
                %s, %s
            )
        """,
            (
                document_id,
                db_source,
                row["section_id"],  # Use section_id as chunk_number
                row["section_id"],
                row["section_name"],
                row["section_content"],
                row["section_summary"],
                row["page_number"],
                doc_name,
                doc_name_without_ext,
            ),
        )
        chunks_inserted += 1

    conn.commit()
    print(f"  Migrated {chunks_inserted} sections to iris_document_chunks")
    if chunks_skipped:
        print(f"  Skipped {chunks_skipped} sections (no matching document)")


def migrate_semantic_search_to_chunks(conn):
    """
    Migrate chunks from iris_semantic_search to iris_document_chunks.
    Also creates document metadata entries for external sources.
    """
    print("\n--- Migrating iris_semantic_search -> iris_document_chunks ---")
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Mapping from semantic search document_id to registry db_source
    # This handles the naming mismatch between tables
    DOC_ID_TO_DB_SOURCE = {
        "EY_FRD_LEASES_2024": "external_ey",
        "PWC_REVENUE_2024": "external_iasb",  # Map PwC to IASB for now (or could skip)
        "ey_international_gaap_2024": "external_ey",
        "iasb_ias": "external_iasb",
        "iasb_ifrs": "external_iasb",
        "iasb_ifrics": "external_iasb",
        "iasb_sic": "external_iasb",
    }

    # Fetch unique documents from iris_semantic_search
    cursor.execute("""
        SELECT DISTINCT
            document_id,
            source_filename,
            filepath
        FROM iris_semantic_search
        WHERE document_id IS NOT NULL
    """)
    unique_docs = cursor.fetchall()
    print(f"  Found {len(unique_docs)} unique documents in iris_semantic_search")

    document_id_map = {}

    # Create document metadata entries for external documents
    for doc in unique_docs:
        original_doc_id = doc["document_id"]  # In semantic search, document_id is like "EY_FRD_LEASES_2024"
        source_filename = doc["source_filename"] or "Unknown Document"

        # Map to actual db_source in registry
        db_source = DOC_ID_TO_DB_SOURCE.get(original_doc_id, original_doc_id)

        # Check if db_source exists in registry
        cursor.execute(
            "SELECT 1 FROM iris_database_registry WHERE db_source = %s", (db_source,)
        )
        if not cursor.fetchone():
            print(f"  Skipping {original_doc_id} (mapped to {db_source}) - not in database registry")
            continue

        # Get aggregated info from chunks (use original_doc_id for query)
        cursor.execute(
            """
            SELECT
                COUNT(*) as chunk_count,
                MAX(chapter_number) as max_chapter,
                STRING_AGG(DISTINCT chapter_name, ', ') as chapters,
                MAX(chunk_end_page) as max_page
            FROM iris_semantic_search
            WHERE document_id = %s AND source_filename = %s
        """,
            (original_doc_id, source_filename),
        )
        agg_info = cursor.fetchone()

        # Build summary from chapter names
        document_summary = f"{source_filename}"
        if agg_info["chapters"]:
            document_summary += f". Chapters: {agg_info['chapters'][:500]}"

        # Generate embedding for the summary
        print(f"    Generating embedding for: {source_filename}")
        summary_embedding = generate_embedding(document_summary)

        # Insert document metadata
        new_id = uuid.uuid4()
        cursor.execute(
            """
            INSERT INTO iris_document_metadata (
                id, db_source, document_name, document_type,
                document_summary, summary_embedding, page_count, chapter_count,
                file_name
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s
            )
            ON CONFLICT (db_source, document_name) DO UPDATE SET
                document_summary = EXCLUDED.document_summary,
                summary_embedding = EXCLUDED.summary_embedding,
                page_count = EXCLUDED.page_count,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """,
            (
                new_id,
                db_source,
                source_filename,
                "external_textbook",
                document_summary,
                summary_embedding,
                agg_info["max_page"],
                agg_info["max_chapter"],
                source_filename,
            ),
        )
        result = cursor.fetchone()
        actual_id = result[0] if result else new_id
        # Store mapping with original_doc_id as key (for chunk lookup)
        document_id_map[(original_doc_id, source_filename)] = (actual_id, db_source)

    conn.commit()
    print(f"  Created {len(document_id_map)} document metadata entries")

    # Now migrate chunks
    cursor.execute("""
        SELECT
            document_id as original_doc_id,
            source_filename,
            chunk_number,
            chapter_number,
            chapter_name,
            section_number,
            section_summary,
            chunk_content,
            embedding,
            chunk_start_page,
            chunk_end_page,
            chunk_start_reference,
            chunk_end_reference
        FROM iris_semantic_search
        WHERE document_id IS NOT NULL
        ORDER BY document_id, source_filename, chunk_number
    """)
    chunks = cursor.fetchall()
    print(f"  Found {len(chunks)} chunks in iris_semantic_search")

    chunks_inserted = 0
    chunks_skipped = 0

    for chunk in chunks:
        original_doc_id = chunk["original_doc_id"]
        source_filename = chunk["source_filename"] or "Unknown Document"

        # Find document_id and db_source from our mapping
        mapping = document_id_map.get((original_doc_id, source_filename))
        if not mapping:
            chunks_skipped += 1
            continue
        document_id, db_source = mapping

        # Build hierarchy string
        hierarchy = ""
        if chunk["chapter_number"]:
            hierarchy = f"Ch{chunk['chapter_number']}"
            if chunk["section_number"]:
                hierarchy += f".S{chunk['section_number']}"

        # Insert chunk
        cursor.execute(
            """
            INSERT INTO iris_document_chunks (
                document_id, db_source, chunk_number,
                chapter_number, chapter_name,
                section_number, chapter_section_hierarchy,
                chunk_content, chunk_summary, chunk_embedding,
                page_number, page_reference,
                page_start, page_end,
                file_name, source_filename
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
        """,
            (
                document_id,
                db_source,
                chunk["chunk_number"],
                chunk["chapter_number"],
                chunk["chapter_name"],
                chunk["section_number"],
                hierarchy,
                chunk["chunk_content"],
                chunk["section_summary"],  # Use section_summary as chunk_summary
                chunk["embedding"],
                chunk["chunk_start_page"],
                chunk["chunk_start_reference"],
                chunk["chunk_start_page"],
                chunk["chunk_end_page"],
                source_filename,
                source_filename,
            ),
        )
        chunks_inserted += 1

    conn.commit()
    print(f"  Migrated {chunks_inserted} chunks to iris_document_chunks")
    if chunks_skipped:
        print(f"  Skipped {chunks_skipped} chunks (no matching document)")


def verify_migration(conn):
    """Verify the migration was successful."""
    print("\n--- Verification ---")
    cursor = conn.cursor()

    # Count documents
    cursor.execute("SELECT COUNT(*) FROM iris_document_metadata")
    doc_count = cursor.fetchone()[0]
    print(f"  iris_document_metadata: {doc_count} documents")

    # Count chunks
    cursor.execute("SELECT COUNT(*) FROM iris_document_chunks")
    chunk_count = cursor.fetchone()[0]
    print(f"  iris_document_chunks: {chunk_count} chunks")

    # Count by source
    cursor.execute("""
        SELECT db_source, COUNT(*) as doc_count
        FROM iris_document_metadata
        GROUP BY db_source
        ORDER BY db_source
    """)
    print("\n  Documents by source:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]}")

    # Verify view
    cursor.execute("""
        SELECT document_name, chunk_count
        FROM v_document_with_chunks
        ORDER BY chunk_count DESC
        LIMIT 5
    """)
    print("\n  Top 5 documents by chunk count:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]} chunks")


def main():
    """Main entry point."""
    print("=" * 60)
    print("UNIFIED DOCUMENT TABLES POPULATION")
    print("=" * 60)

    try:
        conn = get_connection()
        print(f"Connected to database: {os.environ['VECTOR_POSTGRES_DB_NAME']}")

        # Check if new tables exist
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('iris_document_metadata', 'iris_document_chunks')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if "iris_document_metadata" not in tables:
            print("\nERROR: iris_document_metadata table does not exist!")
            print("Run setup_local_db.sql first to create the tables.")
            sys.exit(1)

        if "iris_document_chunks" not in tables:
            print("\nERROR: iris_document_chunks table does not exist!")
            print("Run setup_local_db.sql first to create the tables.")
            sys.exit(1)

        # Clear existing data (for idempotent re-runs)
        print("\n--- Clearing existing data ---")
        cursor.execute("DELETE FROM iris_document_chunks")
        cursor.execute("DELETE FROM iris_document_metadata")
        conn.commit()
        print("  Cleared existing unified table data")

        # Migrate from apg_catalog to iris_document_metadata
        document_id_map = migrate_apg_catalog_to_metadata(conn)

        # Migrate from apg_content to iris_document_chunks
        migrate_apg_content_to_chunks(conn, document_id_map)

        # Migrate from iris_semantic_search to iris_document_chunks
        migrate_semantic_search_to_chunks(conn)

        # Verify migration
        verify_migration(conn)

        conn.close()

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print("\nThe new unified tables are now populated with data from:")
        print("  - apg_catalog -> iris_document_metadata")
        print("  - apg_content -> iris_document_chunks")
        print("  - iris_semantic_search -> iris_document_chunks")
        print("\nExisting tables remain unchanged for backward compatibility.")

    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
