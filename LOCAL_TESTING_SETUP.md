# Local Testing Setup for IRIS

This document explains how to test the IRIS pipeline locally using OpenAI API instead of RBC's enterprise infrastructure.

## Overview

The IRIS codebase is designed for RBC's production environment with:
- OAuth authentication via RBC's API gateway
- SSL-enabled PostgreSQL connections
- RBC CA certificate bundle for HTTPS requests

For local development, we bypass these requirements using:
1. **Monkey-patching** - Runtime function overrides in test scripts (no src code modifications)
2. **System CA bundle symlink** - Points to macOS system certificates
3. **Environment variable overrides** - Configure models and endpoints

---

## What Was Done

### 1. SSL Certificate Setup

**Problem:** `services/src/initial_setup/ssl_setup.py` requires `rbc-ca-bundle.cer` to exist.

**Solution:** Created symlink to system CA bundle:
```bash
ln -sf /etc/ssl/cert.pem services/src/initial_setup/rbc-ca-bundle.cer
```

**Why this works:** OpenAI's API uses standard trusted CAs that are in the macOS system bundle. The code sets `REQUESTS_CA_BUNDLE` environment variable to this path for HTTPS requests.

**Location:** `services/src/initial_setup/rbc-ca-bundle.cer` → `/etc/ssl/cert.pem`

---

### 2. Individual Agent Testing (test_local_openai.py)

**What it tests:**
- Router Agent
- Direct Response Agent
- Clarifier Agent
- Planner Agent

**Monkey-patches applied:** None needed! These agents accept `token` parameter directly.

**How it works:**
```python
# Set environment to use OpenAI
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
os.environ["IRIS_MODEL_SMALL"] = "gpt-4.1-mini"
os.environ["IRIS_MODEL_LARGE"] = "gpt-4.1-mini"

# Call agents directly with OpenAI API key
routing_decision, usage = get_routing_decision(
    conversation=conversation,
    token=api_key  # Pass OpenAI key directly
)
```

**Status:** ✅ All 4 agents pass tests

---

### 3. Full Pipeline Testing (test_full_pipeline.py)

**What it tests:**
- Complete `model()` function flow
- Process monitoring database writes
- SSL and OAuth initialization

**Problem 1: OAuth Setup**

The `model()` function calls `setup_oauth()` which tries to authenticate with RBC's OAuth server.

**Monkey-patch solution:**
```python
import services.src.initial_setup.oauth_setup as oauth_setup

def setup_oauth_local():
    """Return the OpenAI API key instead of doing OAuth"""
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key

# Apply the monkey patch at runtime
oauth_setup.setup_oauth = setup_oauth_local
```

**What this does:**
- Replaces the `setup_oauth()` function at runtime (doesn't modify src files)
- Returns OpenAI API key instead of calling RBC's OAuth endpoint
- The rest of the code thinks it got an OAuth token and uses it for LLM calls

---

**Problem 2: PostgreSQL SSL Requirement**

The database connection code hardcodes `sslmode='require'` but local PostgreSQL runs without SSL.

**Monkey-patch solution:**
```python
import services.src.initial_setup.db_config as db_config

def construct_dsn_no_ssl(params: dict, for_sqlalchemy=True):
    """Modified version that uses sslmode=disable for local postgres"""
    hosts = params.get('host')
    port = params.get('port')
    database = params.get('dbname')
    user = params.get('user')
    password = params.get('password')

    # ... validation code ...

    if for_sqlalchemy:
        dsn = (
            f"postgresql+psycopg2://{user}:{password}@{host_port}/{database}?"
            f"sslmode=disable&target_session_attrs=read-write"  # ← Changed from 'require'
        )
    else:
        dsn = (
            f"dbname='{database}' user='{user}' password='{password}' "
            f"host='{hosts}' port='{port}' sslmode='disable' "  # ← Changed from 'require'
            f"target_session_attrs='read-write'"
        )

    return dsn

# Apply the monkey patch
db_config.construct_dsn = construct_dsn_no_ssl
```

**What this does:**
- Replaces the `construct_dsn()` function at runtime
- Changes SSL mode from 'require' to 'disable'
- Allows connection to local PostgreSQL without SSL

---

**Environment Variables Set:**
```python
# Database configuration for local postgres
os.environ["VECTOR_POSTGRES_DB_HOST"] = "localhost"
os.environ["VECTOR_POSTGRES_DB_PORT"] = "34532"
os.environ["VECTOR_POSTGRES_DB_USERNAME"] = "alexwday"
os.environ["VECTOR_POSTGRES_DB_PASSWORD"] = ""
os.environ["VECTOR_POSTGRES_DB_NAME"] = "finance-dev"

# Skip SSL certificate expiry check
os.environ["IRIS_SSL_CHECK_CERT_EXPIRY"] = "false"
```

**Status:** ✅ Full pipeline works! The monkey-patches successfully allow:
- OAuth replaced with OpenAI API key
- SSL disabled for local PostgreSQL
- Process monitoring writes to database
- Router and Direct Response agents working end-to-end

---

## Local PostgreSQL Setup

**Database:** `maven-finance` (port 34532)
- Contains: `apg_catalog` (10 documents), `apg_content` (20 sections)
- Missing: `iris_textbook_database` (needed for semantic search)

**Database:** `finance-dev` (port 34532)
- Contains: `process_monitor_logs` table
- Used for: Process monitoring writes during test runs

**Configuration:**
- Host: localhost
- Port: 34532 (non-standard, set in local postgres config)
- No SSL enabled
- User: alexwday (no password)

---

## Key Principles

### 1. No Source Code Modifications
All changes are applied at **runtime** in test scripts only. The `services/src/` folder remains unchanged and matches the remote repository.

### 2. Monkey-Patching
```python
# This doesn't modify the source file
module.function_name = my_replacement_function

# The replacement only exists while the test script runs
# Next time you import the module normally, you get the original
```

### 3. Environment Variables
The code reads configuration from environment variables. We override them before importing:
```python
os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
# Now when the code reads config.RBC_BASE_URL, it gets OpenAI's URL
```

---

## What Works Locally

✅ **Individual agent tests** (`test_local_openai.py`)
- Router agent
- Direct response agent
- Clarifier agent
- Planner agent
- All using OpenAI API (gpt-4.1-mini)
- No database access needed

✅ **Process monitoring**
- Writes to local `finance-dev` database
- Logs stages, timing, token usage

✅ **Full pipeline end-to-end**
- Router → Direct Response flow working
- OAuth successfully bypassed with OpenAI key
- SSL successfully disabled for local PostgreSQL
- All logging and monitoring functional

✅ **Catalog search** (if you had data)
- Would work with `apg_catalog` + `apg_content` tables
- Tables exist but need embedding columns added

---

## What Doesn't Work Locally

❌ **Semantic search**
- Missing `iris_textbook_database` table
- This is the table you're designing schemas for

❌ **Database research queries**
- Need both catalog and semantic tables populated with embeddings
- Need pgvector extension installed

---

## Running Tests

### Individual Agents (Recommended)
```bash
# Set your OpenAI API key
export OPENAI_API_KEY='sk-...'

# Run agent tests
python test_local_openai.py
```

**Expected output:**
```
✓ PASS - Router
✓ PASS - Direct Response
✓ PASS - Clarifier
✓ PASS - Planner

Passed: 4/4
```

### Full Pipeline
```bash
export OPENAI_API_KEY='sk-...'
python test_full_pipeline.py
```

**Expected output:**
```
✓ PASS - Greeting Query
✓ PASS - Context Question
✓ PASS - Process Monitoring

Passed: 3/3

🎉 All tests passed! Full IRIS pipeline is working.
   Process monitoring is writing to database correctly.
```

---

## File Locations

### Test Scripts (Not in src/)
- `test_local_openai.py` - Individual agent tests
- `test_full_pipeline.py` - Full pipeline test with monkey-patches

### Modified for Local (Symlink, not code)
- `services/src/initial_setup/rbc-ca-bundle.cer` → `/etc/ssl/cert.pem`

### Source Code (Unchanged)
- `services/src/` - All files match remote main exactly
- No modifications for local testing

---

## Cleanup

To remove local testing setup:

```bash
# Remove symlink
rm services/src/initial_setup/rbc-ca-bundle.cer

# Remove test files (optional)
rm test_local_openai.py test_full_pipeline.py

# Unset environment variables
unset OPENAI_API_KEY
```

The source code (`services/src/`) remains unchanged and ready for production deployment.

---

## Why This Approach?

1. **No src modifications** - Code stays synchronized with IT's version
2. **Reversible** - Delete test files and symlink, you're back to production-ready
3. **Educational** - Shows how the components work independently
4. **Safe** - Can't accidentally commit local testing hacks to production code

---

## Next Steps

To enable full local testing, you would need:

1. Install pgvector extension in PostgreSQL
2. Add embedding columns to `apg_catalog`:
   - `document_description_embedding` (vector(2000))
   - `document_usage_embedding` (vector(2000))
3. Create and populate `iris_textbook_database` table
4. Generate embeddings for all content using OpenAI's embedding API

This is the work you're planning in `RESEARCH_DB_ENHANCEMENTS.md`.
