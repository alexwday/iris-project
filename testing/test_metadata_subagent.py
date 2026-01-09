#!/usr/bin/env python3
"""
Test script for the Metadata Subagent.

Tests Stage 1 of the cascading retrieval architecture:
- Document metadata retrieval from iris_document_metadata
- Top chunk fetching from iris_document_chunks
- LLM decision making (answer_from_metadata vs request_file_research)

Usage:
    python testing/test_metadata_subagent.py
"""

import os
import subprocess
import sys

# =============================================================================
# ENVIRONMENT SETUP (must happen before any iris imports)
# =============================================================================

# Get current user for database connection
current_user = subprocess.check_output(["whoami"]).decode().strip()

# Point to OpenAI instead of RBC Azure
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"

# Use cost-effective models
os.environ["IRIS_MODEL_SMALL"] = "gpt-4o-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4o-mini"
os.environ["IRIS_MODEL_EMBEDDING"] = "text-embedding-3-large"

# Local PostgreSQL config
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = os.getenv(
    "VECTOR_POSTGRES_DB_USERNAME", current_user
)
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

# Skip SSL cert expiry check
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"
os.environ["RBC_ENVIRONMENT"] = "local"

# Check for OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# =============================================================================
# MONKEY PATCHES FOR LOCAL DEVELOPMENT
# =============================================================================

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import modules to patch
import services.src.connections.oauth as oauth_setup
import services.src.connections.postgres as db_config


def setup_oauth_local():
    """Return OpenAI API key instead of doing OAuth."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key


def construct_dsn_no_ssl(params: dict, for_sqlalchemy=True):
    """Modified DSN constructor that disables SSL for local PostgreSQL."""
    hosts = params.get("host")
    if not hosts:
        raise ValueError("Host is not set or is empty.")

    hosts_list = hosts.split(",") if isinstance(hosts, str) else hosts
    port = params.get("port")
    database = params.get("dbname")
    user = params.get("user")
    password = params.get("password")

    if for_sqlalchemy:
        primary_host_port = f"{hosts_list[0]}:{port}"
        dsn = (
            f"postgresql+psycopg2://{user}:{password}@{primary_host_port}/{database}?"
            f"sslmode=disable&target_session_attrs=read-write"
        )
    else:
        dsn = (
            f"dbname='{database}' user='{user}' password='{password}' "
            f"host='{','.join(hosts_list)}' port='{port}' sslmode='disable' "
            f"target_session_attrs='read-write'"
        )

    return dsn


# Apply patches BEFORE importing IRIS modules
oauth_setup.setup_oauth = setup_oauth_local
db_config.construct_dsn = construct_dsn_no_ssl

# =============================================================================
# NOW SAFE TO IMPORT IRIS MODULES
# =============================================================================
from services.src.agent.tools.metadata_subagent import (
    query_metadata_sync,
    MetadataSubagentResult,
)


def test_internal_database():
    """Test metadata subagent with internal database."""
    print("\n" + "=" * 60)
    print("TEST: Internal Database (internal_capm)")
    print("=" * 60)

    result = query_metadata_sync(
        research_statement="What guidance is available on revenue recognition policies?",
        db_source="internal_capm",
        token=None,
    )

    print(f"\nStatus: {result['status_summary']}")
    print(f"Documents found: {len(result['documents'])}")
    print(f"Decision action: {result['decision']['action']}")
    print(f"Decision reasoning: {result['decision']['reasoning'][:200]}...")

    if result["decision"]["action"] == "answer_from_metadata":
        print(f"\nResponse preview: {result['decision']['response'][:300]}...")
    else:
        print(f"Selected files: {result['decision']['selected_files']}")

    # Verify structure
    assert "decision" in result
    assert "documents" in result
    assert "status_summary" in result
    assert "db_source" in result
    assert result["db_source"] == "internal_capm"

    print("\n✓ Internal database test PASSED")
    return result


def test_external_database():
    """Test metadata subagent with external database."""
    print("\n" + "=" * 60)
    print("TEST: External Database (external_ey)")
    print("=" * 60)

    result = query_metadata_sync(
        research_statement="What are the key requirements for lease classification under IFRS 16?",
        db_source="external_ey",
        token=None,
    )

    print(f"\nStatus: {result['status_summary']}")
    print(f"Documents found: {len(result['documents'])}")
    print(f"Decision action: {result['decision']['action']}")
    print(f"Decision reasoning: {result['decision']['reasoning'][:200]}...")

    if result["decision"]["action"] == "answer_from_metadata":
        print(f"\nResponse preview: {result['decision']['response'][:300]}...")
    else:
        print(f"Selected files: {result['decision']['selected_files']}")

    print("\n✓ External database test PASSED")
    return result


def test_empty_database():
    """Test metadata subagent with database that has no matching docs."""
    print("\n" + "=" * 60)
    print("TEST: Database with no matching documents")
    print("=" * 60)

    result = query_metadata_sync(
        research_statement="Quantum computing accounting standards",  # Unlikely to match
        db_source="internal_par",
        token=None,
    )

    print(f"\nStatus: {result['status_summary']}")
    print(f"Documents found: {len(result['documents'])}")
    print(f"Decision action: {result['decision']['action']}")

    print("\n✓ Empty result test PASSED")
    return result


def main():
    """Run all metadata subagent tests."""
    print("=" * 60)
    print("METADATA SUBAGENT TEST SUITE")
    print("=" * 60)

    try:
        test_internal_database()
        test_external_database()
        test_empty_database()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
