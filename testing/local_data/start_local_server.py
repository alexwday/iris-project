#!/usr/bin/env python3
"""
Start IRIS Server Locally with OpenAI API

This script starts the IRIS FastAPI server configured for local development:
- Uses OpenAI API instead of RBC's Azure endpoint
- Connects to local PostgreSQL (no SSL)
- Bypasses OAuth authentication

Usage:
    export OPENAI_API_KEY='sk-...'
    python start_local_server.py

Then open:
    - Chat Interface: http://localhost:8000 (or open chat_interface.html)
    - API Docs: http://localhost:8000/docs
    - Health Check: http://localhost:8000/health
"""

import os
import sys

# =============================================================================
# ENVIRONMENT SETUP (must happen before any iris imports)
# =============================================================================

# Point to OpenAI instead of RBC Azure
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"

# Use cost-effective models
os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1"
os.environ["IRIS_MODEL_EMBEDDING"] = "text-embedding-3-large"

# Local PostgreSQL config
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_NAME"] = "maven-finance"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = os.getenv(
    "VECTOR_POSTGRES_DB_USERNAME", "alexwday"
)
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

# Skip SSL cert expiry check
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"

# Logging
os.environ["IRIS_LOG_LEVEL"] = "INFO"

# =============================================================================
# MONKEY PATCHES (must happen before iris imports)
# =============================================================================

# Add project root to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Import modules to patch
import services.src.connections.oauth as oauth_setup
import services.src.connections.postgres as db_config

# Patch yaml.safe_load to limit max_tokens for gpt-4o-mini compatibility
import yaml

_original_safe_load = yaml.safe_load


def _patched_safe_load(stream):
    """Patch yaml.safe_load to cap max_tokens at 16000 for gpt-4o-mini."""
    result = _original_safe_load(stream)
    if isinstance(result, dict):
        # Cap max_tokens in model config
        if "model" in result and isinstance(result["model"], dict):
            if result["model"].get("max_tokens", 0) > 16000:
                result["model"]["max_tokens"] = 16000
    return result


yaml.safe_load = _patched_safe_load


def setup_oauth_local():
    """Return OpenAI API key instead of doing OAuth."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key


def construct_dsn_no_ssl(params: dict, for_sqlalchemy=True):
    """Modified DSN constructor that disables SSL for local PostgreSQL."""
    hosts = params.get("host")
    if not hosts:
        raise ValueError("Host is not set or is empty.")

    hosts_list = hosts.split(",")
    port = params.get("port")
    database = params.get("dbname")
    user = params.get("user")
    password = params.get("password")

    if "," in str(port):
        ports = port.split(",")
        if len(ports) != len(hosts_list):
            raise ValueError("The number of ports must match the number of hosts.")
    else:
        ports = [port] * len(hosts_list)

    host_port_pairs = [f"{host}:{p}" for host, p in zip(hosts_list, ports)]

    if for_sqlalchemy:
        primary_host_port = host_port_pairs[0]
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


# Apply patches
oauth_setup.setup_oauth = setup_oauth_local
db_config.construct_dsn = construct_dsn_no_ssl

# Patch config validation to skip OAuth checks for local development
from services.src.utils.env_config import Config


def validate_local():
    """Skip OAuth validation for local development."""
    # Only validate database settings exist
    if not Config.DB_HOST:
        print("Warning: DB_HOST not set")
    return True  # Always return True for local dev


Config.validate = classmethod(lambda cls: validate_local())

# =============================================================================
# START SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n" + "=" * 60)
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("=" * 60)
        print("\nUsage:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  python start_local_server.py")
        print("=" * 60 + "\n")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("IRIS LOCAL DEVELOPMENT SERVER")
    print("=" * 60)
    print(f"\nOpenAI API Key: {api_key[:12]}...")
    print(f"Models: gpt-4o-mini (small/large), text-embedding-3-large")
    print(f"Database: maven-finance @ localhost:34532")
    print("\nEndpoints:")
    print("  Chat Interface: Open chat_interface.html in browser")
    print("  API Docs:       http://localhost:8000/docs")
    print("  Health Check:   http://localhost:8000/health")
    print("  Chat API:       POST http://localhost:8000/chat")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    uvicorn.run(
        "services.src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload since patches won't persist
        log_level="info",
    )
