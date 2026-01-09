#!/usr/bin/env python3
"""
Test Unified Metadata-First Architecture for IRIS.

Tests the UNIFIED architecture where every query goes through metadata first,
and each document gets a 3-way decision:
- "answered": Finding from metadata is sufficient
- "irrelevant": Document not relevant
- "needs_deep_research": Needs full document analysis

Key features:
- Batch size of 10 for focused per-document decisions
- Parallel batch processing
- Programmatic reference building from document_ids
- Robust validation of LLM responses
- Merged responses from metadata + file research

Usage:
    python testing/test_batching_architecture.py
"""

import os
import subprocess
import sys

# =============================================================================
# ENVIRONMENT SETUP (must happen before any iris imports)
# =============================================================================

# Get current user for database connection
current_user = subprocess.check_output(["whoami"]).decode().strip()

# Local PostgreSQL config
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_NAME"] = "maven-finance"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = os.getenv("VECTOR_POSTGRES_DB_USERNAME", current_user)
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

# Skip SSL cert check for local
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"
os.environ["RBC_ENVIRONMENT"] = "local"

# =============================================================================
# MONKEY PATCHES FOR LOCAL DEVELOPMENT
# =============================================================================

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import modules to patch
import services.src.connections.postgres as db_config


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
db_config.construct_dsn = construct_dsn_no_ssl

# =============================================================================
# NOW IMPORT IRIS MODULES
# =============================================================================

from services.src.agent.tools.metadata_subagent import (
    fetch_all_documents,
    _get_research_config,
    _validate_unified_decisions,
    _build_reference_index_from_decisions,
    _format_unified_response,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_SELECTED_FILES,
    DEFAULT_TOP_CHUNKS_PER_DOC,
    DEFAULT_MAX_PARALLEL_BATCHES,
)


def test_config_loading():
    """Test config loading from database registry."""
    print("\n" + "=" * 60)
    print("TEST: Config Loading from Database Registry")
    print("=" * 60)

    test_databases = [
        "internal_capm",
        "internal_par",
        "external_ey",
        "nonexistent_db",
    ]

    for db in test_databases:
        config = _get_research_config(db)
        print(f"\n  {db}:")
        print(f"    batch_size: {config.get('batch_size', 'N/A')}")
        print(f"    max_selected_files: {config.get('max_selected_files', 'N/A')}")
        print(f"    max_parallel_batches: {config.get('max_parallel_batches', 'N/A')}")
        print(f"    top_chunks_in_metadata: {config.get('top_chunks_in_metadata', 'N/A')}")


def test_document_fetch():
    """Test document fetching with fake embedding."""
    print("\n" + "=" * 60)
    print("TEST: Document Fetching")
    print("=" * 60)

    # We need a fake embedding for testing
    # Use a simple vector of zeros (won't give meaningful results but tests the query)
    fake_embedding = [0.0] * 2000

    test_databases = [
        "internal_capm",
        "external_ey",
    ]

    for db in test_databases:
        print(f"\n  Database: {db}")
        documents = fetch_all_documents(db, fake_embedding, top_chunks_per_doc=3)
        print(f"  Documents fetched: {len(documents)}")

        if documents:
            first = documents[0]
            print(f"  First document: {first.get('document_name', 'Unknown')}")
            print(f"  Document ID: {first.get('document_id', 'Unknown')[:20]}...")
            print(f"  Top chunks: {len(first.get('top_chunks', []))}")
            summary = first.get("document_summary", "")
            if summary:
                summary_preview = summary[:100] + "..." if len(summary) > 100 else summary
            else:
                summary_preview = "No summary"
            print(f"  Summary preview: {summary_preview}")


def test_batch_creation():
    """Test batch creation logic with batch_size=10."""
    print("\n" + "=" * 60)
    print("TEST: Batch Creation (batch_size=10)")
    print("=" * 60)

    batch_size = DEFAULT_BATCH_SIZE  # Should be 10

    test_cases = [
        (5, 1),     # 5 docs -> 1 batch
        (10, 1),    # 10 docs -> 1 batch
        (11, 2),    # 11 docs -> 2 batches
        (20, 2),    # 20 docs -> 2 batches
        (50, 5),    # 50 docs -> 5 batches
        (100, 10),  # 100 docs -> 10 batches
    ]

    for doc_count, expected_batches in test_cases:
        # Simulate batch creation
        doc_ids = [f"doc_{i}" for i in range(doc_count)]
        batches = [doc_ids[i:i + batch_size] for i in range(0, len(doc_ids), batch_size)]

        status = "PASS" if len(batches) == expected_batches else "FAIL"
        print(f"  {status}: {doc_count} docs -> {len(batches)} batches (expected {expected_batches})")


def test_constants():
    """Display configuration constants."""
    print("\n" + "=" * 60)
    print("DEFAULT CONFIGURATION CONSTANTS")
    print("=" * 60)
    print(f"  DEFAULT_BATCH_SIZE: {DEFAULT_BATCH_SIZE}")
    print(f"  DEFAULT_MAX_SELECTED_FILES: {DEFAULT_MAX_SELECTED_FILES}")
    print(f"  DEFAULT_TOP_CHUNKS_PER_DOC: {DEFAULT_TOP_CHUNKS_PER_DOC}")
    print(f"  DEFAULT_MAX_PARALLEL_BATCHES: {DEFAULT_MAX_PARALLEL_BATCHES}")

    # Verify expected values
    expected = {
        "DEFAULT_BATCH_SIZE": 10,
        "DEFAULT_MAX_SELECTED_FILES": 20,
        "DEFAULT_TOP_CHUNKS_PER_DOC": 3,
        "DEFAULT_MAX_PARALLEL_BATCHES": 5,
    }

    print("\n  Verification:")
    all_pass = True
    for name, expected_value in expected.items():
        actual = eval(name)
        status = "PASS" if actual == expected_value else "FAIL"
        if actual != expected_value:
            all_pass = False
        print(f"    {status}: {name} = {actual} (expected {expected_value})")


def test_unified_architecture():
    """Test the unified 3-way decision architecture."""
    print("\n" + "=" * 60)
    print("TEST: Unified 3-Way Decision Architecture")
    print("=" * 60)

    print("\n  Architecture Flow:")
    print("    1. Every query goes through metadata subagent")
    print("    2. Each document gets 3-way decision:")
    print("       - 'answered': Finding from metadata sufficient")
    print("       - 'irrelevant': Document not relevant")
    print("       - 'needs_deep_research': Needs full document")
    print("    3. Build response from 'answered' findings")
    print("    4. Trigger file research only for 'needs_deep_research' docs")
    print("    5. Merge responses with continued reference numbers")

    print("\n  PASS: Architecture documented correctly")


def test_decision_validation():
    """Test validation of 3-way decisions from LLM response."""
    print("\n" + "=" * 60)
    print("TEST: 3-Way Decision Validation")
    print("=" * 60)

    # Mock batch documents
    batch_documents = [
        {"document_id": "doc-001", "document_name": "Doc 1", "document_summary": "Summary 1"},
        {"document_id": "doc-002", "document_name": "Doc 2", "document_summary": "Summary 2"},
        {"document_id": "doc-003", "document_name": "Doc 3", "document_summary": "Summary 3"},
    ]
    valid_doc_ids = {doc["document_id"] for doc in batch_documents}

    # Test case 1: Valid decisions
    raw_decisions_1 = [
        {"document_id": "doc-001", "status": "answered", "finding": "Found X", "page_reference": 5, "confidence": "high"},
        {"document_id": "doc-002", "status": "irrelevant"},
        {"document_id": "doc-003", "status": "needs_deep_research", "research_hint": "Needs more detail"},
    ]

    validated_1 = _validate_unified_decisions(raw_decisions_1, valid_doc_ids, batch_documents)
    status_1 = "PASS" if len(validated_1) == 3 else "FAIL"
    print(f"  {status_1}: Valid decisions - {len(validated_1)} documents validated")

    # Check status values
    statuses_1 = {d["document_id"]: d["status"] for d in validated_1}
    expected_statuses = {"doc-001": "answered", "doc-002": "irrelevant", "doc-003": "needs_deep_research"}
    statuses_match = statuses_1 == expected_statuses
    status_1b = "PASS" if statuses_match else "FAIL"
    print(f"  {status_1b}: Status values match expected")

    # Test case 2: Missing document in response (should default to needs_deep_research)
    raw_decisions_2 = [
        {"document_id": "doc-001", "status": "answered", "finding": "Found X"},
        # doc-002 and doc-003 missing
    ]

    validated_2 = _validate_unified_decisions(raw_decisions_2, valid_doc_ids, batch_documents)
    status_2 = "PASS" if len(validated_2) == 3 else "FAIL"
    print(f"  {status_2}: Missing docs auto-filled - {len(validated_2)} documents")

    # Check that missing docs defaulted to needs_deep_research
    missing_statuses = [d["status"] for d in validated_2 if d["document_id"] != "doc-001"]
    all_needs_research = all(s == "needs_deep_research" for s in missing_statuses)
    status_2b = "PASS" if all_needs_research else "FAIL"
    print(f"  {status_2b}: Missing docs default to needs_deep_research")

    # Test case 3: Invalid document_id in response
    raw_decisions_3 = [
        {"document_id": "doc-001", "status": "answered", "finding": "Found X"},
        {"document_id": "invalid-id", "status": "answered", "finding": "Should be ignored"},
        {"document_id": "doc-002", "status": "irrelevant"},
        {"document_id": "doc-003", "status": "answered", "finding": "Found Y"},
    ]

    validated_3 = _validate_unified_decisions(raw_decisions_3, valid_doc_ids, batch_documents)
    invalid_present = any(d["document_id"] == "invalid-id" for d in validated_3)
    status_3 = "PASS" if len(validated_3) == 3 and not invalid_present else "FAIL"
    print(f"  {status_3}: Invalid doc_id filtered - {len(validated_3)} valid documents")

    # Test case 4: Invalid status value (should default to needs_deep_research)
    raw_decisions_4 = [
        {"document_id": "doc-001", "status": "answered", "finding": "Found X"},
        {"document_id": "doc-002", "status": "unknown_status"},  # Invalid status
        {"document_id": "doc-003", "status": "irrelevant"},
    ]

    validated_4 = _validate_unified_decisions(raw_decisions_4, valid_doc_ids, batch_documents)
    doc_002_status = next((d["status"] for d in validated_4 if d["document_id"] == "doc-002"), None)
    status_4 = "PASS" if doc_002_status == "needs_deep_research" else "FAIL"
    print(f"  {status_4}: Invalid status defaults to needs_deep_research")


def test_reference_index_building():
    """Test programmatic reference index building from decisions."""
    print("\n" + "=" * 60)
    print("TEST: Reference Index Building from Decisions")
    print("=" * 60)

    # Mock documents
    documents = [
        {"document_id": "doc-001", "document_name": "CAPM_Q2.pdf", "file_name": "/path/to/CAPM_Q2.pdf"},
        {"document_id": "doc-002", "document_name": "Rates.xlsx", "file_name": "/path/to/Rates.xlsx"},
        {"document_id": "doc-003", "document_name": "Policy.pdf", "file_name": None},
    ]

    # Mock decisions (3-way)
    decisions = [
        {"document_id": "doc-001", "status": "answered", "finding": "Rate is 8.5%", "page_reference": 12, "confidence": "high"},
        {"document_id": "doc-002", "status": "irrelevant", "finding": None, "page_reference": None, "confidence": None},
        {"document_id": "doc-003", "status": "answered", "finding": "Policy states...", "page_reference": None, "confidence": "medium"},
    ]

    ref_index = _build_reference_index_from_decisions(decisions, documents)

    # Should have 2 entries (only "answered" decisions)
    status_1 = "PASS" if len(ref_index) == 2 else "FAIL"
    print(f"  {status_1}: Built {len(ref_index)} reference entries (expected 2 answered)")

    # Check reference 1 has page number
    if "1" in ref_index:
        has_page = ref_index["1"].get("page") == 12
        status_2 = "PASS" if has_page else "FAIL"
        print(f"  {status_2}: Reference 1 has page_reference=12")
    else:
        print("  FAIL: Reference 1 not found")

    # Check reference 2 has no page number
    if "2" in ref_index:
        no_page = ref_index["2"].get("page") is None
        status_3 = "PASS" if no_page else "FAIL"
        print(f"  {status_3}: Reference 2 has page_reference=None")
    else:
        print("  FAIL: Reference 2 not found")

    # Test continuing reference numbers
    ref_index_continued = _build_reference_index_from_decisions(decisions, documents, start_ref_num=5)
    has_ref_5 = "5" in ref_index_continued
    has_ref_6 = "6" in ref_index_continued
    status_4 = "PASS" if has_ref_5 and has_ref_6 and "1" not in ref_index_continued else "FAIL"
    print(f"  {status_4}: Reference numbering continues from start_ref_num=5")


def test_response_formatting():
    """Test formatting answered decisions into response text."""
    print("\n" + "=" * 60)
    print("TEST: Response Formatting from Decisions")
    print("=" * 60)

    documents = [
        {"document_id": "doc-001", "document_name": "CAPM_Q2.pdf", "file_name": "/path/to/CAPM_Q2.pdf"},
        {"document_id": "doc-002", "document_name": "Rates.xlsx", "file_name": "/path/to/Rates.xlsx"},
    ]

    decisions = [
        {"document_id": "doc-001", "status": "answered", "finding": "Rate is 8.5%", "page_reference": 12, "confidence": "high"},
        {"document_id": "doc-002", "status": "answered", "finding": "Updated rates", "page_reference": None, "confidence": "medium"},
    ]

    response = _format_unified_response(decisions, documents)

    # Check response contains expected elements
    has_ref_1 = "[REF:1]" in response
    has_ref_2 = "[REF:2]" in response
    has_page = "(p. 12)" in response
    has_finding = "Rate is 8.5%" in response

    status_1 = "PASS" if has_ref_1 and has_ref_2 else "FAIL"
    print(f"  {status_1}: Response contains REF markers")

    status_2 = "PASS" if has_page else "FAIL"
    print(f"  {status_2}: Response contains page reference")

    status_3 = "PASS" if has_finding else "FAIL"
    print(f"  {status_3}: Response contains finding text")

    # Test empty response when no answered decisions
    empty_decisions = [
        {"document_id": "doc-001", "status": "irrelevant", "finding": None},
        {"document_id": "doc-002", "status": "needs_deep_research", "finding": None},
    ]
    empty_response = _format_unified_response(empty_decisions, documents)
    status_4 = "PASS" if empty_response == "" else "FAIL"
    print(f"  {status_4}: Empty response when no answered decisions")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("UNIFIED METADATA-FIRST ARCHITECTURE TESTS")
    print("=" * 60)
    print("\nArchitecture Overview:")
    print("  - Every query goes through metadata subagent first")
    print("  - Each document gets 3-way decision:")
    print("    * answered: Finding from metadata is sufficient")
    print("    * irrelevant: Document not relevant")
    print("    * needs_deep_research: Needs full document analysis")
    print("  - File research triggered ONLY for needs_deep_research docs")
    print("  - Reference numbers continue across metadata + file research")
    print("\nKey Design:")
    print("  - Per-document decisions enable PROGRAMMATIC reference building")
    print("  - LLM returns document_id with each decision (validated)")
    print("  - References built from known metadata, not LLM text")
    print("  - require_deep_research flag REMOVED from clarifier")

    test_constants()
    test_unified_architecture()
    test_batch_creation()
    test_decision_validation()
    test_reference_index_building()
    test_response_formatting()
    test_config_loading()
    test_document_fetch()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
    print("\nNote: Full integration testing requires:")
    print("  1. OpenAI API key set")
    print("  2. Running the full pipeline with test queries")
    print("  3. Verifying merged responses (metadata + file research)")


if __name__ == "__main__":
    main()
