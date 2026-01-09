#!/usr/bin/env python3
"""
Full Local IRIS Integration Test

This script tests the complete IRIS pipeline using local PostgreSQL
and OpenAI API. It exercises:
- Router agent (decide research vs direct response)
- Clarifier agent (extract research statement)
- Planner agent (select databases)
- Database subagents (catalog_search for internal, semantic_search for external)
- Summarizer (format response with citations)

Usage:
    export OPENAI_API_KEY='sk-...'
    python test_full_local.py

Prerequisites:
    - Local PostgreSQL with sample data (via populate_local_db.py)
    - OpenAI API key
"""

import os
import sys
import time
import logging

# =============================================================================
# ENVIRONMENT SETUP (must happen before any iris imports)
# =============================================================================

# Point to OpenAI instead of RBC Azure
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"

# Use cost-effective models
os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1"
os.environ["IRIS_MODEL_EMBEDDING"] = "text-embedding-3-large"

# Local PostgreSQL config
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = os.getenv(
    "VECTOR_POSTGRES_DB_USERNAME", "alexwday"
)
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

# Skip SSL cert expiry check
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"

# Logging
os.environ["IRIS_LOG_LEVEL"] = "INFO"

# =============================================================================
# MONKEY PATCHES (must happen before iris imports)
# =============================================================================

# Add project root to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Import modules to patch
import services.src.connections.oauth as oauth_setup
import services.src.connections.postgres as db_config

# Patch yaml.safe_load to limit max_tokens for gpt-4o-mini compatibility
import yaml

_original_safe_load = yaml.safe_load


def _patched_safe_load(stream):
    """Patch yaml.safe_load to cap max_tokens at 16000 for gpt-4o-mini."""
    result = _original_safe_load(stream)
    if isinstance(result, dict):
        # Cap max_tokens in model config
        if "model" in result and isinstance(result["model"], dict):
            if result["model"].get("max_tokens", 0) > 16000:
                result["model"]["max_tokens"] = 16000
    return result


yaml.safe_load = _patched_safe_load


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

    hosts_list = hosts.split(",")
    port = params.get("port")
    database = params.get("dbname")
    user = params.get("user")
    password = params.get("password")

    if "," in str(port):
        ports = port.split(",")
        if len(ports) != len(hosts_list):
            raise ValueError("The number of ports must match the number of hosts.")
    else:
        ports = [port] * len(hosts_list)

    host_port_pairs = [f"{host}:{p}" for host, p in zip(hosts_list, ports)]

    if for_sqlalchemy:
        primary_host_port = host_port_pairs[0]
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


# Apply patches
oauth_setup.setup_oauth = setup_oauth_local
db_config.construct_dsn = construct_dsn_no_ssl

# =============================================================================
# NOW SAFE TO IMPORT IRIS MODULES
# =============================================================================

from services.src.utils.logging_format import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

# =============================================================================
# TEST CASES
# =============================================================================


def test_direct_response():
    """Test: Simple greeting should get direct response (no database)."""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("TEST 1: Direct Response (Greeting)")
    print("=" * 60)

    conversation = {
        "messages": [{"role": "user", "content": "Hello! What can you help me with?"}]
    }

    print("\nUser: Hello! What can you help me with?")
    print("\nIRIS Response:")
    print("-" * 40)

    response_text = ""
    start_time = time.time()

    try:
        for chunk in model(conversation):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk
            elif isinstance(chunk, dict) and "usage_details" in chunk:
                pass  # Usage info at end of stream

        elapsed = time.time() - start_time
        print(f"\n-" * 40)
        print(f"Time: {elapsed:.1f}s | Length: {len(response_text)} chars")

        # Verify it didn't try to do research
        success = len(response_text) > 50 and "database" not in response_text.lower()
        print(f"\nResult: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_internal_research():
    """Test: Query about RBC policy should search internal databases."""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("TEST 2: Internal Database Research (CAPM Policy)")
    print("=" * 60)

    conversation = {
        "messages": [
            {
                "role": "user",
                "content": "What is RBC's policy on lease classification under IFRS 16?",
            }
        ]
    }

    print("\nUser: What is RBC's policy on lease classification under IFRS 16?")
    print("\nIRIS Response:")
    print("-" * 40)

    response_text = ""
    start_time = time.time()

    try:
        for chunk in model(conversation):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk
            elif isinstance(chunk, dict) and "usage_details" in chunk:
                pass

        elapsed = time.time() - start_time
        print(f"\n-" * 40)
        print(f"Time: {elapsed:.1f}s | Length: {len(response_text)} chars")

        # Check for signs of database research
        has_content = len(response_text) > 100
        mentions_ifrs = (
            "ifrs" in response_text.lower() or "lease" in response_text.lower()
        )

        success = has_content and mentions_ifrs
        print(f"\nResult: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_external_research():
    """Test: Query about external guidance should search semantic search."""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("TEST 3: External Database Research (EY Guidance)")
    print("=" * 60)

    conversation = {
        "messages": [
            {
                "role": "user",
                "content": "What does EY's guidance say about identifying whether a contract contains a lease?",
            }
        ]
    }

    print(
        "\nUser: What does EY's guidance say about identifying whether a contract contains a lease?"
    )
    print("\nIRIS Response:")
    print("-" * 40)

    response_text = ""
    start_time = time.time()

    try:
        for chunk in model(conversation):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk
            elif isinstance(chunk, dict) and "usage_details" in chunk:
                pass

        elapsed = time.time() - start_time
        print(f"\n-" * 40)
        print(f"Time: {elapsed:.1f}s | Length: {len(response_text)} chars")

        # Check for external research signs
        has_content = len(response_text) > 100
        mentions_lease = "lease" in response_text.lower()

        success = has_content and mentions_lease
        print(f"\nResult: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_followup_conversation():
    """Test: Follow-up questions should use conversation context."""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("TEST 4: Follow-up Conversation")
    print("=" * 60)

    # Multi-turn conversation
    conversation = {
        "messages": [
            {"role": "user", "content": "What is IFRS 15?"},
            {
                "role": "assistant",
                "content": "IFRS 15 is the International Financial Reporting Standard for Revenue from Contracts with Customers. It establishes a five-step model for recognizing revenue.",
            },
            {
                "role": "user",
                "content": "Can you remind me what you just said about it?",
            },
        ]
    }

    print("\nUser: What is IFRS 15?")
    print("Assistant: IFRS 15 is the International Financial Reporting Standard...")
    print("User: Can you remind me what you just said about it?")
    print("\nIRIS Response:")
    print("-" * 40)

    response_text = ""
    start_time = time.time()

    try:
        for chunk in model(conversation):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk
            elif isinstance(chunk, dict) and "usage_details" in chunk:
                pass

        elapsed = time.time() - start_time
        print(f"\n-" * 40)
        print(f"Time: {elapsed:.1f}s | Length: {len(response_text)} chars")

        # Should reference IFRS 15 from context
        has_content = len(response_text) > 50
        references_context = (
            "ifrs 15" in response_text.lower() or "revenue" in response_text.lower()
        )

        success = has_content and references_context
        print(f"\nResult: {'PASS' if success else 'FAIL'}")
        return success

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_database_connection():
    """Verify local database is accessible and has data."""
    print("\n" + "=" * 60)
    print("VERIFYING DATABASE CONNECTION")
    print("=" * 60)

    try:
        import psycopg2
        from pgvector.psycopg2 import register_vector

        conn = psycopg2.connect(
            host="localhost",
            port="34532",
            dbname="finance-dev",
            user=os.getenv("VECTOR_POSTGRES_DB_USERNAME", "alexwday"),
            password=os.getenv("VECTOR_POSTGRES_DB_PASSWORD", ""),
        )
        register_vector(conn)

        with conn.cursor() as cur:
            # Check apg_catalog
            cur.execute("SELECT COUNT(*) FROM apg_catalog")
            catalog_count = cur.fetchone()[0]

            # Check apg_content
            cur.execute("SELECT COUNT(*) FROM apg_content")
            content_count = cur.fetchone()[0]

            # Check iris_semantic_search
            cur.execute("SELECT COUNT(*) FROM iris_semantic_search")
            semantic_count = cur.fetchone()[0]

        conn.close()

        print(f"\nDatabase: finance-dev @ localhost:34532")
        print(f"  - apg_catalog: {catalog_count} entries")
        print(f"  - apg_content: {content_count} sections")
        print(f"  - iris_semantic_search: {semantic_count} chunks")

        if catalog_count == 0 or content_count == 0:
            print("\nWARNING: No sample data found!")
            print("Run populate_local_db.py first to generate sample data.")
            return False

        print("\nDatabase connection: OK")
        return True

    except Exception as e:
        print(f"\nERROR: Could not connect to database: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running on port 34532")
        print("  2. Ensure 'finance-dev' database exists")
        print("  3. Run setup_local_db.sql to create tables")
        print("  4. Run populate_local_db.py to add sample data")
        return False


# =============================================================================
# MAIN
# =============================================================================


def main():
    """Main test runner."""
    print("=" * 60)
    print("IRIS FULL LOCAL INTEGRATION TEST")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OPENAI_API_KEY environment variable not set")
        print("Usage: export OPENAI_API_KEY='sk-...'")
        return 1

    print(f"\nOpenAI API Key: {api_key[:12]}...")
    print(f"Models: gpt-4o-mini (small/large), text-embedding-3-large")
    print(f"Database: finance-dev @ localhost:34532")

    # Verify database first
    if not verify_database_connection():
        return 1

    # Run tests
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60)

    results = {}

    # Test 1: Direct response
    results["Direct Response"] = test_direct_response()

    # Test 2: Internal database research
    results["Internal Research"] = test_internal_research()

    # Test 3: External database research
    results["External Research"] = test_external_research()

    # Test 4: Follow-up conversation
    results["Follow-up Conversation"] = test_followup_conversation()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "✓" if passed else "✗"
        print(f"  {icon} {status} - {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour local IRIS environment is fully functional.")
        print("You can now develop and test enhancements locally.")
        return 0
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED")
        print("=" * 60)
        print("\nCheck the error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
