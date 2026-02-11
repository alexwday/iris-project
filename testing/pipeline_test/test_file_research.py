#!/usr/bin/env python3
"""
Standalone File Research Test Script.

Sends a query through the real IRIS file research pipeline
(execute_file_research_sync) against a specific document in PostgreSQL.
Prints retrieval path, number of findings, and each finding with page number.

Usage:
    python testing/pipeline_test/test_file_research.py \
        --db-source test_docs \
        --document P19-1598.pdf \
        --query "How does the knowledge graph language model generate factual text?"
"""

import argparse
import getpass
import json
import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, PROJECT_ROOT)


def setup_environment():
    """Configure environment for local OpenAI testing."""
    os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
    os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1-mini"
    os.environ["IRIS_MODEL_EMBEDDING"] = "text-embedding-3-large"
    os.environ.setdefault("IRIS_LOG_LEVEL", "WARNING")

    current_user = getpass.getuser()
    os.environ.setdefault("VECTOR_POSTGRES_DB_HOST", "localhost")
    os.environ.setdefault("VECTOR_POSTGRES_DB_PORT", "34532")
    os.environ.setdefault("VECTOR_POSTGRES_DB_NAME", "maven-finance")
    os.environ.setdefault("VECTOR_POSTGRES_DB_USERNAME", current_user)
    os.environ.setdefault("VECTOR_POSTGRES_DB_PASSWORD", "")


setup_environment()

from services.src.connections import postgres as db_config


def build_database_dsn_no_ssl(params: dict, for_sqlalchemy=True):
    """Modified DSN builder that disables SSL for local postgres."""
    host = params.get("host", "localhost")
    hosts = host.split(",") if "," in host else [host]
    port = params.get("port", "5432")
    dbname = params.get("dbname", "postgres")
    user = params.get("user", "postgres")
    password = params.get("password", "")

    if for_sqlalchemy:
        hosts_str = ",".join(hosts)
        return (
            f"postgresql+psycopg2://{user}:{password}@{hosts_str}:{port}/{dbname}"
            f"?sslmode=disable&target_session_attrs=read-write"
        )
    else:
        hosts_str = ",".join(hosts)
        return (
            f"host='{hosts_str}' port='{port}' sslmode='disable' "
            f"target_session_attrs='read-write' dbname='{dbname}' user='{user}' password='{password}'"
        )


db_config.build_database_dsn = build_database_dsn_no_ssl

from services.src.utils.logging_format import configure_root_logger

configure_root_logger()

from sqlalchemy import text

from services.src.agent.planner import _generate_query_embedding_vector
from services.src.agent.tools.file_research_subagent import execute_file_research_sync
from services.src.connections.postgres import get_database_session


def lookup_document_id(file_name: str, db_source: str) -> str:
    """Find document_id from iris_document_metadata by file_name.

    Args:
        file_name: Document filename (e.g. "P19-1598.pdf").
        db_source: Database source (e.g. "test_docs").

    Returns:
        Document UUID string.

    Raises:
        SystemExit: If document is not found.
    """
    with get_database_session() as session:
        row = session.execute(
            text(
                "SELECT id FROM iris_document_metadata "
                "WHERE file_name = :file_name AND db_source = :db_source"
            ),
            {"file_name": file_name, "db_source": db_source},
        ).mappings().first()

    if not row:
        print(f"ERROR: Document '{file_name}' not found in db_source='{db_source}'")
        sys.exit(1)

    return str(row["id"])


def main():
    parser = argparse.ArgumentParser(
        description="Test IRIS file research pipeline against a single document."
    )
    parser.add_argument(
        "--db-source", default="test_docs", help="Database source (default: test_docs)"
    )
    parser.add_argument(
        "--document", required=True, help="Document filename (e.g. P19-1598.pdf)"
    )
    parser.add_argument("--query", required=True, help="Research question")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable DEBUG logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    doc_id = lookup_document_id(args.document, args.db_source)

    print(f"Query: {args.query}")
    print(f"Document: {args.document} ({doc_id})")
    print(f"Database: {args.db_source}")
    print()

    embedding, _ = _generate_query_embedding_vector(args.query, token=api_key)
    if not embedding:
        print("ERROR: Failed to generate query embedding")
        sys.exit(1)

    result = execute_file_research_sync(
        research_statement=args.query,
        document_ids=[doc_id],
        db_source=args.db_source,
        research_context={
            "token": api_key,
            "query_embedding": embedding,
        },
    )

    retrieval_paths = result.get("retrieval_paths", {})
    for doc_name, path in retrieval_paths.items():
        print(f"Retrieval path: {path} ({doc_name})")

    findings = result.get("findings", [])
    print(f"\nFindings ({len(findings)}):")
    for finding in findings:
        page = finding.get("page", "?")
        content = finding.get("finding", "")
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"  [p{page}] {preview}")

    print(f"\nStatus: {result.get('status_summary', 'N/A')}")


if __name__ == "__main__":
    main()
