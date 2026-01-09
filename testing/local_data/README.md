# Local IRIS Development Environment

This directory contains everything needed to run and test IRIS locally with sample data and your OpenAI API key.

## Quick Start

```bash
# 1. Install pgvector (if not already installed)
brew install pgvector

# 2. Create tables in local PostgreSQL
psql -p 34532 -d maven-finance -f setup_local_db.sql

# 3. Set your OpenAI API key
export OPENAI_API_KEY='sk-...'

# 4. Generate and insert sample data
cd /Users/alexwday/Projects/iris-project/testing/local_data
python populate_local_db.py

# 5. Run the full integration test
python test_full_local.py
```

## Files

| File | Purpose |
|------|---------|
| `setup_local_db.sql` | Creates tables with pgvector support |
| `sample_data_definitions.py` | Defines sample document structures |
| `populate_local_db.py` | Generates sample data using GPT-4o-mini |
| `test_full_local.py` | Full pipeline integration tests |
| `README.md` | This file |

## Prerequisites

### 1. PostgreSQL with pgvector

```bash
# Install pgvector extension
brew install pgvector

# Verify PostgreSQL is running
pg_isready -p 34532

# Create database if needed
createdb -p 34532 maven-finance
```

### 2. Python Dependencies

```bash
# From project root
pip install openai psycopg2-binary pgvector
```

### 3. OpenAI API Key

Get your API key from https://platform.openai.com/api-keys

```bash
export OPENAI_API_KEY='sk-...'
```

## How It Works

### No Source Code Modifications

All local environment setup is done through:

1. **Environment Variables** - Set before imports to override config:
   ```python
   os.environ["AZURE_BASE_URL"] = "https://api.openai.com/v1"
   ```

2. **Monkey Patching** - Replace functions at runtime:
   ```python
   oauth_setup.setup_oauth = setup_oauth_local  # Returns OpenAI key
   db_config.construct_dsn = construct_dsn_no_ssl  # Disables SSL
   ```

3. **Same Database Schema** - Sample data uses identical table structures as production.

### Sample Data

The sample data includes:

**Internal Documents (apg_catalog + apg_content):**
- `internal_capm`: 3 policy documents (Revenue, Lease, Financial Instruments)
- `internal_par`: 2 PAR memos (Cloud Computing, Crypto Assets)

**External Documents (iris_semantic_search):**
- `external_ey`: EY Lease Accounting Guide (3 chapters, ~18 chunks)
- `external_pwc`: PwC Revenue Recognition Guide (2 chapters, ~12 chunks)

Each document has AI-generated:
- Descriptions and usage statements
- Section content (2-3 paragraphs per page)
- Vector embeddings (2000 dimensions)

## Estimated Costs

| Operation | Tokens | Cost |
|-----------|--------|------|
| Generate 5 internal docs | ~15,000 | ~$0.02 |
| Generate 30 external chunks | ~20,000 | ~$0.03 |
| Generate ~40 embeddings | ~40,000 | ~$0.01 |
| **Total setup** | | **~$0.10** |
| Per test run | ~5,000 | ~$0.01 |

## Test Cases

The `test_full_local.py` script runs these tests:

1. **Direct Response** - Greeting should not trigger database research
2. **Internal Research** - Policy question should search `internal_capm`
3. **External Research** - EY guidance question should search `external_ey`
4. **Follow-up Conversation** - Context questions should use conversation history

## Troubleshooting

### "pgvector extension not found"

```bash
# Install pgvector
brew install pgvector

# Load extension
psql -p 34532 -d maven-finance -c "CREATE EXTENSION vector;"
```

### "Connection refused"

```bash
# Check if PostgreSQL is running
pg_isready -p 34532

# Start PostgreSQL (if using Homebrew)
brew services start postgresql@14
```

### "relation does not exist"

```bash
# Create tables
psql -p 34532 -d maven-finance -f setup_local_db.sql
```

### "No sample data found"

```bash
# Populate with sample data
python populate_local_db.py
```

### "OPENAI_API_KEY not set"

```bash
export OPENAI_API_KEY='sk-...'
```

## Development Workflow

1. Make code changes in `services/src/`
2. Run `python test_full_local.py` to test
3. Iterate until tests pass
4. Commit and push to remote
5. Pull to work computer and test with real data

## Adding More Sample Data

Edit `sample_data_definitions.py` to add more documents:

```python
INTERNAL_DOCUMENTS = {
    "internal_capm": [
        {
            "document_name": "New Policy Document",
            "document_type": "policy",
            "num_pages": 3,
            "theme": "Description of the policy",
            "topics": ["Topic 1", "Topic 2", "Topic 3"]
        },
        # ... more documents
    ]
}
```

Then run `python populate_local_db.py` again.

## Resetting Data

To start fresh:

```bash
# Clear all tables and recreate
psql -p 34532 -d maven-finance -f setup_local_db.sql

# Repopulate
python populate_local_db.py
```
