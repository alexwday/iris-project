#!/usr/bin/env python3
"""
Export IRIS initial data for IT deployment.

Generates CSV, SQL INSERT, and PostgreSQL COPY format files for:
- iris_database_registry (all entries)
- prompts (IRIS model only, excludes doc_refresh)

Output files are created in db_config/schemas/initial_data/
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
DB_PORT = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
DB_NAME = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
DB_USER = os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres"))
DB_PASSWORD = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "schemas", "initial_data")


def get_connection():
    """Create database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def fetch_iris_prompts(conn) -> List[Dict]:
    """Fetch only IRIS model prompts (excludes doc_refresh)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                model, layer, name, version, description,
                system_prompt, user_prompt, tool_definition
            FROM prompts
            WHERE model = 'iris'
            ORDER BY layer, name
        """)
        return [dict(row) for row in cur.fetchall()]


def fetch_registry(conn) -> List[Dict]:
    """Fetch all database registry entries."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                db_source, db_name, db_summary, db_description,
                search_modes, catalog_config, semantic_config, metadata_config,
                sample_questions, enabled, ad_groups,
                batch_size, max_selected_files,
                top_chunks_in_catalog_selection, top_chunks_in_metadata_research,
                page_threshold_for_full_content, enable_db_wide_deep_research,
                metadata_context_fields, max_parallel_files, max_chunks_per_file,
                max_pages_for_full_context, max_primary_section_page_count,
                max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages
            FROM iris_database_registry
            ORDER BY db_source
        """)
        return [dict(row) for row in cur.fetchall()]


def format_pg_array(arr: Optional[List]) -> str:
    """Format Python list as PostgreSQL array literal."""
    if arr is None:
        return ""
    return "{" + ",".join(str(x) for x in arr) + "}"


def format_json(obj: Any) -> str:
    """Format object as JSON string."""
    if obj is None:
        return ""
    return json.dumps(obj, separators=(",", ":"))


def escape_sql_string(s: Optional[str]) -> str:
    """Escape string for SQL INSERT statement."""
    if s is None:
        return "NULL"
    escaped = s.replace("'", "''")
    return f"'{escaped}'"


def escape_csv_field(val: Any) -> str:
    """Escape value for CSV output."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (dict, list)):
        return json.dumps(val, separators=(",", ":"))
    return str(val)


def write_prompts_csv(prompts: List[Dict], filepath: str):
    """Write prompts to CSV file."""
    columns = [
        "model", "layer", "name", "version", "description",
        "system_prompt", "user_prompt", "tool_definition"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for row in prompts:
            csv_row = []
            for col in columns:
                val = row.get(col)
                if col == "tool_definition" and val is not None:
                    csv_row.append(json.dumps(val, indent=None, separators=(",", ":")))
                elif val is None:
                    csv_row.append("")
                else:
                    csv_row.append(str(val))
            writer.writerow(csv_row)

    print(f"  Created: {filepath}")


def write_prompts_sql(prompts: List[Dict], filepath: str):
    """Write prompts as SQL INSERT statements."""
    columns = [
        "model", "layer", "name", "version", "description",
        "system_prompt", "user_prompt", "tool_definition"
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("-- IRIS Prompts Initial Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- \n")
        f.write("-- Import with: psql -f iris_prompts.sql\n")
        f.write("-- Or run in pgAdmin/DBeaver\n")
        f.write("--\n")
        f.write("-- Note: Uses ON CONFLICT to handle re-runs safely\n\n")

        f.write("BEGIN;\n\n")

        for row in prompts:
            values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    values.append("NULL")
                elif col == "tool_definition":
                    json_str = json.dumps(val, separators=(",", ":"))
                    values.append(escape_sql_string(json_str) + "::jsonb")
                else:
                    values.append(escape_sql_string(str(val)))

            f.write(f"INSERT INTO prompts ({', '.join(columns)})\n")
            f.write(f"VALUES ({', '.join(values)})\n")
            f.write(f"ON CONFLICT (model, layer, name, version) DO UPDATE SET\n")
            f.write(f"    description = EXCLUDED.description,\n")
            f.write(f"    system_prompt = EXCLUDED.system_prompt,\n")
            f.write(f"    user_prompt = EXCLUDED.user_prompt,\n")
            f.write(f"    tool_definition = EXCLUDED.tool_definition,\n")
            f.write(f"    updated_at = CURRENT_TIMESTAMP;\n\n")

        f.write("COMMIT;\n")
        f.write(f"\n-- Inserted/Updated {len(prompts)} IRIS prompts\n")

    print(f"  Created: {filepath}")


def write_registry_csv(registry: List[Dict], filepath: str):
    """Write registry to CSV file."""
    columns = [
        "db_source", "db_name", "db_summary", "db_description",
        "search_modes", "catalog_config", "semantic_config", "metadata_config",
        "sample_questions", "enabled", "ad_groups",
        "batch_size", "max_selected_files",
        "top_chunks_in_catalog_selection", "top_chunks_in_metadata_research",
        "page_threshold_for_full_content", "enable_db_wide_deep_research",
        "metadata_context_fields", "max_parallel_files", "max_chunks_per_file",
        "max_pages_for_full_context", "max_primary_section_page_count",
        "max_subsection_page_count", "max_neighbour_chunks", "max_gap_fill_pages"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for row in registry:
            csv_row = []
            for col in columns:
                val = row.get(col)
                csv_row.append(escape_csv_field(val))
            writer.writerow(csv_row)

    print(f"  Created: {filepath}")


def write_registry_sql(registry: List[Dict], filepath: str):
    """Write registry as SQL INSERT statements."""
    columns = [
        "db_source", "db_name", "db_summary", "db_description",
        "search_modes", "catalog_config", "semantic_config", "metadata_config",
        "sample_questions", "enabled", "ad_groups",
        "batch_size", "max_selected_files",
        "top_chunks_in_catalog_selection", "top_chunks_in_metadata_research",
        "page_threshold_for_full_content", "enable_db_wide_deep_research",
        "metadata_context_fields", "max_parallel_files", "max_chunks_per_file",
        "max_pages_for_full_context", "max_primary_section_page_count",
        "max_subsection_page_count", "max_neighbour_chunks", "max_gap_fill_pages"
    ]

    array_cols = {"search_modes", "ad_groups", "metadata_context_fields"}
    json_cols = {"catalog_config", "semantic_config", "metadata_config", "sample_questions"}
    bool_cols = {"enabled", "enable_db_wide_deep_research"}

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("-- IRIS Database Registry Initial Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- \n")
        f.write("-- Import with: psql -f iris_database_registry.sql\n")
        f.write("-- Or run in pgAdmin/DBeaver\n")
        f.write("--\n")
        f.write("-- Note: Uses ON CONFLICT to handle re-runs safely\n")
        f.write("-- Note: 'test_docs' is included for testing - remove if not needed\n\n")

        f.write("BEGIN;\n\n")

        for row in registry:
            values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    values.append("NULL")
                elif col in array_cols:
                    if val:
                        arr_str = "ARRAY[" + ",".join(escape_sql_string(x) for x in val) + "]::text[]"
                        values.append(arr_str)
                    else:
                        values.append("NULL")
                elif col in json_cols:
                    if val:
                        json_str = json.dumps(val, separators=(",", ":"))
                        values.append(escape_sql_string(json_str) + "::jsonb")
                    else:
                        values.append("NULL")
                elif col in bool_cols:
                    values.append("true" if val else "false")
                elif isinstance(val, int):
                    values.append(str(val))
                else:
                    values.append(escape_sql_string(str(val)))

            # Add comment for test_docs
            if row.get("db_source") == "test_docs":
                f.write("-- TEST DATABASE: Remove this entry for production if not needed\n")

            f.write(f"INSERT INTO iris_database_registry ({', '.join(columns)})\n")
            f.write(f"VALUES (\n    {',\n    '.join(values)}\n)\n")
            f.write(f"ON CONFLICT (db_source) DO UPDATE SET\n")

            update_cols = [c for c in columns if c != "db_source"]
            update_stmts = [f"    {c} = EXCLUDED.{c}" for c in update_cols]
            update_stmts.append("    updated_at = CURRENT_TIMESTAMP")
            f.write(",\n".join(update_stmts) + ";\n\n")

        f.write("COMMIT;\n")
        f.write(f"\n-- Inserted/Updated {len(registry)} database registry entries\n")

    print(f"  Created: {filepath}")


def write_copy_format(data: List[Dict], columns: List[str], filepath: str, table_name: str):
    """Write data in PostgreSQL COPY format (tab-delimited)."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- PostgreSQL COPY format for {table_name}\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- \n")
        f.write(f"-- Import with:\n")
        f.write(f"--   \\copy {table_name}({','.join(columns)}) FROM '{os.path.basename(filepath)}' WITH (FORMAT text, NULL '\\N')\n")
        f.write("-- \n")
        f.write("-- Or use psql:\n")
        f.write(f"--   cat {os.path.basename(filepath)} | grep -v '^--' | psql -c \"\\copy {table_name}({','.join(columns)}) FROM STDIN WITH (FORMAT text, NULL '\\N')\"\n")
        f.write("--\n")

        for row in data:
            fields = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    fields.append("\\N")
                elif isinstance(val, bool):
                    fields.append("t" if val else "f")
                elif isinstance(val, list):
                    fields.append("{" + ",".join(str(x) for x in val) + "}")
                elif isinstance(val, dict):
                    fields.append(json.dumps(val, separators=(",", ":")))
                else:
                    # Escape tabs, newlines, backslashes for COPY format
                    s = str(val)
                    s = s.replace("\\", "\\\\")
                    s = s.replace("\t", "\\t")
                    s = s.replace("\n", "\\n")
                    s = s.replace("\r", "\\r")
                    fields.append(s)
            f.write("\t".join(fields) + "\n")

    print(f"  Created: {filepath}")


def main():
    """Export initial data in multiple formats."""
    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    try:
        conn = get_connection()
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # Fetch data
        print("\nFetching data...")
        prompts = fetch_iris_prompts(conn)
        registry = fetch_registry(conn)

        print(f"  Found {len(prompts)} IRIS prompts")
        print(f"  Found {len(registry)} registry entries")

        # Export prompts
        print("\nExporting prompts...")
        write_prompts_csv(prompts, os.path.join(OUTPUT_DIR, "iris_prompts.csv"))
        write_prompts_sql(prompts, os.path.join(OUTPUT_DIR, "iris_prompts.sql"))

        # Export registry
        print("\nExporting registry...")
        write_registry_csv(registry, os.path.join(OUTPUT_DIR, "iris_database_registry.csv"))
        write_registry_sql(registry, os.path.join(OUTPUT_DIR, "iris_database_registry.sql"))

        # Create README
        readme_path = os.path.join(OUTPUT_DIR, "README.md")
        with open(readme_path, "w") as f:
            f.write("# IRIS Initial Data\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Contents\n\n")
            f.write("| File | Description | Import Method |\n")
            f.write("|------|-------------|---------------|\n")
            f.write("| `iris_prompts.sql` | 8 IRIS prompts (SQL INSERT) | `psql -f iris_prompts.sql` |\n")
            f.write("| `iris_prompts.csv` | 8 IRIS prompts (CSV) | pgAdmin Import or `\\copy` |\n")
            f.write("| `iris_database_registry.sql` | 17 database configs (SQL INSERT) | `psql -f iris_database_registry.sql` |\n")
            f.write("| `iris_database_registry.csv` | 17 database configs (CSV) | pgAdmin Import or `\\copy` |\n\n")
            f.write("## Recommended Import Order\n\n")
            f.write("1. Create tables first using schema files in parent directory\n")
            f.write("2. Import `iris_database_registry.sql` (registry must exist before documents)\n")
            f.write("3. Import `iris_prompts.sql`\n\n")
            f.write("## SQL Files (Recommended)\n\n")
            f.write("The `.sql` files use `INSERT ... ON CONFLICT DO UPDATE` syntax, making them:\n")
            f.write("- Safe to re-run multiple times\n")
            f.write("- Self-contained with all escaping handled\n")
            f.write("- Wrapped in transactions for atomicity\n\n")
            f.write("```bash\n")
            f.write("# Import both tables\n")
            f.write("psql -h <host> -p <port> -d <database> -f iris_database_registry.sql\n")
            f.write("psql -h <host> -p <port> -d <database> -f iris_prompts.sql\n")
            f.write("```\n\n")
            f.write("## CSV Files\n\n")
            f.write("For GUI tools like pgAdmin or DBeaver:\n")
            f.write("1. Right-click table → Import/Export\n")
            f.write("2. Select CSV file\n")
            f.write("3. Ensure column mapping matches\n\n")
            f.write("For psql `\\copy`:\n")
            f.write("```bash\n")
            f.write("\\copy iris_database_registry FROM 'iris_database_registry.csv' WITH (FORMAT csv, HEADER true)\n")
            f.write("\\copy prompts(model,layer,name,version,description,system_prompt,user_prompt,tool_definition) FROM 'iris_prompts.csv' WITH (FORMAT csv, HEADER true)\n")
            f.write("```\n\n")
            f.write("## Notes\n\n")
            f.write("- `test_docs` registry entry is included for testing - remove if not needed in production\n")
            f.write("- Prompts include only `model='iris'` entries (doc_refresh prompts excluded)\n")
            f.write("- JSONB columns are properly escaped in all formats\n")
            f.write("- Array columns use PostgreSQL array literal format `{val1,val2}`\n")

        print(f"  Created: {readme_path}")

        print(f"\nExport complete! Files written to: {OUTPUT_DIR}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
