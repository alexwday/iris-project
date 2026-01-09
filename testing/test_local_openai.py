#!/usr/bin/env python3
"""
Local OpenAI Testing Script for IRIS

Tests the IRIS pipeline components (router, clarifier, planner, direct response)
using your OpenAI API key instead of RBC's OAuth/Azure endpoint.

This skips database retrieval subagents to test everything else.
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

# Import after setting env vars
from services.src.utils.logging_format import configure_logging

configure_logging()

import logging

logger = logging.getLogger(__name__)


def test_router_agent(api_key: str):
    """Test the router agent to see if it can decide research vs direct response"""
    from services.src.agent.router import get_routing_decision

    print("\n" + "=" * 60)
    print("Testing Router Agent")
    print("=" * 60)

    conversation = {
        "messages": [{"role": "user", "content": "Hello! What can you help me with?"}]
    }

    try:
        routing_decision, usage = get_routing_decision(
            conversation=conversation, token=api_key
        )

        print(f"✓ Router decision: {routing_decision.get('decision')}")
        print(f"  Reasoning: {routing_decision.get('reasoning', 'N/A')}")
        if usage:
            print(
                f"  Tokens used: {usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)}"
            )
        return True

    except Exception as e:
        print(f"✗ Router agent failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_direct_response(api_key: str):
    """Test the direct response agent"""
    from services.src.agent.direct_response import response_from_conversation

    print("\n" + "=" * 60)
    print("Testing Direct Response Agent")
    print("=" * 60)

    conversation = {
        "messages": [
            {"role": "user", "content": "What is IFRS?"},
            {
                "role": "assistant",
                "content": "IFRS stands for International Financial Reporting Standards.",
            },
            {
                "role": "user",
                "content": "Can you remind me what you just told me about IFRS?",
            },
        ]
    }

    try:
        print("Streaming response:")
        print("-" * 60)

        response_text = ""
        for chunk in response_from_conversation(
            conversation=conversation, token=api_key
        ):
            if isinstance(chunk, dict) and "usage_details" in chunk:
                usage = chunk["usage_details"]
                print(
                    f"\n✓ Tokens used: {usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)}"
                )
            elif isinstance(chunk, str):
                print(chunk, end="", flush=True)
                response_text += chunk

        print("\n" + "-" * 60)
        return True

    except Exception as e:
        print(f"✗ Direct response failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_clarifier(api_key: str):
    """Test the clarifier agent"""
    from services.src.agent.clarifier import clarify_research_needs

    print("\n" + "=" * 60)
    print("Testing Clarifier Agent")
    print("=" * 60)

    conversation = {
        "messages": [
            {
                "role": "user",
                "content": "What are the revenue recognition rules for software licenses?",
            }
        ]
    }

    try:
        clarifier_decision, usage = clarify_research_needs(
            conversation=conversation, token=api_key
        )

        print(f"✓ Clarifier action: {clarifier_decision.get('action')}")
        print(f"  Scope: {clarifier_decision.get('scope', 'N/A')}")
        print(
            f"  Research statement: {clarifier_decision.get('research_statement', 'N/A')[:100]}..."
        )
        if usage:
            print(
                f"  Tokens used: {usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)}"
            )
        return True

    except Exception as e:
        print(f"✗ Clarifier failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_planner(api_key: str):
    """Test the planner agent"""
    from services.src.agent.planner import create_database_selection_plan
    from services.src.agent.tools.database_metadata import (
        get_available_databases,
    )

    print("\n" + "=" * 60)
    print("Testing Planner Agent")
    print("=" * 60)

    research_statement = "Find RBC's accounting policy on revenue recognition from CAPM"
    available_databases = get_available_databases()

    try:
        plan, usage = create_database_selection_plan(
            research_statement=research_statement,
            token=api_key,
            available_databases=available_databases,
        )

        print(
            f"✓ Plan created with {len(plan.get('selected_databases', []))} databases"
        )
        for i, db_plan in enumerate(plan.get("selected_databases", []), 1):
            print(
                f"  {i}. {db_plan.get('database_id')} - {db_plan.get('query_approach', 'N/A')[:60]}..."
            )
        if usage:
            print(
                f"  Tokens used: {usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)}"
            )
        return True

    except Exception as e:
        print(f"✗ Planner failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("=" * 60)
    print("IRIS Local OpenAI Testing")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  Please set your OpenAI API key:")
        print("   export OPENAI_API_KEY='sk-...'")
        print("\nOr run with:")
        print("   OPENAI_API_KEY='sk-...' python test_local_openai.py")
        return 1

    print(f"\n✓ Using OpenAI API key: {api_key[:10]}...")
    print(f"✓ Model: gpt-4.1-mini")
    print(f"✓ Endpoint: https://api.openai.com/v1")

    # Run tests
    results = {
        "Router": test_router_agent(api_key),
        "Direct Response": test_direct_response(api_key),
        "Clarifier": test_clarifier(api_key),
        "Planner": test_planner(api_key),
    }

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
        print("\n🎉 All tests passed! IRIS core pipeline is working.")
        print("   (Database retrieval subagents not tested)")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
