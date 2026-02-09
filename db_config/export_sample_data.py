#!/usr/bin/env python3
"""
Sample Data Exporter for IRIS Internal Wiki Testing

This script connects to the local maven-finance database and exports a small set
of test documents as SQL INSERT statements for the internal_wiki db_source. The
output file can then be executed on IT's database to provide sample data for
testing the IRIS pipeline.

Exports 3 documents (18 chunks total) from test_docs, remapping them to
internal_wiki with new UUIDs so they don't collide with any existing data.

Usage:
    python db_config/export_sample_data.py
"""

import os
import uuid
from typing import Dict, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg2

DB_HOST = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
DB_PORT = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
DB_NAME = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
DB_USER = os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres"))
DB_PASSWORD = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(
    SCRIPT_DIR, "schemas", "initial_data", "sample_internal_wiki.sql"
)

TARGET_DB_SOURCE = "internal_wiki"
SOURCE_DB_SOURCE = "test_docs"
TARGET_DOCS = ["D18-1334.pdf", "P19-1164.pdf", "W18-5713.pdf"]


def get_connection():
    """Create database connection to local maven-finance."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def escape_sql_string(value: str) -> str:
    """Escape a string for safe inclusion in a SQL literal."""
    return value.replace("'", "''")


def format_sql_value(value) -> str:
    """Format a Python value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f"'{escape_sql_string(value)}'"
    return f"'{escape_sql_string(str(value))}'"


def fetch_metadata(conn) -> List[Dict]:
    """Fetch metadata rows for the target documents."""
    cur = conn.cursor()
    placeholders = ", ".join(["%s"] * len(TARGET_DOCS))
    cur.execute(
        f"""
        SELECT id, db_source, document_name, document_type, document_summary,
               summary_embedding::text, page_count, primary_section_count,
               subsection_count, file_name, file_path, file_size, file_type,
               document_description, document_usage, file_hash
        FROM iris_document_metadata
        WHERE db_source = %s AND document_name IN ({placeholders})
        ORDER BY document_name
        """,
        [SOURCE_DB_SOURCE] + TARGET_DOCS,
    )

    columns = [
        "id", "db_source", "document_name", "document_type", "document_summary",
        "summary_embedding", "page_count", "primary_section_count",
        "subsection_count", "file_name", "file_path", "file_size", "file_type",
        "document_description", "document_usage", "file_hash",
    ]

    rows = []
    for row in cur.fetchall():
        rows.append(dict(zip(columns, row)))
    cur.close()
    return rows


def fetch_chunks(conn, original_doc_id: str) -> List[Dict]:
    """Fetch chunk rows for a given document ID."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, document_id, db_source, chunk_number, primary_section_number,
               primary_section_name, subsection_number, subsection_name,
               hierarchy_path, chunk_content, chunk_embedding::text, page_number,
               file_name, source_filename, primary_section_page_count,
               subsection_page_count
        FROM iris_document_chunks
        WHERE document_id = %s
        ORDER BY chunk_number
        """,
        [original_doc_id],
    )

    columns = [
        "id", "document_id", "db_source", "chunk_number",
        "primary_section_number", "primary_section_name", "subsection_number",
        "subsection_name", "hierarchy_path", "chunk_content", "chunk_embedding",
        "page_number", "file_name", "source_filename",
        "primary_section_page_count", "subsection_page_count",
    ]

    rows = []
    for row in cur.fetchall():
        rows.append(dict(zip(columns, row)))
    cur.close()
    return rows


def generate_metadata_sql(
    metadata_rows: List[Dict], id_mapping: Dict[str, str]
) -> str:
    """Generate SQL INSERT statements for metadata rows."""
    lines = []
    lines.append(
        "-- =============================================================================\n"
        "-- Metadata: iris_document_metadata (internal_wiki sample data)\n"
        "-- =============================================================================\n"
        "--\n"
        "-- 3 sample documents remapped from test_docs to internal_wiki.\n"
        "-- Uses ON CONFLICT to allow idempotent re-runs.\n"
        "-- =============================================================================\n"
    )

    for row in metadata_rows:
        new_id = id_mapping[row["id"]]
        embedding = row["summary_embedding"]

        lines.append(
            f"INSERT INTO iris_document_metadata (\n"
            f"    id, db_source, document_name, document_type, document_summary,\n"
            f"    summary_embedding, page_count, primary_section_count,\n"
            f"    subsection_count, file_name, file_path, file_size, file_type,\n"
            f"    document_description, document_usage, file_hash\n"
            f") VALUES (\n"
            f"    {format_sql_value(new_id)},\n"
            f"    {format_sql_value(TARGET_DB_SOURCE)},\n"
            f"    {format_sql_value(row['document_name'])},\n"
            f"    {format_sql_value(row['document_type'])},\n"
            f"    {format_sql_value(row['document_summary'])},\n"
            f"    '{escape_sql_string(embedding)}'::halfvec,\n"
            f"    {format_sql_value(row['page_count'])},\n"
            f"    {format_sql_value(row['primary_section_count'])},\n"
            f"    {format_sql_value(row['subsection_count'])},\n"
            f"    {format_sql_value(row['file_name'])},\n"
            f"    {format_sql_value(row['file_path'])},\n"
            f"    {format_sql_value(row['file_size'])},\n"
            f"    {format_sql_value(row['file_type'])},\n"
            f"    {format_sql_value(row['document_description'])},\n"
            f"    {format_sql_value(row['document_usage'])},\n"
            f"    {format_sql_value(row['file_hash'])}\n"
            f")\n"
            f"ON CONFLICT (db_source, document_name) DO UPDATE SET\n"
            f"    document_type = EXCLUDED.document_type,\n"
            f"    document_summary = EXCLUDED.document_summary,\n"
            f"    summary_embedding = EXCLUDED.summary_embedding,\n"
            f"    page_count = EXCLUDED.page_count,\n"
            f"    primary_section_count = EXCLUDED.primary_section_count,\n"
            f"    subsection_count = EXCLUDED.subsection_count,\n"
            f"    file_name = EXCLUDED.file_name,\n"
            f"    file_path = EXCLUDED.file_path,\n"
            f"    file_size = EXCLUDED.file_size,\n"
            f"    file_type = EXCLUDED.file_type,\n"
            f"    document_description = EXCLUDED.document_description,\n"
            f"    document_usage = EXCLUDED.document_usage,\n"
            f"    file_hash = EXCLUDED.file_hash,\n"
            f"    updated_at = CURRENT_TIMESTAMP;\n"
        )

    return "\n".join(lines)


def generate_chunks_sql(
    all_chunks: List[Tuple[str, List[Dict]]], id_mapping: Dict[str, str]
) -> str:
    """Generate SQL INSERT statements for chunk rows."""
    lines = []
    lines.append(
        "-- =============================================================================\n"
        "-- Chunks: iris_document_chunks (internal_wiki sample data)\n"
        "-- =============================================================================\n"
        "--\n"
        "-- 18 chunks across 3 sample documents with real HALFVEC(3072) embeddings.\n"
        "-- References metadata IDs from the inserts above.\n"
        "--\n"
        "-- Two-pass approach: metadata must be inserted first so that the\n"
        "-- document_id foreign key references are valid.\n"
        "-- =============================================================================\n"
    )

    for original_doc_id, chunks in all_chunks:
        new_doc_id = id_mapping[original_doc_id]
        doc_name = chunks[0]["file_name"] if chunks else "unknown"
        lines.append(f"-- Chunks for {doc_name} ({len(chunks)} chunks)")

        for chunk in chunks:
            new_chunk_id = str(uuid.uuid4())
            embedding = chunk["chunk_embedding"]

            lines.append(
                f"INSERT INTO iris_document_chunks (\n"
                f"    id, document_id, db_source, chunk_number,\n"
                f"    primary_section_number, primary_section_name,\n"
                f"    subsection_number, subsection_name, hierarchy_path,\n"
                f"    chunk_content, chunk_embedding, page_number, file_name,\n"
                f"    source_filename, primary_section_page_count,\n"
                f"    subsection_page_count\n"
                f") VALUES (\n"
                f"    {format_sql_value(new_chunk_id)},\n"
                f"    {format_sql_value(new_doc_id)},\n"
                f"    {format_sql_value(TARGET_DB_SOURCE)},\n"
                f"    {format_sql_value(chunk['chunk_number'])},\n"
                f"    {format_sql_value(chunk['primary_section_number'])},\n"
                f"    {format_sql_value(chunk['primary_section_name'])},\n"
                f"    {format_sql_value(chunk['subsection_number'])},\n"
                f"    {format_sql_value(chunk['subsection_name'])},\n"
                f"    {format_sql_value(chunk['hierarchy_path'])},\n"
                f"    {format_sql_value(chunk['chunk_content'])},\n"
                f"    '{escape_sql_string(embedding)}'::halfvec,\n"
                f"    {format_sql_value(chunk['page_number'])},\n"
                f"    {format_sql_value(chunk['file_name'])},\n"
                f"    {format_sql_value(chunk['source_filename'])},\n"
                f"    {format_sql_value(chunk['primary_section_page_count'])},\n"
                f"    {format_sql_value(chunk['subsection_page_count'])}\n"
                f")\n"
                f"ON CONFLICT (id) DO NOTHING;\n"
            )

        lines.append("")

    return "\n".join(lines)


def main():
    """Export 3 test documents as internal_wiki sample SQL data."""
    print("Connecting to local database...")
    conn = get_connection()

    print(f"Fetching metadata for {len(TARGET_DOCS)} documents from {SOURCE_DB_SOURCE}...")
    metadata_rows = fetch_metadata(conn)

    if len(metadata_rows) != len(TARGET_DOCS):
        found = [r["document_name"] for r in metadata_rows]
        missing = [d for d in TARGET_DOCS if d not in found]
        print(f"ERROR: Expected {len(TARGET_DOCS)} docs, found {len(metadata_rows)}")
        print(f"  Missing: {missing}")
        conn.close()
        return

    id_mapping = {}
    for row in metadata_rows:
        id_mapping[row["id"]] = str(uuid.uuid4())

    all_chunks = []
    total_chunks = 0
    for row in metadata_rows:
        print(f"  Fetching chunks for {row['document_name']}...")
        chunks = fetch_chunks(conn, row["id"])
        all_chunks.append((row["id"], chunks))
        total_chunks += len(chunks)
        print(f"    Found {len(chunks)} chunks")

    conn.close()

    print(f"\nTotal: {len(metadata_rows)} documents, {total_chunks} chunks")
    print(f"Generating SQL...")

    header = (
        "-- =============================================================================\n"
        "-- Sample Internal Wiki Data for IRIS Testing\n"
        "-- =============================================================================\n"
        "--\n"
        f"-- Auto-generated by export_sample_data.py\n"
        f"-- Source: {SOURCE_DB_SOURCE} -> {TARGET_DB_SOURCE}\n"
        f"-- Documents: {', '.join(TARGET_DOCS)}\n"
        f"-- Total: {len(metadata_rows)} metadata rows, {total_chunks} chunk rows\n"
        "--\n"
        "-- This file inserts sample document data into internal_wiki for testing.\n"
        "-- Requires iris_database_registry to have an 'internal_wiki' entry.\n"
        "-- Metadata is inserted first, then chunks reference the metadata IDs.\n"
        "-- =============================================================================\n"
        "\n"
    )

    metadata_sql = generate_metadata_sql(metadata_rows, id_mapping)
    chunks_sql = generate_chunks_sql(all_chunks, id_mapping)

    full_sql = header + metadata_sql + "\n\n" + chunks_sql

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        f.write(full_sql)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\nWrote {OUTPUT_FILE}")
    print(f"  Size: {file_size_kb:.1f} KB")
    print(f"  Metadata rows: {len(metadata_rows)}")
    print(f"  Chunk rows: {total_chunks}")


if __name__ == "__main__":
    main()
