#!/usr/bin/env python3
"""
Quick script to view IRIS request timings from process_monitor_logs.

Usage:
    python testing/view_timings.py           # Show last 5 requests
    python testing/view_timings.py --last 10 # Show last 10 requests
    python testing/view_timings.py --uuid <run_uuid>  # Show specific request
"""

import argparse
import os
import psycopg2
from tabulate import tabulate

DB_HOST = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
DB_PORT = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
DB_NAME = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
DB_USER = os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres"))
DB_PASSWORD = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def show_recent_requests(limit: int = 5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT run_uuid,
               MIN(stage_start_time) as start_time,
               SUM(duration_ms) as total_ms
        FROM process_monitor_logs
        GROUP BY run_uuid
        ORDER BY MIN(stage_start_time) DESC
        LIMIT %s
    """, (limit,))

    requests = cursor.fetchall()

    for run_uuid, start_time, total_ms in requests:
        print(f"\n{'='*70}")
        print(f"Run: {run_uuid}")
        print(f"Time: {start_time}")
        print(f"Total: {total_ms}ms ({total_ms/1000:.1f}s)")
        print(f"{'='*70}")

        show_request_details(cursor, str(run_uuid))

    cursor.close()
    conn.close()


def show_request_details(cursor, run_uuid: str):
    cursor.execute("""
        SELECT stage_name, duration_ms, total_tokens,
               COALESCE(total_cost::text, '-') as cost,
               status
        FROM process_monitor_logs
        WHERE run_uuid = %s
        ORDER BY stage_start_time
    """, (run_uuid,))

    rows = cursor.fetchall()

    table_data = []
    for stage, duration, tokens, cost, status in rows:
        duration_str = f"{duration}ms" if duration else "-"
        tokens_str = str(tokens) if tokens else "-"
        table_data.append([stage, duration_str, tokens_str, cost, status])

    print(tabulate(
        table_data,
        headers=["Stage", "Duration", "Tokens", "Cost", "Status"],
        tablefmt="simple"
    ))


def show_single_request(run_uuid: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(duration_ms) as total_ms
        FROM process_monitor_logs
        WHERE run_uuid = %s
    """, (run_uuid,))

    result = cursor.fetchone()
    if not result or result[0] is None:
        print(f"No data found for run_uuid: {run_uuid}")
        return

    print(f"\n{'='*70}")
    print(f"Run: {run_uuid}")
    print(f"Total: {result[0]}ms ({result[0]/1000:.1f}s)")
    print(f"{'='*70}")

    show_request_details(cursor, run_uuid)

    cursor.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="View IRIS request timings")
    parser.add_argument("--last", type=int, default=5, help="Number of recent requests to show")
    parser.add_argument("--uuid", type=str, help="Show specific request by UUID")

    args = parser.parse_args()

    if args.uuid:
        show_single_request(args.uuid)
    else:
        show_recent_requests(args.last)


if __name__ == "__main__":
    main()
