#!/usr/bin/env python3
"""
Test script for Cascading Retrieval Architecture.

Tests the two-stage retrieval flow:
- Stage 1: Metadata Subagent (document summaries + top chunks)
- Stage 2: File Research Subagent (deep document analysis)

This script validates that:
1. Simple queries can be answered from metadata alone (Stage 1 only)
2. Complex queries trigger Stage 2 file research
3. Multi-database queries work correctly
4. The summarizer properly synthesizes results

Usage:
    python testing/test_cascading_retrieval.py
"""

import os
import subprocess
import sys
import time
import json

# =============================================================================
# ENVIRONMENT SETUP (must happen before any iris imports)
# =============================================================================

current_user = subprocess.check_output(["whoami"]).decode().strip()

os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1"
os.environ["IRIS_MODEL_EMBEDDING"] = "text-embedding-3-large"
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = os.getenv(
    "VECTOR_POSTGRES_DB_USERNAME", current_user
)
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"
os.environ["RBC_ENVIRONMENT"] = "local"

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# =============================================================================
# MONKEY PATCHES FOR LOCAL DEVELOPMENT
# =============================================================================

import services.src.connections.oauth as oauth_setup
import services.src.connections.postgres as db_config


def setup_oauth_local():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key


def construct_dsn_no_ssl(params: dict, for_sqlalchemy=True):
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


oauth_setup.setup_oauth = setup_oauth_local
db_config.construct_dsn = construct_dsn_no_ssl

# =============================================================================
# TEST CASES
# =============================================================================

# Each test case has:
# - name: Display name
# - query: User question
# - expected_behavior: What should happen
# - validation: Function to check if response is valid

TEST_CASES = [
    {
        "name": "1. Direct Response - Greeting",
        "query": "Hello!",
        "expected_behavior": "Direct response without database research",
        "validate": lambda r: len(r) > 20
        and "Research Plan" not in r
        and "📋" not in r,
    },
    # --- STAGE 1 TESTS: Metadata-Only Responses ---
    {
        "name": "2. Metadata-Only - List CAPM Documents",
        "query": "What accounting policy documents do we have in the internal CAPM database?",
        "expected_behavior": "Answer from metadata summaries (Stage 1 only)",
        "validate": lambda r: (
            "Answered from" in r  # Key indicator of metadata-only response
            and (
                "lease" in r.lower()
                or "revenue" in r.lower()
                or "financial" in r.lower()
            )
        ),
    },
    {
        "name": "3. Metadata-Only - Describe PAR Memos",
        "query": "What topics are covered in our internal PAR memos?",
        "expected_behavior": "Answer from metadata summaries (Stage 1 only)",
        "validate": lambda r: (
            "Answered from" in r and ("cloud" in r.lower() or "crypto" in r.lower())
        ),
    },
    # --- STAGE 2 TESTS: File Research Responses ---
    {
        "name": "4. File Research - Lease Classification",
        "query": "According to our internal policy, what is the definition of a lease under IFRS 16?",
        "expected_behavior": "Query internal_capm, find Lease Accounting Policy (Stage 2)",
        "validate": lambda r: (
            "lease" in r.lower()
            and (
                "ifrs 16" in r.lower()
                or "right to control" in r.lower()
                or "identified asset" in r.lower()
            )
        ),
    },
    {
        "name": "5. File Research - Revenue Recognition",
        "query": "What are the five steps for revenue recognition under our internal policy?",
        "expected_behavior": "Query internal_capm, find Revenue Recognition Policy (Stage 2)",
        "validate": lambda r: (
            "revenue" in r.lower()
            and ("five" in r.lower() or "5" in r or "step" in r.lower())
        ),
    },
    {
        "name": "6. File Research - Cloud Computing",
        "query": "What is the accounting treatment for cloud computing arrangements according to our PAR guidance?",
        "expected_behavior": "Query internal_par, find PAR 2024-001 (Stage 2)",
        "validate": lambda r: (
            "cloud" in r.lower()
            and (
                "service" in r.lower()
                or "intangible" in r.lower()
                or "ifrs" in r.lower()
            )
        ),
    },
    {
        "name": "7. File Research - Crypto Assets",
        "query": "According to our internal PAR guidance, how should cryptocurrency holdings be classified under IFRS?",
        "expected_behavior": "Query internal_par, find PAR 2024-002 (Stage 2)",
        "validate": lambda r: (
            ("crypto" in r.lower() or "cryptocurrency" in r.lower())
            and (
                "intangible" in r.lower()
                or "fair value" in r.lower()
                or "ias 38" in r.lower()
            )
        ),
    },
    {
        "name": "8. File Research - EY Lease Identification",
        "query": "What does EY's IFRS 16 guidance say about identifying whether a contract contains a lease?",
        "expected_behavior": "Query external_ey, find EY Leases document (Stage 2)",
        "validate": lambda r: (
            "lease" in r.lower()
            and (
                "identified asset" in r.lower()
                or "control" in r.lower()
                or "contract" in r.lower()
            )
        ),
    },
    {
        "name": "9. File Research - EY Right-of-Use Asset",
        "query": "How is a right-of-use asset measured at initial recognition according to EY guidance?",
        "expected_behavior": "Query external_ey, find ROU asset guidance (Stage 2)",
        "validate": lambda r: (
            ("right-of-use" in r.lower() or "rou" in r.lower())
            and (
                "initial" in r.lower()
                or "measurement" in r.lower()
                or "cost" in r.lower()
            )
        ),
    },
    {
        "name": "10. File Research - PwC Revenue Model",
        "query": "What are the five steps in the IFRS 15 revenue recognition model according to the PwC guide? Provide an overview of each step.",
        "expected_behavior": "Query external_iasb, find PwC Revenue Guide (Stage 2)",
        "validate": lambda r: (
            "revenue" in r.lower()
            and (
                "step" in r.lower()
                or "contract" in r.lower()
                or "performance" in r.lower()
            )
        ),
    },
    {
        "name": "11. File Research - PwC Variable Consideration",
        "query": "What guidance does PwC provide on estimating variable consideration under IFRS 15?",
        "expected_behavior": "Query external_iasb, find variable consideration content (Stage 2)",
        "validate": lambda r: (
            "variable" in r.lower()
            and (
                "consideration" in r.lower()
                or "estimate" in r.lower()
                or "constraint" in r.lower()
            )
        ),
    },
    {
        "name": "12. Multi-DB Query - Leases Comparison",
        "query": "Compare the lease identification criteria from our internal policy with EY's external guidance.",
        "expected_behavior": "Query both internal_capm and external_ey (Stage 2 on both)",
        "validate": lambda r: (
            "lease" in r.lower()
            and len(r) > 500  # Should have substantial content from multiple sources
        ),
    },
]


def run_test(test_case: dict) -> dict:
    """Run a single test case and return results."""
    from services.src.chat_model.model import model

    print(f"\n{'='*70}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*70}")
    print(f"Query: {test_case['query']}")
    print(f"Expected: {test_case['expected_behavior']}")
    print("-" * 70)

    conversation = {"messages": [{"role": "user", "content": test_case["query"]}]}

    response_text = ""
    start_time = time.time()

    try:
        for chunk in model(conversation):
            if isinstance(chunk, str):
                response_text += chunk
            elif isinstance(chunk, dict) and "usage_details" in chunk:
                pass

        elapsed = time.time() - start_time

        # Truncate response for display
        display_response = (
            response_text[:800] + "..." if len(response_text) > 800 else response_text
        )
        print(f"\nResponse Preview:\n{display_response}")
        print(f"\n[Time: {elapsed:.1f}s | Length: {len(response_text)} chars]")

        # Validate
        is_valid = test_case["validate"](response_text)
        status = "PASS" if is_valid else "FAIL"
        print(f"\nResult: {status}")

        return {
            "name": test_case["name"],
            "status": status,
            "elapsed": elapsed,
            "response_length": len(response_text),
            "response": response_text,
        }

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return {
            "name": test_case["name"],
            "status": "ERROR",
            "error": str(e),
        }


def main():
    """Run all test cases."""
    print("=" * 70)
    print("CASCADING RETRIEVAL ARCHITECTURE TEST SUITE")
    print("=" * 70)
    print(f"Models: gpt-4.1-mini (small), gpt-4.1 (large)")
    print(f"Database: finance-dev @ localhost:34532")
    print(f"Test Cases: {len(TEST_CASES)}")
    print("  - Stage 1 (Metadata-Only): Tests 2-3")
    print("  - Stage 2 (File Research): Tests 4-12")
    print("=" * 70)

    results = []

    for test_case in TEST_CASES:
        result = run_test(test_case)
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    for result in results:
        status_icon = (
            "✓"
            if result["status"] == "PASS"
            else "✗" if result["status"] == "FAIL" else "!"
        )
        print(f"  {status_icon} {result['status']} - {result['name']}")

    print(f"\nPassed: {passed}/{len(results)}")
    if failed > 0:
        print(f"Failed: {failed}")
    if errors > 0:
        print(f"Errors: {errors}")

    print("=" * 70)

    if passed == len(results):
        print("ALL TESTS PASSED!")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
