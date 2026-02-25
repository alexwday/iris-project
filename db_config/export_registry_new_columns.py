#!/usr/bin/env python3
"""
Export new/extra columns in iris_database_registry relative to initial data.

Use this on any environment to detect:
1) columns present in the live table but not in initial_data CSV
2) values for those extra columns per db_source

Outputs are written to db_config/ by default:
  - registry_new_columns_report.json
  - registry_new_columns_values.csv
  - registry_new_columns_report.md
  - registry_new_columns_values.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, time
from decimal import Decimal
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
DEFAULT_BASELINE_CSV = SCRIPT_DIR / "schemas" / "initial_data" / "iris_database_registry.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR
TABLE_NAME = "iris_database_registry"
KEY_COLUMN = "db_source"
SAMPLE_QUESTIONS_COLUMN = "sample_questions"
EXCLUDED_EXTRA_VALUE_COLUMNS = {"created_at", "updated_at"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export columns that exist in live iris_database_registry table but not in "
            "the initial data CSV header, including their values by db_source."
        )
    )
    parser.add_argument(
        "--baseline-csv",
        default=str(DEFAULT_BASELINE_CSV),
        help=f"Baseline CSV path. Default: {DEFAULT_BASELINE_CSV}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for report outputs. Default: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def get_connection():
    host = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
    port = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
    database = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
    user = os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres"))
    password = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")
    gssencmode = os.getenv("PGGSSENCMODE", "")
    sslmode = os.getenv("PGSSLMODE", "")

    kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
    }
    if gssencmode:
        kwargs["gssencmode"] = gssencmode
    if sslmode:
        kwargs["sslmode"] = sslmode

    return psycopg2.connect(**kwargs), {
        "host": host,
        "port": str(port),
        "database": database,
        "user": user,
    }


def load_baseline_columns(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Baseline CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            raise ValueError(f"Baseline CSV has no header: {path}")
        return [column.strip() for column in header]


def fetch_table_columns(conn, table_name: str) -> list[dict[str, Any]]:
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
        cur.execute(query, (table_name,))
        rows = cur.fetchall()

    return [
        {
            "column_name": row[0],
            "data_type": row[1],
            "udt_name": row[2],
            "is_nullable": row[3],
            "column_default": row[4],
            "ordinal_position": row[5],
        }
        for row in rows
    ]


def fetch_row_count(conn, table_name: str) -> int:
    query = sql.SQL("SELECT COUNT(*) FROM {table}").format(table=sql.Identifier(table_name))
    with conn.cursor() as cur:
        cur.execute(query)
        return int(cur.fetchone()[0])


def fetch_selected_values(
    conn,
    table_name: str,
    key_column: str,
    selected_columns: list[str],
) -> list[dict[str, Any]]:
    selected = [key_column] + selected_columns
    query = sql.SQL("SELECT {cols} FROM {table} ORDER BY {key_col}").format(
        cols=sql.SQL(", ").join(sql.Identifier(col) for col in selected),
        table=sql.Identifier(table_name),
        key_col=sql.Identifier(key_column),
    )

    rows: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(query)
        for record in cur.fetchall():
            rows.append({column: value for column, value in zip(selected, record)})

    return rows


def normalize_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.hex()
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_json(val) for key, val in value.items()}
    return value


def value_to_text(value: Any, max_len: int | None = None) -> str:
    normalized = normalize_json(value)
    if normalized is None:
        text = "NULL"
    elif isinstance(normalized, (dict, list)):
        text = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    else:
        text = str(normalized)

    if max_len is not None and len(text) > max_len:
        return f"{text[:max_len]}... (truncated)"
    return text


def build_column_stats(
    extra_columns: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for column in extra_columns:
        raw_values = [row.get(column) for row in rows]
        non_null_values = [value for value in raw_values if value is not None]
        distinct_rendered = {value_to_text(value) for value in non_null_values}
        sample_values = []
        for value in non_null_values[:5]:
            sample_values.append(value_to_text(value))

        stats[column] = {
            "non_null_count": len(non_null_values),
            "distinct_non_null_count": len(distinct_rendered),
            "sample_values": sample_values,
        }
    return stats


def write_values_csv(path: Path, key_column: str, extra_columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([key_column] + extra_columns)
        for row in rows:
            out = [value_to_text(row.get(key_column))]
            for column in extra_columns:
                out.append(value_to_text(row.get(column)))
            writer.writerow(out)


def markdown_cell(value: Any) -> str:
    text = value_to_text(value)
    text = text.replace("|", "\\|")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br>")
    return text


def extract_sample_questions(value: Any) -> list[str]:
    normalized = normalize_json(value)
    if normalized is None:
        return []

    if isinstance(normalized, list):
        return [value_to_text(item) for item in normalized]

    if isinstance(normalized, tuple):
        return [value_to_text(item) for item in list(normalized)]

    if isinstance(normalized, str):
        text = normalized.strip()
        if text == "":
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [value_to_text(item) for item in parsed]
            except json.JSONDecodeError:
                pass
        return [normalized]

    return [value_to_text(normalized)]


def write_values_text(path: Path, key_column: str, matrix_columns: list[str], rows: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("IRIS Registry Full Value Dump")
    lines.append("=" * 80)
    lines.append("")
    if not rows:
        lines.append("No rows found.")
        lines.append("")
    for row in rows:
        key_value = value_to_text(row.get(key_column))
        lines.append(f"{key_column}: {key_value}")
        lines.append("-" * 80)
        for column in matrix_columns:
            lines.append(f"{column}:")
            lines.append(value_to_text(row.get(column)))
            lines.append("")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_report(
    path: Path,
    connection_info: dict[str, str],
    baseline_csv: Path,
    baseline_columns: list[str],
    actual_columns_meta: list[dict[str, Any]],
    extra_columns_meta: list[dict[str, Any]],
    matrix_extra_columns: list[str],
    sample_questions_available: bool,
    stats: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    actual_columns = [meta["column_name"] for meta in actual_columns_meta]
    extra_columns = [meta["column_name"] for meta in extra_columns_meta]

    lines: list[str] = []
    lines.append("# IRIS Registry New Column Report")
    lines.append("")
    lines.append(f"- Generated: `{now}`")
    lines.append(
        f"- Database: `{connection_info['host']}:{connection_info['port']}/{connection_info['database']}`"
    )
    lines.append(f"- User: `{connection_info['user']}`")
    lines.append(f"- Baseline CSV: `{baseline_csv}`")
    lines.append(f"- Baseline columns: **{len(baseline_columns)}**")
    lines.append(f"- Actual table columns: **{len(actual_columns)}**")
    lines.append(f"- New/extra columns: **{len(extra_columns)}**")
    lines.append(
        "- Matrix extra columns (excluding `created_at` and `updated_at`): **"
        + str(len(matrix_extra_columns))
        + "**"
    )
    lines.append("")

    lines.append("## Table 1: Extra Column Schema")
    lines.append("")
    if extra_columns:
        lines.append(
            "| column_name | data_type | udt_name | nullable | default | non_null | distinct |"
        )
        lines.append("|---|---|---|---|---|---:|---:|")
        for meta in extra_columns_meta:
            column = meta["column_name"]
            stat = stats[column]
            lines.append(
                "| "
                + " | ".join(
                    [
                        column,
                        str(meta.get("data_type", "")),
                        str(meta.get("udt_name", "")),
                        str(meta.get("is_nullable", "")),
                        str(meta.get("column_default", ""))[:80],
                        str(stat["non_null_count"]),
                        str(stat["distinct_non_null_count"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    else:
        lines.append("No new columns were found relative to baseline CSV.")
        lines.append("")

    lines.append("## Table 2: Extra Column Value Matrix (excluding created_at, updated_at)")
    lines.append("")
    if matrix_extra_columns:
        lines.append("| db_source | " + " | ".join(matrix_extra_columns) + " |")
        lines.append("|---|" + "|".join("---" for _ in matrix_extra_columns) + "|")
        for row in rows:
            parts = [markdown_cell(row.get(KEY_COLUMN))]
            for column in matrix_extra_columns:
                parts.append(markdown_cell(row.get(column)))
            lines.append("| " + " | ".join(parts) + " |")
    else:
        lines.append("_No extra columns remain after excluding created_at and updated_at._")
    lines.append("")

    lines.append("## Table 3: Sample Questions by db_source")
    lines.append("")
    if sample_questions_available:
        lines.append("| db_source | question_index | sample_question |")
        lines.append("|---|---:|---|")
        for row in rows:
            db_source = markdown_cell(row.get(KEY_COLUMN))
            questions = extract_sample_questions(row.get(SAMPLE_QUESTIONS_COLUMN))
            if not questions:
                lines.append(f"| {db_source} | 0 | NULL |")
                continue
            for index, question in enumerate(questions, start=1):
                lines.append(f"| {db_source} | {index} | {markdown_cell(question)} |")
    else:
        lines.append("_sample_questions column not found in target table._")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    baseline_csv = Path(args.baseline_csv).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "registry_new_columns_report.json"
    csv_path = output_dir / "registry_new_columns_values.csv"
    md_path = output_dir / "registry_new_columns_report.md"
    txt_path = output_dir / "registry_new_columns_values.txt"

    try:
        baseline_columns = load_baseline_columns(baseline_csv)
    except Exception as exc:
        print(f"Setup error (baseline): {exc}", file=sys.stderr)
        return 2

    conn = None
    try:
        conn, connection_info = get_connection()
        actual_columns_meta = fetch_table_columns(conn, TABLE_NAME)
        if not actual_columns_meta:
            print(f"Table not found: {TABLE_NAME}", file=sys.stderr)
            return 2

        actual_columns = [meta["column_name"] for meta in actual_columns_meta]
        baseline_set = set(baseline_columns)
        extra_columns_meta = [
            meta for meta in actual_columns_meta if meta["column_name"] not in baseline_set
        ]
        extra_columns = [meta["column_name"] for meta in extra_columns_meta]
        matrix_extra_columns = [
            column for column in extra_columns if column not in EXCLUDED_EXTRA_VALUE_COLUMNS
        ]
        sample_questions_available = SAMPLE_QUESTIONS_COLUMN in actual_columns

        fetch_columns = list(extra_columns)
        if sample_questions_available and SAMPLE_QUESTIONS_COLUMN not in fetch_columns:
            fetch_columns.append(SAMPLE_QUESTIONS_COLUMN)

        rows: list[dict[str, Any]] = []
        if fetch_columns:
            rows = fetch_selected_values(conn, TABLE_NAME, KEY_COLUMN, fetch_columns)
        elif sample_questions_available:
            rows = fetch_selected_values(conn, TABLE_NAME, KEY_COLUMN, [SAMPLE_QUESTIONS_COLUMN])

        stats = build_column_stats(extra_columns, rows)
        report = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "table": TABLE_NAME,
            "key_column": KEY_COLUMN,
            "connection": connection_info,
            "baseline_csv": str(baseline_csv),
            "baseline_column_count": len(baseline_columns),
            "actual_column_count": len(actual_columns),
            "row_count": fetch_row_count(conn, TABLE_NAME),
            "baseline_columns": baseline_columns,
            "actual_columns": actual_columns,
            "excluded_matrix_columns": sorted(EXCLUDED_EXTRA_VALUE_COLUMNS),
            "extra_columns_for_matrix": matrix_extra_columns,
            "sample_questions_available": sample_questions_available,
            "extra_columns": [
                {
                    **meta,
                    **stats[meta["column_name"]],
                }
                for meta in extra_columns_meta
            ],
            "rows": [
                {key: normalize_json(value) for key, value in row.items()}
                for row in rows
            ],
        }

        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

        write_values_csv(csv_path, KEY_COLUMN, matrix_extra_columns, rows)
        text_columns = list(matrix_extra_columns)
        if sample_questions_available and SAMPLE_QUESTIONS_COLUMN not in text_columns:
            text_columns.append(SAMPLE_QUESTIONS_COLUMN)
        write_values_text(txt_path, KEY_COLUMN, text_columns, rows)
        write_markdown_report(
            path=md_path,
            connection_info=connection_info,
            baseline_csv=baseline_csv,
            baseline_columns=baseline_columns,
            actual_columns_meta=actual_columns_meta,
            extra_columns_meta=extra_columns_meta,
            matrix_extra_columns=matrix_extra_columns,
            sample_questions_available=sample_questions_available,
            stats=stats,
            rows=rows,
        )

        print("=" * 72)
        print("IRIS Registry New Column Export")
        print("=" * 72)
        print(
            f"Database: {connection_info['host']}:{connection_info['port']}/{connection_info['database']}"
        )
        print(f"Baseline columns: {len(baseline_columns)}")
        print(f"Actual columns:   {len(actual_columns)}")
        print(f"New columns:      {len(extra_columns)}")
        if matrix_extra_columns:
            print("Matrix extra columns: " + ", ".join(matrix_extra_columns))
        else:
            print("Matrix extra columns: (none after excluding created_at/updated_at)")
        print(
            "Sample questions column: "
            + ("present" if sample_questions_available else "missing")
        )
        if extra_columns:
            print("New columns found:")
            for meta in extra_columns_meta:
                column = meta["column_name"]
                stat = stats[column]
                print(
                    f"- {column} ({meta['data_type']}) | non_null={stat['non_null_count']} "
                    f"| distinct={stat['distinct_non_null_count']}"
                )
        else:
            print("No extra columns found.")

        print("")
        print(f"JSON report: {json_path}")
        print(f"CSV values:  {csv_path}")
        print(f"MD report:   {md_path}")
        print(f"TXT values:  {txt_path}")
        print("=" * 72)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
