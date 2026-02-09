#!/usr/bin/env python3
"""
IRIS Initial Data Population Script for IT Deployment

This script populates the 5 IRIS tables in IT's PostgreSQL database with initial
data needed to run the IRIS pipeline. It executes SQL files from the
schemas/initial_data/ directory in the correct dependency order.

Steps:
    1. Registry (wipe + load): DELETE CASCADE then insert 16 database entries
    2. Prompts (additive upsert): Insert 8 IRIS prompts without touching others
    3. Sample data (optional): Load 3 test documents into internal_wiki

Connection is configured via environment variables matching the sync.py pattern.

Usage:
    # Full population (all 3 steps)
    python db_config/populate_initial_data.py

    # Skip sample data (registry + prompts only)
    python db_config/populate_initial_data.py --skip-sample-data

    # Dry run (show what would happen)
    python db_config/populate_initial_data.py --dry-run
"""

import argparse
import os
import sys

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
INITIAL_DATA_DIR = os.path.join(SCRIPT_DIR, "schemas", "initial_data")

REGISTRY_SQL = os.path.join(INITIAL_DATA_DIR, "iris_database_registry.sql")
PROMPTS_SQL = os.path.join(INITIAL_DATA_DIR, "iris_prompts.sql")
SAMPLE_DATA_SQL = os.path.join(INITIAL_DATA_DIR, "sample_internal_wiki.sql")


def get_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def read_sql_file(path: str) -> str:
    """Read a SQL file and return its contents."""
    with open(path, "r") as f:
        return f.read()


def step_registry(conn, dry_run: bool) -> None:
    """Wipe and reload the iris_database_registry table.

    Args:
        conn: Active psycopg2 connection.
        dry_run: If True, show plan without executing.
    """
    print("\n[Step 1/3] Registry: wipe + load iris_database_registry")
    print(f"  Source: {REGISTRY_SQL}")

    if not os.path.exists(REGISTRY_SQL):
        print(f"  ERROR: File not found: {REGISTRY_SQL}")
        sys.exit(1)

    sql = read_sql_file(REGISTRY_SQL)

    if dry_run:
        print("  [DRY RUN] Would DELETE FROM iris_database_registry CASCADE")
        print(f"  [DRY RUN] Would execute {REGISTRY_SQL} ({len(sql)} bytes)")
        return

    cur = conn.cursor()
    cur.execute("DELETE FROM iris_database_registry CASCADE")
    deleted = cur.rowcount
    print(f"  Deleted {deleted} existing registry entries (CASCADE)")

    cur.execute(sql)
    conn.commit()
    cur.close()

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM iris_database_registry")
    count = cur.fetchone()[0]
    cur.close()
    print(f"  Loaded {count} registry entries")


def step_prompts(conn, dry_run: bool) -> None:
    """Add IRIS prompts to the prompts table (additive upsert).

    Args:
        conn: Active psycopg2 connection.
        dry_run: If True, show plan without executing.
    """
    print("\n[Step 2/3] Prompts: additive upsert to prompts table")
    print(f"  Source: {PROMPTS_SQL}")

    if not os.path.exists(PROMPTS_SQL):
        print(f"  ERROR: File not found: {PROMPTS_SQL}")
        sys.exit(1)

    sql = read_sql_file(PROMPTS_SQL)

    if dry_run:
        print("  [DRY RUN] Would ensure unique constraint on (model, layer, name, version)")
        print("  [DRY RUN] Would clean up any duplicate IRIS prompts from prior failed runs")
        print(f"  [DRY RUN] Would execute {PROMPTS_SQL} ({len(sql)} bytes)")
        print("  [DRY RUN] Uses ON CONFLICT upsert - won't affect non-IRIS prompts")
        return

    cur = conn.cursor()

    cur.execute("""
        DELETE FROM prompts a USING prompts b
        WHERE a.id > b.id
          AND a.model = b.model AND a.layer = b.layer
          AND a.name = b.name AND a.version = b.version
          AND a.model = 'iris'
    """)
    dupes_removed = cur.rowcount
    if dupes_removed > 0:
        print(f"  Cleaned up {dupes_removed} duplicate IRIS prompt rows")
    conn.commit()

    cur.execute("""
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_prompts_model_layer_name_version'
    """)
    if cur.fetchone() is None:
        cur.execute("""
            ALTER TABLE prompts
            ADD CONSTRAINT uq_prompts_model_layer_name_version
            UNIQUE (model, layer, name, version)
        """)
        conn.commit()
        print("  Created unique constraint on (model, layer, name, version)")
    else:
        print("  Unique constraint already exists")

    cur.execute("SELECT COUNT(*) FROM prompts WHERE model = 'iris'")
    before = cur.fetchone()[0]

    cur.execute(sql)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM prompts WHERE model = 'iris'")
    after = cur.fetchone()[0]
    cur.close()
    print(f"  IRIS prompts: {before} -> {after}")


def step_sample_data(conn, dry_run: bool) -> None:
    """Load sample internal_wiki documents for testing.

    Args:
        conn: Active psycopg2 connection.
        dry_run: If True, show plan without executing.
    """
    print("\n[Step 3/3] Sample data: load internal_wiki test documents")
    print(f"  Source: {SAMPLE_DATA_SQL}")

    if not os.path.exists(SAMPLE_DATA_SQL):
        print(f"  ERROR: File not found: {SAMPLE_DATA_SQL}")
        print("  Run 'python db_config/export_sample_data.py' first to generate it.")
        sys.exit(1)

    sql = read_sql_file(SAMPLE_DATA_SQL)

    if dry_run:
        print(f"  [DRY RUN] Would execute {SAMPLE_DATA_SQL} ({len(sql)} bytes)")
        print("  [DRY RUN] Inserts 3 metadata rows + 18 chunk rows into internal_wiki")
        return

    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

    cur.execute(
        "SELECT COUNT(*) FROM iris_document_metadata WHERE db_source = 'internal_wiki'"
    )
    meta_count = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM iris_document_chunks WHERE db_source = 'internal_wiki'"
    )
    chunk_count = cur.fetchone()[0]
    cur.close()
    print(f"  internal_wiki: {meta_count} documents, {chunk_count} chunks")


def main():
    """Populate IRIS tables with initial data for IT deployment."""
    parser = argparse.ArgumentParser(
        description="Populate IRIS tables with initial data for IT deployment."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing.",
    )
    parser.add_argument(
        "--skip-sample-data",
        action="store_true",
        help="Skip step 3 (sample internal_wiki data).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("IRIS Initial Data Population")
    print("=" * 60)
    print(f"  Host:     {DB_HOST}")
    print(f"  Port:     {DB_PORT}")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")

    if args.dry_run:
        print(f"  Mode:     DRY RUN (no changes will be made)")
    else:
        print(f"  Mode:     LIVE")

    if args.skip_sample_data:
        print(f"  Sample:   SKIPPED (--skip-sample-data)")

    if not args.dry_run:
        print("\nConnecting to database...")
    conn = None
    if not args.dry_run:
        try:
            conn = get_connection()
            print("  Connected successfully")
        except psycopg2.OperationalError as e:
            print(f"\n  ERROR: Could not connect to database")
            print(f"  {e}")
            print("\n  Set these environment variables:")
            print("    VECTOR_POSTGRES_DB_HOST")
            print("    VECTOR_POSTGRES_DB_PORT")
            print("    VECTOR_POSTGRES_DB_NAME")
            print("    VECTOR_POSTGRES_DB_USERNAME")
            print("    VECTOR_POSTGRES_DB_PASSWORD")
            sys.exit(1)

    try:
        step_registry(conn, args.dry_run)
        step_prompts(conn, args.dry_run)

        if not args.skip_sample_data:
            step_sample_data(conn, args.dry_run)
        else:
            print("\n[Step 3/3] Sample data: SKIPPED")
    except Exception as e:
        print(f"\nERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN complete. No changes were made.")
    else:
        print("Population complete. Verify with:")
        print("  SELECT COUNT(*) FROM iris_database_registry;")
        print("  SELECT COUNT(*) FROM prompts WHERE model = 'iris';")
        if not args.skip_sample_data:
            print(
                "  SELECT COUNT(*) FROM iris_document_metadata"
                " WHERE db_source = 'internal_wiki';"
            )
            print(
                "  SELECT COUNT(*) FROM iris_document_chunks"
                " WHERE db_source = 'internal_wiki';"
            )
    print("=" * 60)


if __name__ == "__main__":
    main()
