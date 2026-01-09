#!/usr/bin/env python3
"""
Populate Local Database with Sample IRIS Data

This script generates and inserts sample data into the local PostgreSQL database
for testing the IRIS pipeline. It uses OpenAI to generate realistic content.

Usage:
    export OPENAI_API_KEY='sk-...'
    python populate_local_db.py

Prerequisites:
    - PostgreSQL running on port 34532 with 'finance-dev' database
    - pgvector extension installed
    - Tables created via setup_local_db.sql
    - OpenAI API key set
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import sample data definitions
from sample_data_definitions import (
    INTERNAL_DOCUMENTS,
    EXTERNAL_DOCUMENTS,
    CATALOG_DESCRIPTION_PROMPT,
    CATALOG_USAGE_PROMPT,
    SECTION_CONTENT_PROMPT,
    SECTION_SUMMARY_PROMPT,
    CHUNK_CONTENT_PROMPT,
    CHAPTER_SUMMARY_PROMPT,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": "34532",
    "dbname": "finance-dev",
    "user": os.getenv("VECTOR_POSTGRES_DB_USERNAME", "alexwday"),
    "password": os.getenv("VECTOR_POSTGRES_DB_PASSWORD", ""),
}

# Rate limiting for OpenAI API
API_DELAY_SECONDS = 0.5  # Delay between API calls to avoid rate limits

# =============================================================================
# DATABASE HELPERS
# =============================================================================

def get_db_connection():
    """Get PostgreSQL connection with pgvector support."""
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )
    register_vector(conn)
    return conn


def clear_sample_data(conn):
    """Clear existing sample data from tables."""
    logger.info("Clearing existing sample data...")
    with conn.cursor() as cur:
        # Clear internal documents
        cur.execute("DELETE FROM apg_catalog WHERE document_source LIKE 'internal_%'")
        cur.execute("DELETE FROM apg_content WHERE document_source LIKE 'internal_%'")

        # Clear external documents
        cur.execute("DELETE FROM iris_semantic_search WHERE document_id LIKE 'EY_%' OR document_id LIKE 'PWC_%'")

    conn.commit()
    logger.info("Sample data cleared")


# =============================================================================
# OPENAI HELPERS
# =============================================================================

def get_openai_client():
    """Get OpenAI client."""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    return OpenAI(api_key=api_key)


def generate_text(client, prompt: str, max_tokens: int = 500) -> str:
    """Generate text using GPT-4o-mini."""
    time.sleep(API_DELAY_SECONDS)  # Rate limiting

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


def generate_embedding(client, text: str) -> List[float]:
    """Generate embedding using text-embedding-3-large."""
    time.sleep(API_DELAY_SECONDS)  # Rate limiting

    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=[text],
        dimensions=2000,
    )

    return response.data[0].embedding


def generate_embeddings_batch(client, texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts in one call."""
    if not texts:
        return []

    time.sleep(API_DELAY_SECONDS)

    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=texts,
        dimensions=2000,
    )

    return [item.embedding for item in response.data]


# =============================================================================
# INTERNAL DOCUMENT GENERATION
# =============================================================================

def generate_catalog_entry(
    client,
    doc_source: str,
    doc_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a catalog entry with AI-generated descriptions."""
    logger.info(f"  Generating catalog entry: {doc_info['document_name']}")

    # Generate description
    description_prompt = CATALOG_DESCRIPTION_PROMPT.format(
        document_name=doc_info["document_name"],
        document_type=doc_info["document_type"],
        theme=doc_info["theme"],
    )
    description = generate_text(client, description_prompt, max_tokens=200)

    # Generate usage statement
    usage_prompt = CATALOG_USAGE_PROMPT.format(
        document_name=doc_info["document_name"],
        theme=doc_info["theme"],
        topics=", ".join(doc_info.get("topics", [])),
    )
    usage = generate_text(client, usage_prompt, max_tokens=200)

    # Generate embedding for description
    embedding = generate_embedding(client, description)

    return {
        "document_source": doc_source,
        "document_type": doc_info["document_type"],
        "document_name": doc_info["document_name"],
        "document_description": description,
        "document_usage": usage,
        "document_description_embedding": embedding,
        "file_name": f"{doc_info['document_name'].lower().replace(' ', '_').replace('-', '_')}.pdf",
        "file_link": f"file:///sample_docs/{doc_info['document_name'].lower().replace(' ', '_')}.pdf",
    }


def generate_content_sections(
    client,
    doc_source: str,
    doc_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate content sections for a document."""
    sections = []
    num_pages = doc_info["num_pages"]
    topics = doc_info.get("topics", [f"Topic {i+1}" for i in range(num_pages)])

    for page_num in range(1, num_pages + 1):
        topic = topics[page_num - 1] if page_num <= len(topics) else f"Section {page_num}"
        section_name = f"{page_num}. {topic}"

        logger.info(f"    Generating section {page_num}/{num_pages}: {topic}")

        # Generate section summary
        summary_prompt = SECTION_SUMMARY_PROMPT.format(
            section_name=section_name,
            topic=topic,
            document_name=doc_info["document_name"],
        )
        summary = generate_text(client, summary_prompt, max_tokens=100)

        # Generate section content
        content_prompt = SECTION_CONTENT_PROMPT.format(
            document_name=doc_info["document_name"],
            section_name=section_name,
            page_number=page_num,
            total_pages=num_pages,
            topic=topic,
            theme=doc_info["theme"],
        )
        content = generate_text(client, content_prompt, max_tokens=600)

        sections.append({
            "document_source": doc_source,
            "document_type": doc_info["document_type"],
            "document_name": doc_info["document_name"],
            "section_id": page_num,
            "section_name": section_name,
            "section_summary": summary,
            "section_content": content,
            "page_number": page_num,
        })

    return sections


def insert_internal_documents(conn, client):
    """Generate and insert all internal documents."""
    logger.info("\n" + "="*60)
    logger.info("GENERATING INTERNAL DOCUMENTS")
    logger.info("="*60)

    total_catalog = 0
    total_content = 0

    for doc_source, documents in INTERNAL_DOCUMENTS.items():
        logger.info(f"\nProcessing {doc_source}...")

        for doc_info in documents:
            # Generate catalog entry
            catalog_entry = generate_catalog_entry(client, doc_source, doc_info)

            # Insert catalog entry
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO apg_catalog
                    (document_source, document_type, document_name, document_description,
                     document_usage, document_description_embedding, file_name, file_link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    catalog_entry["document_source"],
                    catalog_entry["document_type"],
                    catalog_entry["document_name"],
                    catalog_entry["document_description"],
                    catalog_entry["document_usage"],
                    catalog_entry["document_description_embedding"],
                    catalog_entry["file_name"],
                    catalog_entry["file_link"],
                ))
                catalog_id = cur.fetchone()[0]

            total_catalog += 1

            # Generate and insert content sections
            sections = generate_content_sections(client, doc_source, doc_info)

            with conn.cursor() as cur:
                for section in sections:
                    cur.execute("""
                        INSERT INTO apg_content
                        (document_source, document_type, document_name, section_id,
                         section_name, section_summary, section_content, page_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        section["document_source"],
                        section["document_type"],
                        section["document_name"],
                        section["section_id"],
                        section["section_name"],
                        section["section_summary"],
                        section["section_content"],
                        section["page_number"],
                    ))

            total_content += len(sections)
            conn.commit()

    logger.info(f"\nInternal documents complete:")
    logger.info(f"  - Catalog entries: {total_catalog}")
    logger.info(f"  - Content sections: {total_content}")

    return total_catalog, total_content


# =============================================================================
# EXTERNAL DOCUMENT GENERATION
# =============================================================================

def generate_chunk_content(
    client,
    doc_info: Dict[str, Any],
    chapter: Dict[str, Any],
    section: Dict[str, Any],
    chunk_number: int,
) -> str:
    """Generate content for a single chunk."""
    prompt = CHUNK_CONTENT_PROMPT.format(
        source_filename=doc_info["source_filename"],
        chapter_name=chapter["chapter_name"],
        section_name=section["section_name"],
        page_start=section["page_range"][0],
        page_end=section["page_range"][1],
        theme=section["theme"],
        chunk_number=chunk_number,
        total_chunks=section["num_chunks"],
    )

    return generate_text(client, prompt, max_tokens=600)


def generate_chapter_summary(
    client,
    doc_info: Dict[str, Any],
    chapter: Dict[str, Any],
) -> str:
    """Generate chapter summary."""
    section_names = ", ".join([s["section_name"] for s in chapter["sections"]])

    prompt = CHAPTER_SUMMARY_PROMPT.format(
        source_filename=doc_info["source_filename"],
        chapter_number=chapter["chapter_number"],
        chapter_name=chapter["chapter_name"],
        section_names=section_names,
    )

    return generate_text(client, prompt, max_tokens=150)


def insert_external_documents(conn, client):
    """Generate and insert all external documents."""
    logger.info("\n" + "="*60)
    logger.info("GENERATING EXTERNAL DOCUMENTS (Semantic Search)")
    logger.info("="*60)

    total_chunks = 0

    for doc_source, documents in EXTERNAL_DOCUMENTS.items():
        logger.info(f"\nProcessing {doc_source}...")

        for doc_info in documents:
            logger.info(f"  Document: {doc_info['source_filename']}")

            for chapter in doc_info["chapters"]:
                logger.info(f"    Chapter {chapter['chapter_number']}: {chapter['chapter_name']}")

                # Generate chapter summary
                chapter_summary = generate_chapter_summary(client, doc_info, chapter)

                for section in chapter["sections"]:
                    logger.info(f"      Section {section['section_number']}: {section['section_name']}")

                    # Calculate page info
                    page_start, page_end = section["page_range"]
                    section_page_count = page_end - page_start + 1

                    # Build section summary with breadcrumb
                    section_summary = f"{chapter['chapter_name']} > {section['section_name']}: {section['theme']}"

                    # Generate chunks
                    chunk_texts = []
                    chunk_records = []

                    for chunk_num in range(1, section["num_chunks"] + 1):
                        # Generate chunk content
                        chunk_content = generate_chunk_content(
                            client, doc_info, chapter, section, chunk_num
                        )
                        chunk_texts.append(chunk_content)

                        # Calculate chunk page range (distribute across section pages)
                        pages_per_chunk = max(1, section_page_count // section["num_chunks"])
                        chunk_start_page = page_start + (chunk_num - 1) * pages_per_chunk
                        chunk_end_page = min(page_end, chunk_start_page + pages_per_chunk - 1)

                        chunk_records.append({
                            "document_id": doc_info["document_id"],
                            "filename": f"{chapter['chapter_number']:02d}_{chapter['chapter_name'].replace(' ', '_')}.pdf",
                            "filepath": f"/sample_docs/{doc_info['document_id']}/{chapter['chapter_number']:02d}_{chapter['chapter_name'].replace(' ', '_')}.pdf",
                            "source_filename": doc_info["source_filename"],
                            "chapter_number": chapter["chapter_number"],
                            "chapter_name": chapter["chapter_name"],
                            "chapter_summary": chapter_summary,
                            "chapter_page_count": sum(
                                s["page_range"][1] - s["page_range"][0] + 1
                                for s in chapter["sections"]
                            ),
                            "section_number": section["section_number"],
                            "section_summary": section_summary,
                            "section_start_page": page_start,
                            "section_end_page": page_end,
                            "section_page_count": section_page_count,
                            "section_start_reference": f"{chapter['chapter_number']}-{page_start}",
                            "section_end_reference": f"{chapter['chapter_number']}-{page_end}",
                            "chunk_number": chunk_num,
                            "chunk_content": chunk_content,
                            "chunk_start_page": chunk_start_page,
                            "chunk_end_page": chunk_end_page,
                            "chunk_start_reference": f"{chapter['chapter_number']}-{chunk_start_page}",
                            "chunk_end_reference": f"{chapter['chapter_number']}-{chunk_end_page}",
                        })

                    # Generate embeddings in batch
                    logger.info(f"        Generating {len(chunk_texts)} embeddings...")
                    embeddings = generate_embeddings_batch(client, chunk_texts)

                    # Insert chunks with embeddings
                    with conn.cursor() as cur:
                        for record, embedding in zip(chunk_records, embeddings):
                            cur.execute("""
                                INSERT INTO iris_semantic_search
                                (document_id, filename, filepath, source_filename,
                                 chapter_number, chapter_name, chapter_summary, chapter_page_count,
                                 section_number, section_summary, section_start_page, section_end_page,
                                 section_page_count, section_start_reference, section_end_reference,
                                 chunk_number, chunk_content, chunk_start_page, chunk_end_page,
                                 chunk_start_reference, chunk_end_reference, embedding)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                record["document_id"],
                                record["filename"],
                                record["filepath"],
                                record["source_filename"],
                                record["chapter_number"],
                                record["chapter_name"],
                                record["chapter_summary"],
                                record["chapter_page_count"],
                                record["section_number"],
                                record["section_summary"],
                                record["section_start_page"],
                                record["section_end_page"],
                                record["section_page_count"],
                                record["section_start_reference"],
                                record["section_end_reference"],
                                record["chunk_number"],
                                record["chunk_content"],
                                record["chunk_start_page"],
                                record["chunk_end_page"],
                                record["chunk_start_reference"],
                                record["chunk_end_reference"],
                                embedding,
                            ))

                    total_chunks += len(chunk_records)
                    conn.commit()

    logger.info(f"\nExternal documents complete:")
    logger.info(f"  - Total chunks: {total_chunks}")

    return total_chunks


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    print("="*60)
    print("IRIS LOCAL DATABASE POPULATION")
    print("="*60)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OPENAI_API_KEY environment variable not set")
        print("Usage: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    print(f"\nOpenAI API Key: {api_key[:12]}...")
    print(f"Database: {DB_CONFIG['dbname']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    # Confirm
    print("\nThis will:")
    print("  1. Clear existing sample data")
    print("  2. Generate new sample documents using GPT-4o-mini")
    print("  3. Generate embeddings using text-embedding-3-large")
    print("  4. Insert into local PostgreSQL")
    print(f"\nEstimated API cost: $0.50 - $1.50")

    response = input("\nProceed? [y/N]: ").strip().lower()
    if response != 'y':
        print("Aborted")
        sys.exit(0)

    try:
        # Initialize
        client = get_openai_client()
        conn = get_db_connection()

        # Clear existing data
        clear_sample_data(conn)

        # Generate and insert internal documents
        catalog_count, content_count = insert_internal_documents(conn, client)

        # Generate and insert external documents
        chunk_count = insert_external_documents(conn, client)

        # Summary
        print("\n" + "="*60)
        print("POPULATION COMPLETE")
        print("="*60)
        print(f"\nInternal Documents:")
        print(f"  - apg_catalog entries: {catalog_count}")
        print(f"  - apg_content sections: {content_count}")
        print(f"\nExternal Documents:")
        print(f"  - iris_semantic_search chunks: {chunk_count}")
        print("\nNext step: Run test_full_local.py to test the pipeline")
        print("="*60)

        conn.close()

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
