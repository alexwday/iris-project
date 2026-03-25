#!/usr/bin/env python3
"""
Compare seed registry data against a live Postgres registry table.

Compares:
1) Schema-level column differences (seed CSV header vs DB table columns)
2) Row-level differences keyed by db_source
3) Field-level value differences for overlapping columns

Usage:
    python db_config/compare_registry_seed_to_db.py

Uses the same DB env vars as populate_initial_data.py:
  VECTOR_POSTGRES_DB_HOST
  VECTOR_POSTGRES_DB_PORT
  VECTOR_POSTGRES_DB_NAME
  VECTOR_POSTGRES_DB_USERNAME
  VECTOR_POSTGRES_DB_PASSWORD
  PGSSLMODE (optional)
  PGGSSENCMODE (optional)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local", override=True)
except ImportError:
    pass


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SEED_CSV = SCRIPT_DIR / "schemas" / "initial_data" / "iris_database_registry.csv"
DEFAULT_TABLE = "iris_database_registry"
DEFAULT_OUTPUT_JSON = SCRIPT_DIR / "registry_seed_vs_db.report.json"
DEFAULT_OUTPUT_MD = SCRIPT_DIR / "registry_seed_vs_db.report.md"
DEFAULT_IGNORE_COLUMNS = ("created_at", "updated_at", "uploaded_at")


COLUMN_TYPES: dict[str, set[str]] = {
    "json": {"catalog_config", "semantic_config", "metadata_config", "sample_questions"},
    "array": {"search_modes", "ad_groups", "metadata_context_fields"},
    "int": {
        "batch_size",
        "max_selected_files",
        "top_chunks_in_catalog_selection",
        "top_chunks_in_metadata_research",
        "page_threshold_for_full_content",
        "display_order",
        "max_parallel_files",
        "max_chunks_per_file",
        "max_pages_for_full_context",
        "max_primary_section_page_count",
        "max_subsection_page_count",
        "max_neighbour_chunks",
        "max_gap_fill_pages",
    },
    "bool": {"enabled", "enable_db_wide_deep_research", "is_internal"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare registry seed CSV against live Postgres registry table."
    )
    parser.add_argument(
        "--seed-csv",
        default=str(DEFAULT_SEED_CSV),
        help=f"Seed CSV path. Default: {DEFAULT_SEED_CSV}",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE,
        help=f"Target table name. Default: {DEFAULT_TABLE}",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help=f"JSON report output path. Default: {DEFAULT_OUTPUT_JSON}",
    )
    parser.add_argument(
        "--output-md",
        default=str(DEFAULT_OUTPUT_MD),
        help=f"Markdown report output path. Default: {DEFAULT_OUTPUT_MD}",
    )
    parser.add_argument(
        "--ignore-columns",
        default=",".join(DEFAULT_IGNORE_COLUMNS),
        help="Comma-separated columns to ignore in value comparison.",
    )
    parser.add_argument(
        "--max-differences",
        type=int,
        default=1000,
        help="Max number of value-difference rows to include in report.",
    )
    return parser.parse_args()


def get_connection():
    kwargs: dict[str, Any] = {
        "host": os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost"),
        "port": os.getenv("VECTOR_POSTGRES_DB_PORT", "34532"),
        "database": os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance"),
        "user": os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres")),
        "password": os.getenv("VECTOR_POSTGRES_DB_PASSWORD", ""),
    }
    gssencmode = os.getenv("PGGSSENCMODE", "")
    sslmode = os.getenv("PGSSLMODE", "")
    if gssencmode:
        kwargs["gssencmode"] = gssencmode
    if sslmode:
        kwargs["sslmode"] = sslmode
    return psycopg2.connect(**kwargs), kwargs


def parse_bool(raw: str, context: str) -> bool:
    value = raw.strip().lower()
    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid bool {raw!r} at {context}")


def parse_json(raw: str, context: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON {raw!r} at {context}: {exc}") from exc


def parse_pg_array_literal(value: str) -> list[Any]:
    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return [text]

    inner = text[1:-1]
    if inner == "":
        return []

    out: list[Any] = []
    token: list[str] = []
    in_quotes = False
    escape = False

    for ch in inner:
        if escape:
            token.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if ch == "," and not in_quotes:
            item = "".join(token)
            out.append(None if item == "NULL" else item)
            token = []
            continue
        token.append(ch)

    item = "".join(token)
    out.append(None if item == "NULL" else item)
    return out


def parse_seed_value(column: str, raw: str | None) -> Any:
    if raw is None:
        return None
    if raw == "":
        if (
            column in COLUMN_TYPES["json"]
            or column in COLUMN_TYPES["array"]
            or column in COLUMN_TYPES["int"]
            or column in COLUMN_TYPES["bool"]
        ):
            return None
        return ""

    if column in COLUMN_TYPES["bool"]:
        return parse_bool(raw, f"seed.{column}")
    if column in COLUMN_TYPES["int"]:
        return int(raw)
    if column in COLUMN_TYPES["json"] or column in COLUMN_TYPES["array"]:
        return parse_json(raw, f"seed.{column}")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def normalize_db_value(column: str, value: Any) -> Any:
    if value is None:
        return None

    if column in COLUMN_TYPES["bool"]:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return parse_bool(value, f"db.{column}")
        return bool(value)

    if column in COLUMN_TYPES["int"]:
        return int(value)

    if column in COLUMN_TYPES["json"]:
        if isinstance(value, str):
            text = value.strip()
            return None if text == "" else parse_json(text, f"db.{column}")
        return value

    if column in COLUMN_TYPES["array"]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str):
            text = value.strip()
            if text == "":
                return None
            if text.startswith("{") and text.endswith("}"):
                return parse_pg_array_literal(text)
            return parse_json(text, f"db.{column}")
        return value

    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n")
    return value


def canonical(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def short_hash(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()[:12]


def load_seed(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError(f"Seed CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Seed CSV has no header: {path}")
        columns = [c.strip() for c in reader.fieldnames]
        rows: list[dict[str, Any]] = []
        for i, raw_row in enumerate(reader, start=2):
            parsed: dict[str, Any] = {}
            for c in columns:
                try:
                    parsed[c] = parse_seed_value(c, raw_row.get(c))
                except Exception as exc:
                    raise ValueError(f"{path}:{i} column={c}: {exc}") from exc
            rows.append(parsed)
    return columns, rows


def fetch_table_columns(conn, table: str) -> list[dict[str, Any]]:
    query = """
        SELECT
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (table,))
        rows = cur.fetchall()
    return [
        {
            "column_name": r[0],
            "data_type": r[1],
            "udt_name": r[2],
            "is_nullable": r[3],
            "column_default": r[4],
            "ordinal_position": r[5],
        }
        for r in rows
    ]


def fetch_rows(conn, table: str, columns: list[str]) -> list[dict[str, Any]]:
    if not columns:
        return []
    query = sql.SQL("SELECT {cols} FROM {table}").format(
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        table=sql.Identifier(table),
    )
    with conn.cursor() as cur:
        cur.execute(query)
        rows = []
        for record in cur.fetchall():
            row: dict[str, Any] = {}
            for c, v in zip(columns, record):
                row[c] = normalize_db_value(c, v)
            rows.append(row)
        return rows


def build_index(rows: list[dict[str, Any]], key: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    out: dict[str, dict[str, Any]] = {}
    dupes: list[str] = []
    for row in rows:
        k = row.get(key)
        if k in out:
            dupes.append(str(k))
            continue
        out[str(k)] = row
    return out, dupes


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Registry Seed vs Database Comparison")
    lines.append("")
    lines.append(f"- Generated: `{report['generated_at']}`")
    lines.append(f"- Seed CSV: `{report['seed_csv']}`")
    lines.append(f"- Table: `{report['table']}`")
    conn = report["connection"]
    lines.append(f"- Database: `{conn['host']}:{conn['port']}/{conn['database']}`")
    lines.append("")
    lines.append("## Schema Differences")
    lines.append("")
    lines.append(f"- Seed columns: **{report['seed_column_count']}**")
    lines.append(f"- DB columns: **{report['db_column_count']}**")
    lines.append(f"- Missing in DB: **{len(report['schema_missing_in_db'])}**")
    lines.append(f"- Extra in DB: **{len(report['schema_extra_in_db'])}**")
    lines.append("")
    if report["schema_missing_in_db"]:
        lines.append("### Missing Columns In DB")
        lines.append("")
        lines.append("| column |")
        lines.append("|---|")
        for c in report["schema_missing_in_db"]:
            lines.append(f"| {c} |")
        lines.append("")
    if report["schema_extra_in_db"]:
        lines.append("### Extra Columns In DB")
        lines.append("")
        lines.append("| column | data_type | nullable | default |")
        lines.append("|---|---|---|---|")
        for c in report["schema_extra_in_db"]:
            meta = report["db_column_meta"].get(c, {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        c,
                        str(meta.get("data_type", "")),
                        str(meta.get("is_nullable", "")),
                        str(meta.get("column_default", "") or ""),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.append("## Row Differences")
    lines.append("")
    lines.append(f"- Seed rows: **{report['seed_row_count']}**")
    lines.append(f"- DB rows: **{report['db_row_count']}**")
    lines.append(f"- Missing rows in DB: **{len(report['missing_db_sources'])}**")
    lines.append(f"- Extra rows in DB: **{len(report['extra_db_sources'])}**")
    lines.append(f"- Changed rows: **{report['changed_row_count']}**")
    lines.append(f"- Value differences: **{report['value_difference_count']}**")
    lines.append("")

    if report["missing_db_sources"]:
        lines.append("### Missing db_source In DB")
        lines.append("")
        lines.append("| db_source |")
        lines.append("|---|")
        for s in report["missing_db_sources"]:
            lines.append(f"| {s} |")
        lines.append("")
    if report["extra_db_sources"]:
        lines.append("### Extra db_source In DB")
        lines.append("")
        lines.append("| db_source |")
        lines.append("|---|")
        for s in report["extra_db_sources"]:
            lines.append(f"| {s} |")
        lines.append("")

    lines.append("## Field Differences")
    lines.append("")
    if report["value_differences"]:
        lines.append("| db_source | column | seed_hash | db_hash | seed_value | db_value |")
        lines.append("|---|---|---|---|---|---|")
        for diff in report["value_differences"]:
            seed_val = canonical(diff["seed_value"]).replace("|", "\\|").replace("\n", "<br>")
            db_val = canonical(diff["db_value"]).replace("|", "\\|").replace("\n", "<br>")
            lines.append(
                "| "
                + " | ".join(
                    [
                        diff["db_source"],
                        diff["column"],
                        diff["seed_hash"],
                        diff["db_hash"],
                        seed_val,
                        db_val,
                    ]
                )
                + " |"
            )
    else:
        lines.append("_No field differences found in compared columns._")
    lines.append("")

    lines.append("## Field Difference Counts")
    lines.append("")
    lines.append("| column | diff_count |")
    lines.append("|---|---:|")
    for c, n in sorted(report["value_difference_by_column"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {c} | {n} |")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    seed_csv = Path(args.seed_csv).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    ignore_columns = {c.strip() for c in args.ignore_columns.split(",") if c.strip()}
    key_column = "db_source"

    try:
        seed_columns, seed_rows = load_seed(seed_csv)
    except Exception as exc:
        print(f"Seed load error: {exc}", file=sys.stderr)
        return 2

    conn = None
    try:
        conn, conn_kwargs = get_connection()
        db_cols_meta = fetch_table_columns(conn, args.table)
        if not db_cols_meta:
            print(f"Table not found: {args.table}", file=sys.stderr)
            return 2

        db_columns = [c["column_name"] for c in db_cols_meta]
        seed_col_set = set(seed_columns)
        db_col_set = set(db_columns)

        schema_missing_in_db = sorted(seed_col_set - db_col_set)
        schema_extra_in_db = sorted(db_col_set - seed_col_set)

        compare_columns = [c for c in seed_columns if c in db_col_set and c not in ignore_columns]
        db_rows = fetch_rows(conn, args.table, compare_columns)

        seed_index, seed_dupes = build_index(seed_rows, key_column)
        db_index, db_dupes = build_index(db_rows, key_column)

        seed_keys = set(seed_index.keys())
        db_keys = set(db_index.keys())
        missing_sources = sorted(seed_keys - db_keys)
        extra_sources = sorted(db_keys - seed_keys)
        common_sources = sorted(seed_keys & db_keys)

        value_differences: list[dict[str, Any]] = []
        changed_rows: set[str] = set()
        diff_by_col: Counter[str] = Counter()
        truncated = False

        for source in common_sources:
            seed_row = seed_index[source]
            db_row = db_index[source]
            for col in compare_columns:
                seed_val = seed_row.get(col)
                db_val = db_row.get(col)
                if seed_val == db_val:
                    continue
                changed_rows.add(source)
                diff_by_col[col] += 1
                if len(value_differences) < args.max_differences:
                    value_differences.append(
                        {
                            "db_source": source,
                            "column": col,
                            "seed_value": seed_val,
                            "db_value": db_val,
                            "seed_hash": short_hash(seed_val),
                            "db_hash": short_hash(db_val),
                        }
                    )
                else:
                    truncated = True

        report: dict[str, Any] = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "seed_csv": str(seed_csv),
            "table": args.table,
            "connection": {
                "host": conn_kwargs["host"],
                "port": str(conn_kwargs["port"]),
                "database": conn_kwargs["database"],
                "user": conn_kwargs["user"],
            },
            "ignore_columns": sorted(ignore_columns),
            "seed_column_count": len(seed_columns),
            "db_column_count": len(db_columns),
            "schema_missing_in_db": schema_missing_in_db,
            "schema_extra_in_db": schema_extra_in_db,
            "db_column_meta": {c["column_name"]: c for c in db_cols_meta},
            "compare_columns": compare_columns,
            "seed_row_count": len(seed_rows),
            "db_row_count": len(db_rows),
            "missing_db_sources": missing_sources,
            "extra_db_sources": extra_sources,
            "seed_duplicate_keys": seed_dupes,
            "db_duplicate_keys": db_dupes,
            "changed_row_count": len(changed_rows),
            "value_difference_count": sum(diff_by_col.values()),
            "value_difference_by_column": dict(diff_by_col),
            "value_differences": value_differences,
            "value_differences_truncated": truncated,
            "matches_seed_exactly": not any(
                [
                    schema_missing_in_db,
                    missing_sources,
                    extra_sources,
                    seed_dupes,
                    db_dupes,
                    diff_by_col,
                ]
            ),
        }

        output_json.parent.mkdir(parents=True, exist_ok=True)
        with output_json.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        write_markdown(output_md, report)

        print("=" * 80)
        print("Registry Seed vs DB Comparison")
        print("=" * 80)
        print(f"Seed CSV: {seed_csv}")
        print(f"Table: {args.table}")
        print(
            f"Database: {conn_kwargs['host']}:{conn_kwargs['port']}/{conn_kwargs['database']}"
        )
        print("")
        print(
            f"Columns seed/db: {report['seed_column_count']}/{report['db_column_count']}"
        )
        print(
            "Schema missing/extra: "
            f"{len(schema_missing_in_db)}/{len(schema_extra_in_db)}"
        )
        print(f"Rows seed/db: {report['seed_row_count']}/{report['db_row_count']}")
        print(
            "Rows missing/extra/changed: "
            f"{len(missing_sources)}/{len(extra_sources)}/{len(changed_rows)}"
        )
        print(f"Value differences: {report['value_difference_count']}")
        if truncated:
            print(
                f"Value differences truncated at {args.max_differences}. "
                "Increase --max-differences for more."
            )
        print("")
        print(f"JSON report: {output_json}")
        print(f"MD report:   {output_md}")
        print(
            "Status: "
            + ("PASS (exact match)" if report["matches_seed_exactly"] else "FAIL (differences found)")
        )
        print("=" * 80)

        return 0 if report["matches_seed_exactly"] else 1
    except Exception as exc:
        print(f"Comparison error: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
