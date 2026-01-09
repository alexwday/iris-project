#!/usr/bin/env python3
"""
Populate iris_database_registry table from AVAILABLE_DATABASES

Part of IRIS Enhancement: Universal Cascading Retrieval Architecture
This script migrates database configurations from the hardcoded AVAILABLE_DATABASES
dict to the PostgreSQL iris_database_registry table.

Usage:
    python populate_database_registry.py
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# =============================================================================
# ENVIRONMENT SETUP (must happen before config imports)
# =============================================================================
# Override any placeholder values from .env with local testing defaults
# This is needed because .env may contain "your_db_username_here" placeholders

# Get current user for database connection
try:
    current_user = subprocess.check_output(["whoami"]).decode().strip()
except Exception:
    current_user = "postgres"

# Set local PostgreSQL connection if not already properly set
if os.getenv("VECTOR_POSTGRES_DB_USERNAME", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_USERNAME"] = current_user
if os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = ""
if os.getenv("VECTOR_POSTGRES_DB_HOST", "").startswith("your_"):
    os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"

# =============================================================================
# NOW SAFE TO IMPORT
# =============================================================================

# Add parent directory to path to access config and services
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import Json

# Import from archived file (one-time population script)
# The AVAILABLE_DATABASES dict is kept in the archived file for reference
import sys

sys.path.insert(0, str(project_root / "notes" / "prompts"))
from database_statement import AVAILABLE_DATABASES
from config.config import Config

# Initialize config to get AD group mapping
config = Config()

# =============================================================================
# RESEARCH CONFIG TEMPLATES
# =============================================================================
# Different database types may need different research configurations
# Based on notes/NEW_DATABASE_REGISTRY_SCHEMA.md

# High-volume databases (many documents, need more aggressive batching)
HIGH_VOLUME_RESEARCH_CONFIG = {
    "batch_size": 10,
    "max_selected_files": 15,
    "top_chunks_in_catalog_selection": 1,  # Path A: file_selection mode
    "top_chunks_in_metadata_research": 3,  # Path B/C: metadata_research mode
    "page_threshold_for_full_content": 150,
    "enable_db_wide_deep_research": True,  # Allow Path B (vs metadata-only Path C)
}

# Domain-specific databases (fewer documents, allow deeper research)
DOMAIN_SPECIFIC_RESEARCH_CONFIG = {
    "batch_size": 10,
    "max_selected_files": 10,
    "top_chunks_in_catalog_selection": 1,  # Path A: file_selection mode
    "top_chunks_in_metadata_research": 3,  # Path B/C: metadata_research mode
    "page_threshold_for_full_content": 150,
    "enable_db_wide_deep_research": True,  # Allow Path B (vs metadata-only Path C)
}

# External authoritative sources (large documents, need careful chunking)
EXTERNAL_AUTHORITATIVE_RESEARCH_CONFIG = {
    "batch_size": 10,
    "max_selected_files": 8,
    "top_chunks_in_catalog_selection": 2,  # Path A: more context for large docs
    "top_chunks_in_metadata_research": 3,  # Path B/C: metadata_research mode
    "page_threshold_for_full_content": 100,
    "enable_db_wide_deep_research": True,  # Allow Path B (vs metadata-only Path C)
}

# Map database sources to their appropriate research config
DB_RESEARCH_CONFIG_MAP = {
    # High-volume internal databases
    "internal_capm": HIGH_VOLUME_RESEARCH_CONFIG,
    "internal_wiki": HIGH_VOLUME_RESEARCH_CONFIG,
    "internal_memos": HIGH_VOLUME_RESEARCH_CONFIG,
    # Domain-specific internal databases
    "internal_par": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_aio": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_esg": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_cheatsheets": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_ext_reporting_and_disclosure": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_global_finance_standards": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_management_reporting": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_process_and_controls": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_sab_99": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_intragroup_memos": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    "internal_pafe": DOMAIN_SPECIFIC_RESEARCH_CONFIG,
    # External authoritative sources
    "external_ey": EXTERNAL_AUTHORITATIVE_RESEARCH_CONFIG,
    "external_iasb": EXTERNAL_AUTHORITATIVE_RESEARCH_CONFIG,
}

# Questions mapping from database_statement.py
questions_mapping = {
    "external_ey": [],
    "external_iasb": [
        "Under IFRS, what are examples of temporary differences that lead to a deferred tax liability?",
        "Under IFRS, what are the presentation requirements for compound financial instruments? Please specify the relevant standard and sections.",
    ],
    "internal_cheatsheets": [],
    "internal_wiki": [],
    "internal_memos": [],
    "internal_capm": [
        "What is the IFRS and U.S. GAAP difference on firm commitment related to hedging?",
        "Is a call option in a finanical instrument an embedded derivative?",
        "What threshold is considered to be probable under IFRS?",
        "What are the main criteria to derecognize a financial asset under IFRS?",
    ],
    "internal_par": [
        "What would the approval level be if i had a Contract PAR greater than $200MM?",
        "Who is responsible for the fulfillment of all monitoring, reporting, and follow up of the PAR?",
        "According to RBC PAR when is an addendum required?",
        "How do I know if my PAR requires a GE or GOCx meeting?",
    ],
    "internal_aio": [
        "What type of business relationships are acceptable with an external auditor?",
        "What types of financial information are required to be disclosed to external parties?",
        "What arrangements are prohibited under joint marketing and co-branding with external auditors?",
        "What are examples of external parties?",
    ],
    "internal_esg": [
        "If something isn't material should it still go into the Sustainability Report?",
        "Is there a threshold for materiality?",
        "How to treat measurement uncertainty in the ESG framework?",
        "What are the ESG guidelines for revising materiality from prior reporting periods?",
    ],
    "internal_ext_reporting_and_disclosure": [
        "According to the disclosure policy: Who are authorized spokespersons?",
        "What guidelines should be followed for announcements that are not material?",
        "Can an RBC employee speak at a conference during quiet period?",
        "Which teams must review forward-looking information before it's disclosed?",
    ],
    "internal_global_finance_standards": [
        "What are the minimum standards for Non-Interest Expenses in COA reporting?",
        "What is RBC's global FX rate policy?",
        "What are examples of regulatory reports RBC provides OSFI?",
        "What are requirements for resident and non-resident transactions?",
    ],
    "internal_management_reporting": [
        "What are the major performance measurements for management reporting at RBC?",
        "What are the processes for funds transfer pricing?",
        "How are FTE numbers calculated?",
        "How does RBC do rounding for management reporting purposes?",
    ],
    "internal_process_and_controls": [
        "What are the requirements of RBC's internal controls policy?",
        "What is the top down risk based approach in the ICFR policy?",
        "What are the standardized abbreviations for the Chart of Accounts?",
        "How does RBC apply it's ICMP policy for Control Activities?",
    ],
    "internal_sab_99": [
        "What is the most common root cause?",
        "How many errors impacted Deposits?",
        "How many have EUDA related issues?",
    ],
}


def build_db_description(db_info):
    """Build detailed description from available database info."""
    description = db_info.get("description", "")
    content_type = db_info.get("content_type", "")
    use_when = db_info.get("use_when", "")
    query_type = db_info.get("query_type", "")

    # Build formatted description
    desc_parts = []

    # Content section
    desc_parts.append(f"**Content:** {description}. {content_type}.")

    # Extract tier/priority from use_when (usually at the start)
    if (
        "Tier" in use_when
        or "Primary" in use_when
        or "Supplementary" in use_when
        or "Authoritative" in use_when
    ):
        # Extract the tier/priority section (before "**Strategy:**" or first period)
        tier_section = use_when.split("**Strategy:**")[0].strip()
        if ":" in tier_section:
            tier_text = tier_section.split(":", 1)[0].strip()
            desc_parts.append(f"\n\n**Tier/Priority:** {tier_text}")

    # Strategy and when to use
    desc_parts.append(f"\n\n**Usage Guidance:** {use_when}")

    # Query type
    desc_parts.append(f"\n\n**Query Type:** {query_type}")

    return "".join(desc_parts)


def get_ad_groups_for_database(db_source, ad_group_mapping):
    """Reverse lookup: find which AD groups have access to this database."""
    groups = []
    for ad_group, db_list in ad_group_mapping.items():
        if db_source in db_list:
            groups.append(ad_group.strip())
    return groups if groups else None


def get_research_config(db_source: str) -> dict:
    """Get the appropriate research config for a database."""
    return DB_RESEARCH_CONFIG_MAP.get(db_source, DOMAIN_SPECIFIC_RESEARCH_CONFIG)


def populate_registry():
    """Populate iris_database_registry table from AVAILABLE_DATABASES."""

    # Get AD group mapping - handle case where config cannot connect
    try:
        ad_group_mapping = config.get_ad_group_to_db_mapping()
    except Exception as e:
        print(f"Warning: Could not get AD group mapping: {e}")
        print("Continuing with empty AD group mapping...")
        ad_group_mapping = {}

    # Connect to local PostgreSQL (env vars already set at module load time)
    conn = psycopg2.connect(
        host="localhost",
        port=34532,
        database="finance-dev",
        user=current_user,
        password="",
    )

    try:
        cur = conn.cursor()

        print(
            f"Populating iris_database_registry with {len(AVAILABLE_DATABASES)} databases..."
        )
        print(f"Using research config templates based on database type\n")

        for db_source, db_info in AVAILABLE_DATABASES.items():
            # Extract fields
            db_name = db_info.get("name", "")
            db_summary = db_info.get("description", "")
            db_description = build_db_description(db_info)

            # Get research config for this database type
            research_config = get_research_config(db_source)
            research_config_json = Json(research_config)

            # Sample questions
            sample_questions = questions_mapping.get(db_source, [])
            sample_questions_json = Json(sample_questions) if sample_questions else None

            # AD groups
            ad_groups = get_ad_groups_for_database(db_source, ad_group_mapping)

            # Default search modes
            search_modes = ["catalog", "semantic"]

            # Insert row
            cur.execute(
                """
                INSERT INTO iris_database_registry (
                    db_source, db_name, db_summary, db_description,
                    research_config, search_modes, sample_questions, enabled, ad_groups
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (db_source) DO UPDATE SET
                    db_name = EXCLUDED.db_name,
                    db_summary = EXCLUDED.db_summary,
                    db_description = EXCLUDED.db_description,
                    research_config = EXCLUDED.research_config,
                    search_modes = EXCLUDED.search_modes,
                    sample_questions = EXCLUDED.sample_questions,
                    enabled = EXCLUDED.enabled,
                    ad_groups = EXCLUDED.ad_groups,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    db_source,
                    db_name,
                    db_summary,
                    db_description,
                    research_config_json,
                    search_modes,
                    sample_questions_json,
                    True,  # enabled
                    ad_groups,
                ),
            )

            # Determine config type for display
            if research_config == HIGH_VOLUME_RESEARCH_CONFIG:
                config_type = "high-volume"
            elif research_config == EXTERNAL_AUTHORITATIVE_RESEARCH_CONFIG:
                config_type = "external-auth"
            else:
                config_type = "domain-specific"

            print(f"  ✓ {db_source}: {db_name} [{config_type}]")

        conn.commit()
        print(f"\n✅ Successfully populated {len(AVAILABLE_DATABASES)} databases")

        # Show summary
        cur.execute("SELECT COUNT(*) FROM iris_database_registry")
        count = cur.fetchone()[0]
        print(f"Total rows in iris_database_registry: {count}")

        # Show sample of research_config
        cur.execute(
            """
            SELECT db_source, research_config->>'batch_size' as batch_size,
                   research_config->>'max_selected_files' as max_files
            FROM iris_database_registry
            LIMIT 3
        """
        )
        rows = cur.fetchall()
        print(f"\nSample research_config values:")
        for row in rows:
            print(f"  {row[0]}: batch_size={row[1]}, max_selected_files={row[2]}")

        cur.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    populate_registry()
