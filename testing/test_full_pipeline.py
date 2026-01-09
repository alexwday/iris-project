#!/usr/bin/env python3
"""
Full Pipeline Test for IRIS

Tests the complete IRIS pipeline including process monitoring,
using queries that trigger direct response (no database research needed).
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment to use OpenAI directly
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1-mini"
os.environ["IRIS_LOG_LEVEL"] = "INFO"

# Skip SSL cert check for local development
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"

# Local database configuration for process monitoring
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = "alexwday"
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = ""
os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"

# Import after setting env vars
from services.src.utils.logging_format import configure_logging

configure_logging()

import logging

logger = logging.getLogger(__name__)

# Monkey-patch db_config to use sslmode=disable for local postgres
import services.src.connections.postgres as db_config

original_construct_dsn = db_config.construct_dsn


def construct_dsn_no_ssl(params: dict, for_sqlalchemy=True):
    """Modified version that uses sslmode=disable for local postgres"""
    hosts = params.get("host")
    if not hosts:
        raise ValueError("Host is not set or is empty.")

    hosts = hosts.split(",")
    port = params.get("port")
    database = params.get("dbname")
    user = params.get("user")
    password = params.get("password")

    if "," in port:
        ports = port.split(",")
        if len(ports) != len(hosts):
            raise ValueError("The number of ports must match the number of hosts.")
    else:
        ports = [port] * len(hosts)

    host_port_pairs = [f"{host}:{port}" for host, port in zip(hosts, ports)]

    if for_sqlalchemy:
        primary_host_port = host_port_pairs[0]
        dsn = (
            f"postgresql+psycopg2://{user}:{password}@{primary_host_port}/{database}?"
            f"sslmode=disable&target_session_attrs=read-write"
        )
    else:
        dsn = (
            f"dbname='{database}' user='{user}' password='{password}' "
            f"host='{','.join(hosts)}' port='{port}' sslmode='disable' "
            f"target_session_attrs='read-write'"
        )

    return dsn


# Apply the monkey patch
db_config.construct_dsn = construct_dsn_no_ssl

# Monkey-patch oauth_setup to return our OpenAI API key instead of doing OAuth
import services.src.connections.oauth as oauth_setup


def setup_oauth_local():
    """Return the OpenAI API key instead of doing OAuth"""
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    logger.info(f"Using OpenAI API key instead of OAuth (key: {api_key[:10]}...)")
    return api_key


# Apply the OAuth monkey patch
oauth_setup.setup_oauth = setup_oauth_local


def test_full_pipeline_greeting(api_key: str):
    """Test full pipeline with a greeting (should trigger direct response)"""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("Testing Full Pipeline - Greeting Query")
    print("=" * 60)

    conversation = [{"role": "user", "content": "Hello! What can you help me with?"}]

    try:
        print("\nStreaming response:")
        print("-" * 60)

        response_text = ""
        for chunk in model(conversation, api_key):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk

        print("\n" + "-" * 60)
        print(f"\n✓ Response received ({len(response_text)} characters)")
        return True

    except Exception as e:
        print(f"\n✗ Full pipeline test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_full_pipeline_context_question(api_key: str):
    """Test full pipeline with a question about previous context"""
    from services.src.chat_model.model import model

    print("\n" + "=" * 60)
    print("Testing Full Pipeline - Context Question")
    print("=" * 60)

    conversation = [
        {
            "role": "user",
            "content": "My company reported $100M in revenue last quarter.",
        },
        {
            "role": "assistant",
            "content": "Thank you for sharing that information. Your company reported $100M in revenue last quarter.",
        },
        {"role": "user", "content": "What did I just tell you about our revenue?"},
    ]

    try:
        print("\nStreaming response:")
        print("-" * 60)

        response_text = ""
        for chunk in model(conversation, api_key):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk

        print("\n" + "-" * 60)
        print(f"\n✓ Response received ({len(response_text)} characters)")
        return True

    except Exception as e:
        print(f"\n✗ Full pipeline test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_process_monitoring_logs():
    """Check if process monitoring wrote to the database"""
    import psycopg2

    print("\n" + "=" * 60)
    print("Checking Process Monitoring Logs")
    print("=" * 60)

    try:
        conn = psycopg2.connect(
            host="localhost",
            port=34532,
            user="alexwday",
            password="",
            dbname="finance-dev",
        )
        cursor = conn.cursor()

        # Check for recent IRIS logs
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM process_monitor_logs
            WHERE model_name = 'iris'
            AND log_timestamp > NOW() - INTERVAL '2 minutes'
        """
        )
        recent_count = cursor.fetchone()[0]

        if recent_count > 0:
            print(f"✓ Found {recent_count} recent process monitoring log(s) for IRIS")

            # Show the recent logs
            cursor.execute(
                """
                SELECT stage_name, status, duration_ms, total_tokens, total_cost
                FROM process_monitor_logs
                WHERE model_name = 'iris'
                AND log_timestamp > NOW() - INTERVAL '2 minutes'
                ORDER BY log_id DESC
                LIMIT 10
            """
            )
            logs = cursor.fetchall()

            print("\nRecent IRIS logs:")
            print(
                f"{'Stage':<25} {'Status':<15} {'Duration(ms)':<12} {'Tokens':<10} {'Cost'}"
            )
            print("-" * 80)
            for stage, status, duration, tokens, cost in logs:
                duration_str = str(duration) if duration else "N/A"
                tokens_str = str(tokens) if tokens else "N/A"
                cost_str = f"${cost:.4f}" if cost else "N/A"
                print(
                    f"{stage:<25} {status:<15} {duration_str:<12} {tokens_str:<10} {cost_str}"
                )

            cursor.close()
            conn.close()
            return True
        else:
            print("⚠️  No recent IRIS logs found in process_monitor_logs")
            print("   This might indicate process monitoring is not writing to DB")
            cursor.close()
            conn.close()
            return False

    except Exception as e:
        print(f"✗ Error checking process monitoring logs: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("=" * 60)
    print("IRIS Full Pipeline Test")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  Please set your OpenAI API key:")
        print("   export OPENAI_API_KEY='sk-...'")
        return 1

    print(f"\n✓ Using OpenAI API key: {api_key[:10]}...")
    print(f"✓ Model: gpt-4.1-mini")
    print(f"✓ Endpoint: https://api.openai.com/v1")

    # Run tests
    results = {}

    # Test 1: Greeting (should be quick, direct response)
    results["Greeting Query"] = test_full_pipeline_greeting(api_key)

    # Test 2: Context question (should use direct response from conversation)
    results["Context Question"] = test_full_pipeline_context_question(api_key)

    # Check process monitoring
    results["Process Monitoring"] = check_process_monitoring_logs()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! Full IRIS pipeline is working.")
        print("   Process monitoring is writing to database correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
