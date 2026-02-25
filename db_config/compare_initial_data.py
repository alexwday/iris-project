#!/usr/bin/env python3
"""
Compare two Postgres databases against IRIS initial seed data.

This script validates that each target database matches the canonical
initial data in:
  - db_config/schemas/initial_data/iris_prompts.csv
  - db_config/schemas/initial_data/iris_database_registry.csv

It compares only baseline columns from the initial load and ignores any
additional columns that may exist in target databases.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql


SCRIPT_DIR = Path(__file__).resolve().parent
INITIAL_DATA_DIR = SCRIPT_DIR / "schemas" / "initial_data"
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "compare_initial_data.config.json"
DEFAULT_REPORT_PATH = SCRIPT_DIR / "compare_initial_data.report.json"


@dataclass(frozen=True)
class ConnectionConfig:
    name: str
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str | None = None
    gssencmode: str | None = None


@dataclass(frozen=True)
class TableSpec:
    name: str
    csv_path: Path
    key_columns: tuple[str, ...]
    where_clause: str | None = None


TABLE_SPECS = (
    TableSpec(
        name="prompts",
        csv_path=INITIAL_DATA_DIR / "iris_prompts.csv",
        key_columns=("model", "layer", "name", "version"),
        where_clause="model = 'iris'",
    ),
    TableSpec(
        name="iris_database_registry",
        csv_path=INITIAL_DATA_DIR / "iris_database_registry.csv",
        key_columns=("db_source",),
    ),
)


COLUMN_TYPES: dict[str, dict[str, set[str]]] = {
    "prompts": {
        "json": {"tool_definition"},
        "array": set(),
        "int": set(),
        "bool": set(),
    },
    "iris_database_registry": {
        "json": {
            "catalog_config",
            "semantic_config",
            "metadata_config",
            "sample_questions",
        },
        "array": {"search_modes", "ad_groups", "metadata_context_fields"},
        "int": {
            "batch_size",
            "max_selected_files",
            "top_chunks_in_catalog_selection",
            "top_chunks_in_metadata_research",
            "page_threshold_for_full_content",
            "max_parallel_files",
            "max_chunks_per_file",
            "max_pages_for_full_context",
            "max_primary_section_page_count",
            "max_subsection_page_count",
            "max_neighbour_chunks",
            "max_gap_fill_pages",
        },
        "bool": {"enabled", "enable_db_wide_deep_research"},
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two Postgres databases against IRIS initial data in "
            "db_config/schemas/initial_data."
        )
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=(
            "Path to JSON config with two database connections. "
            f"Default: {DEFAULT_CONFIG_PATH}"
        ),
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_REPORT_PATH),
        help=(
            "Path to write JSON report. "
            f"Default: {DEFAULT_REPORT_PATH}"
        ),
    )
    parser.add_argument(
        "--max-differences",
        type=int,
        default=100,
        help="Maximum per-table value-difference entries to include in output.",
    )
    parser.add_argument(
        "--max-key-samples",
        type=int,
        default=10,
        help="How many missing/extra keys to print per table.",
    )
    return parser.parse_args()


def normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def parse_bool(raw: str, context: str) -> bool:
    value = raw.strip().lower()
    if value in {"true", "t", "1", "yes", "y"}:
        return True
    if value in {"false", "f", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value {raw!r} ({context})")


def parse_json_value(raw: str, context: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON value ({context}): {exc}") from exc


def parse_pg_array_literal(value: str) -> list[Any]:
    """
    Parse a simple PostgreSQL text array literal (e.g. {"a","b"} or {a,b}).
    """
    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return [text]

    inner = text[1:-1]
    if inner == "":
        return []

    result: list[Any] = []
    token: list[str] = []
    in_quotes = False
    escape = False

    for char in inner:
        if escape:
            token.append(char)
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char == '"':
            in_quotes = not in_quotes
            continue

        if char == "," and not in_quotes:
            item = "".join(token)
            result.append(None if item == "NULL" else item)
            token = []
            continue

        token.append(char)

    item = "".join(token)
    result.append(None if item == "NULL" else item)
    return result


def parse_csv_value(table_name: str, column_name: str, raw: str | None) -> Any:
    if raw is None:
        return None

    table_types = COLUMN_TYPES[table_name]
    context = f"{table_name}.{column_name}"

    if raw == "":
        if (
            column_name in table_types["bool"]
            or column_name in table_types["int"]
            or column_name in table_types["json"]
            or column_name in table_types["array"]
        ):
            return None
        return ""

    if column_name in table_types["bool"]:
        return parse_bool(raw, context)

    if column_name in table_types["int"]:
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid integer value {raw!r} ({context})") from exc

    if column_name in table_types["json"] or column_name in table_types["array"]:
        return parse_json_value(raw, context)

    return normalize_line_endings(raw)


def normalize_db_value(table_name: str, column_name: str, value: Any) -> Any:
    if value is None:
        return None

    table_types = COLUMN_TYPES[table_name]

    if column_name in table_types["bool"]:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return parse_bool(value, f"{table_name}.{column_name}")
        return bool(value)

    if column_name in table_types["int"]:
        return int(value)

    if column_name in table_types["json"]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            return parse_json_value(stripped, f"{table_name}.{column_name}")
        return value

    if column_name in table_types["array"]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            if stripped.startswith("{") and stripped.endswith("}"):
                return parse_pg_array_literal(stripped)
            return parse_json_value(stripped, f"{table_name}.{column_name}")
        return value

    if isinstance(value, str):
        return normalize_line_endings(value)

    return value


def canonical_string(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def preview_value(value: Any, max_len: int = 220) -> str:
    rendered = canonical_string(value)
    if len(rendered) <= max_len:
        return rendered
    return f"{rendered[:max_len]}... (truncated)"


def short_hash(value: Any) -> str:
    rendered = canonical_string(value)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:12]


def format_key(key_columns: tuple[str, ...], key_values: tuple[Any, ...]) -> str:
    parts = [f"{column}={value!r}" for column, value in zip(key_columns, key_values)]
    return ", ".join(parts)


def key_sorter(key_values: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple("" if value is None else str(value) for value in key_values)


def load_golden_table(spec: TableSpec) -> dict[str, Any]:
    if not spec.csv_path.exists():
        raise FileNotFoundError(f"Golden source file not found: {spec.csv_path}")

    with spec.csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"No CSV header found in {spec.csv_path}")

        columns = [column.strip() for column in reader.fieldnames]
        rows: list[dict[str, Any]] = []

        for row_number, raw_row in enumerate(reader, start=2):
            parsed_row: dict[str, Any] = {}
            for column in columns:
                try:
                    parsed_row[column] = parse_csv_value(spec.name, column, raw_row.get(column))
                except ValueError as exc:
                    raise ValueError(
                        f"{spec.csv_path}:{row_number} column={column}: {exc}"
                    ) from exc
            rows.append(parsed_row)

    return {"columns": columns, "rows": rows}


def load_connection_configs(config_path: Path) -> list[ConnectionConfig]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw_config = json.load(handle)

    raw_connections = raw_config.get("connections", raw_config)
    parsed_connections: list[dict[str, Any]] = []

    if isinstance(raw_connections, list):
        for item in raw_connections:
            if not isinstance(item, dict):
                raise ValueError("Each connection entry must be an object.")
            parsed_connections.append(item)
    elif isinstance(raw_connections, dict):
        for name, item in raw_connections.items():
            if not isinstance(item, dict):
                raise ValueError(f"Connection {name!r} must be an object.")
            merged = dict(item)
            merged.setdefault("name", name)
            parsed_connections.append(merged)
    else:
        raise ValueError("Config must contain a list or object of connections.")

    if len(parsed_connections) != 2:
        raise ValueError("Config must define exactly 2 connections.")

    configs: list[ConnectionConfig] = []
    required_fields = ("host", "port", "database", "user")

    for index, entry in enumerate(parsed_connections, start=1):
        name = entry.get("name") or f"db{index}"

        missing = [field for field in required_fields if field not in entry]
        if missing:
            raise ValueError(
                f"Connection {name!r} missing required fields: {', '.join(missing)}"
            )

        def read_str(field_name: str, default: str | None = None) -> str | None:
            raw_value = entry.get(field_name, default)
            if raw_value is None:
                return None
            return os.path.expandvars(str(raw_value))

        port_raw = read_str("port")
        if port_raw is None:
            raise ValueError(f"Connection {name!r} has invalid port.")
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ValueError(f"Connection {name!r} has invalid port: {port_raw!r}") from exc

        configs.append(
            ConnectionConfig(
                name=str(name),
                host=read_str("host") or "",
                port=port,
                database=read_str("database") or "",
                user=read_str("user") or "",
                password=read_str("password", "") or "",
                sslmode=read_str("sslmode"),
                gssencmode=read_str("gssencmode"),
            )
        )

    return configs


def get_connection(config: ConnectionConfig):
    kwargs: dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "user": config.user,
        "password": config.password,
    }
    if config.sslmode:
        kwargs["sslmode"] = config.sslmode
    if config.gssencmode:
        kwargs["gssencmode"] = config.gssencmode
    return psycopg2.connect(**kwargs)


def fetch_table_columns(conn, table_name: str) -> list[str]:
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (table_name,))
        return [row[0] for row in cur.fetchall()]


def fetch_rows(conn, spec: TableSpec, selected_columns: list[str]) -> list[dict[str, Any]]:
    if not selected_columns:
        return []

    query = sql.SQL("SELECT {cols} FROM {table}").format(
        cols=sql.SQL(", ").join(sql.Identifier(column) for column in selected_columns),
        table=sql.Identifier(spec.name),
    )

    if spec.where_clause:
        query += sql.SQL(" WHERE ") + sql.SQL(spec.where_clause)

    rows: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(query)
        for record in cur.fetchall():
            row: dict[str, Any] = {}
            for column, value in zip(selected_columns, record):
                row[column] = normalize_db_value(spec.name, column, value)
            rows.append(row)
    return rows


def build_index(
    rows: list[dict[str, Any]],
    key_columns: tuple[str, ...],
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], list[str]]:
    index: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicates: list[str] = []

    for row in rows:
        key = tuple(row.get(column) for column in key_columns)
        if key in index:
            duplicates.append(format_key(key_columns, key))
            continue
        index[key] = row

    return index, duplicates


def compare_table(
    spec: TableSpec,
    golden_columns: list[str],
    golden_rows: list[dict[str, Any]],
    actual_columns: list[str],
    actual_rows: list[dict[str, Any]],
    max_differences: int,
) -> dict[str, Any]:
    baseline_columns = list(golden_columns)
    baseline_column_set = set(baseline_columns)
    actual_column_set = set(actual_columns)

    ignored_extra_columns = sorted(actual_column_set - baseline_column_set)
    missing_baseline_columns = sorted(baseline_column_set - actual_column_set)
    compare_columns = [column for column in baseline_columns if column in actual_column_set]

    result: dict[str, Any] = {
        "table": spec.name,
        "key_columns": list(spec.key_columns),
        "where_clause": spec.where_clause,
        "baseline_columns": baseline_columns,
        "actual_columns": actual_columns,
        "ignored_extra_columns": ignored_extra_columns,
        "missing_baseline_columns": missing_baseline_columns,
        "compare_columns": compare_columns,
        "errors": [],
        "expected_rows": len(golden_rows),
        "actual_rows": len(actual_rows),
        "missing_keys": [],
        "extra_keys": [],
        "duplicate_expected_keys": [],
        "duplicate_actual_keys": [],
        "value_differences": [],
        "value_differences_truncated": False,
        "changed_row_count": 0,
        "matches_golden": False,
    }

    missing_key_columns = [column for column in spec.key_columns if column not in actual_column_set]
    if missing_key_columns:
        result["errors"].append(
            f"Missing required key columns in target table: {', '.join(missing_key_columns)}"
        )
        result["matches_golden"] = False
        return result

    expected_index, duplicate_expected = build_index(golden_rows, spec.key_columns)
    actual_index, duplicate_actual = build_index(actual_rows, spec.key_columns)
    result["duplicate_expected_keys"] = duplicate_expected
    result["duplicate_actual_keys"] = duplicate_actual

    expected_keys = set(expected_index.keys())
    actual_keys = set(actual_index.keys())

    missing_keys = sorted(expected_keys - actual_keys, key=key_sorter)
    extra_keys = sorted(actual_keys - expected_keys, key=key_sorter)
    common_keys = sorted(expected_keys & actual_keys, key=key_sorter)

    result["missing_keys"] = [format_key(spec.key_columns, key) for key in missing_keys]
    result["extra_keys"] = [format_key(spec.key_columns, key) for key in extra_keys]

    changed_keys: set[tuple[Any, ...]] = set()
    value_differences: list[dict[str, Any]] = []
    truncated = False

    for key in common_keys:
        expected_row = expected_index[key]
        actual_row = actual_index[key]

        for column in compare_columns:
            expected_value = expected_row.get(column)
            actual_value = actual_row.get(column)

            if expected_value == actual_value:
                continue

            changed_keys.add(key)
            if len(value_differences) < max_differences:
                value_differences.append(
                    {
                        "key": format_key(spec.key_columns, key),
                        "column": column,
                        "expected_preview": preview_value(expected_value),
                        "actual_preview": preview_value(actual_value),
                        "expected_hash": short_hash(expected_value),
                        "actual_hash": short_hash(actual_value),
                    }
                )
            else:
                truncated = True

    result["value_differences"] = value_differences
    result["value_differences_truncated"] = truncated
    result["changed_row_count"] = len(changed_keys)

    has_issues = any(
        [
            bool(result["errors"]),
            bool(result["missing_baseline_columns"]),
            bool(result["missing_keys"]),
            bool(result["extra_keys"]),
            bool(result["duplicate_expected_keys"]),
            bool(result["duplicate_actual_keys"]),
            bool(result["value_differences"]) or result["value_differences_truncated"],
        ]
    )
    result["matches_golden"] = not has_issues
    return result


def compare_database(
    config: ConnectionConfig,
    golden_data: dict[str, dict[str, Any]],
    max_differences: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "name": config.name,
        "connection": {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "user": config.user,
        },
        "tables": [],
        "errors": [],
        "matches_golden": False,
    }

    try:
        conn = get_connection(config)
    except Exception as exc:
        report["errors"].append(f"Connection failed: {exc}")
        return report

    try:
        for spec in TABLE_SPECS:
            table_golden = golden_data[spec.name]
            golden_columns = table_golden["columns"]
            golden_rows = table_golden["rows"]

            actual_columns = fetch_table_columns(conn, spec.name)
            if not actual_columns:
                report["tables"].append(
                    {
                        "table": spec.name,
                        "key_columns": list(spec.key_columns),
                        "where_clause": spec.where_clause,
                        "baseline_columns": list(golden_columns),
                        "actual_columns": [],
                        "ignored_extra_columns": [],
                        "missing_baseline_columns": list(golden_columns),
                        "compare_columns": [],
                        "errors": [f"Table {spec.name!r} not found in target database."],
                        "expected_rows": len(golden_rows),
                        "actual_rows": 0,
                        "missing_keys": [],
                        "extra_keys": [],
                        "duplicate_expected_keys": [],
                        "duplicate_actual_keys": [],
                        "value_differences": [],
                        "value_differences_truncated": False,
                        "changed_row_count": 0,
                        "matches_golden": False,
                    }
                )
                continue

            compare_columns = [column for column in golden_columns if column in set(actual_columns)]
            actual_rows = fetch_rows(conn, spec, compare_columns)
            table_report = compare_table(
                spec=spec,
                golden_columns=golden_columns,
                golden_rows=golden_rows,
                actual_columns=actual_columns,
                actual_rows=actual_rows,
                max_differences=max_differences,
            )
            report["tables"].append(table_report)
    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        conn.close()

    report["matches_golden"] = not report["errors"] and all(
        table.get("matches_golden", False) for table in report["tables"]
    )
    return report


def print_table_summary(table: dict[str, Any], max_key_samples: int) -> None:
    print(f"  Table: {table['table']}")
    print(
        "    Columns (baseline/actual): "
        f"{len(table['baseline_columns'])}/{len(table['actual_columns'])}"
    )

    if table["ignored_extra_columns"]:
        print(
            "    Ignored extra columns: "
            + ", ".join(table["ignored_extra_columns"])
        )
    if table["missing_baseline_columns"]:
        print(
            "    Missing baseline columns: "
            + ", ".join(table["missing_baseline_columns"])
        )

    print(
        f"    Rows (expected/actual): {table['expected_rows']}/{table['actual_rows']}"
    )
    print(
        "    Missing keys / Extra keys / Changed rows: "
        f"{len(table['missing_keys'])} / {len(table['extra_keys'])} / {table['changed_row_count']}"
    )

    if table["errors"]:
        for error in table["errors"]:
            print(f"    ERROR: {error}")

    if table["duplicate_expected_keys"]:
        print(
            f"    Duplicate keys in golden data: {len(table['duplicate_expected_keys'])}"
        )
    if table["duplicate_actual_keys"]:
        print(
            f"    Duplicate keys in target data: {len(table['duplicate_actual_keys'])}"
        )

    if table["missing_keys"]:
        print("    Missing key samples:")
        for key in table["missing_keys"][:max_key_samples]:
            print(f"      - {key}")

    if table["extra_keys"]:
        print("    Extra key samples:")
        for key in table["extra_keys"][:max_key_samples]:
            print(f"      - {key}")

    if table["value_differences"]:
        print("    Value differences (sample):")
        for diff in table["value_differences"][:max_key_samples]:
            print(
                "      - "
                f"{diff['key']} | {diff['column']} "
                f"(golden_hash={diff['expected_hash']}, target_hash={diff['actual_hash']})"
            )
            print(f"        golden: {diff['expected_preview']}")
            print(f"        target: {diff['actual_preview']}")

    if table["value_differences_truncated"]:
        print("    Value differences truncated. Increase --max-differences for full output.")


def print_report(report: dict[str, Any], max_key_samples: int) -> None:
    print("=" * 80)
    print("IRIS Initial Data Comparison")
    print("=" * 80)
    print("Golden source files:")
    for spec in TABLE_SPECS:
        print(f"- {spec.name}: {spec.csv_path}")

    for db_report in report["databases"]:
        connection = db_report["connection"]
        print("\n" + "-" * 80)
        print(
            f"Database: {db_report['name']} "
            f"({connection['host']}:{connection['port']}/{connection['database']})"
        )
        print(f"Status: {'PASS' if db_report['matches_golden'] else 'FAIL'}")

        if db_report["errors"]:
            for error in db_report["errors"]:
                print(f"ERROR: {error}")
            continue

        for table in db_report["tables"]:
            print_table_summary(table, max_key_samples=max_key_samples)

    print("\n" + "=" * 80)
    if report["all_match_golden"]:
        print("Overall result: PASS (both databases match golden source on baseline columns)")
    else:
        print("Overall result: FAIL (at least one database differs from golden source)")
    print("=" * 80)


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()

    try:
        connection_configs = load_connection_configs(config_path)
        golden_data = {spec.name: load_golden_table(spec) for spec in TABLE_SPECS}
    except Exception as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 2

    db_reports = [
        compare_database(config, golden_data, max_differences=args.max_differences)
        for config in connection_configs
    ]

    report = {
        "config_path": str(config_path),
        "databases": db_reports,
        "all_match_golden": all(db_report["matches_golden"] for db_report in db_reports),
    }

    print_report(report, max_key_samples=args.max_key_samples)

    output_path = Path(args.output_json).expanduser().resolve()
    write_json_report(report, output_path)
    print(f"JSON report written to: {output_path}")

    return 0 if report["all_match_golden"] else 1


if __name__ == "__main__":
    sys.exit(main())
