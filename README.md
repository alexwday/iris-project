# IRIS - Intelligent Retrieval & Interaction System

An AI agent-based system for answering user queries by searching and synthesizing financial data sources. Includes a chat API (`services/src/`) and a document ingestion pipeline (`doc_refresh/`).

## Prerequisites

- **Python 3.13+**
- **PostgreSQL 14+** with the `pgvector` extension
- **OpenAI API key** (for local development)
- **LibreOffice** (only if processing DOCX files via doc_refresh)

## Quick Start

### 1. Clone and set up the virtual environment

```bash
git clone <repo-url> iris-project
cd iris-project
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
# Core dependencies (IRIS chat service)
pip install -e .

# Doc refresh pipeline dependencies (additional)
pip install sqlalchemy pymupdf4llm tiktoken

# Development tools (optional)
pip install -e ".[dev]"
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values. For **local development**, override with `.env.local`:

| Variable | Description | Local Default |
|----------|-------------|---------------|
| `VECTOR_POSTGRES_DB_HOST` | PostgreSQL host | `localhost` |
| `VECTOR_POSTGRES_DB_PORT` | PostgreSQL port | `34532` |
| `VECTOR_POSTGRES_DB_NAME` | Database name | `maven-finance` |
| `VECTOR_POSTGRES_DB_USERNAME` | Database user | your OS username |
| `VECTOR_POSTGRES_DB_PASSWORD` | Database password | (empty for local) |
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OAUTH_URL` | OAuth endpoint | (clear for local) |
| `AZURE_BASE_URL` | Azure LLM endpoint | (clear for local) |

Clearing `OAUTH_URL` and `AZURE_BASE_URL` makes the system use the OpenAI API directly with your `OPENAI_API_KEY`.

### 4. Set up the database

Create the PostgreSQL database and enable pgvector:

```sql
CREATE DATABASE "maven-finance";
\c maven-finance
CREATE EXTENSION IF NOT EXISTS vector;
```

Create the required tables by running each schema file:

```bash
psql -h localhost -p 34532 -d maven-finance -f db_config/schemas/iris_database_registry.sql
psql -h localhost -p 34532 -d maven-finance -f db_config/schemas/prompts.sql
psql -h localhost -p 34532 -d maven-finance -f db_config/schemas/iris_document_metadata.sql
psql -h localhost -p 34532 -d maven-finance -f db_config/schemas/iris_document_chunks.sql
psql -h localhost -p 34532 -d maven-finance -f db_config/schemas/process_monitor_logs.sql
```

### 5. Populate initial data

```bash
# Load registry entries, prompts, and sample test documents
python db_config/populate_initial_data.py

# Or skip sample documents (registry + prompts only)
python db_config/populate_initial_data.py --skip-sample-data

# Preview what would be loaded
python db_config/populate_initial_data.py --dry-run
```

This loads:
- **Database registry** entries into `iris_database_registry`
- **IRIS prompts** (model=`iris`) for the chat agents
- **Doc refresh prompts** (model=`doc_refresh`) for the ingestion pipeline
- **Sample data** (optional): 3 test documents with 18 chunks into `internal_wiki`

## Running the IRIS Chat Service

```bash
source venv/bin/activate
export OPENAI_API_KEY='sk-...'
python start_server.py
```

The FastAPI server starts on **http://localhost:8000**.

- **Chat interface**: Open `chat_interface.html` in your browser
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### Chat API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send a message (streaming response) |
| POST | `/reset` | Reset conversation history |
| GET | `/health` | Health check |
| GET | `/databases` | List available databases |

## Running the Doc Refresh Pipeline

The doc_refresh pipeline processes PDF/DOCX files into structured, searchable chunks in PostgreSQL.

### Configuration

Set these additional environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `BASE_PATH` | Root folder containing document subfolders | `/path/to/documents` |
| `DATABASE_NAMES` | Comma-separated folder names to process | `internal_wiki,policies` |
| `FILE_SOURCE_MODE` | File access mode | `local` or `nas` |

If `DATABASE_NAMES` is empty, the pipeline auto-discovers subfolders under `BASE_PATH`.

### Running

```bash
source venv/bin/activate
export OPENAI_API_KEY='sk-...'

# Standard run
python -m doc_refresh.main

# Dry run (no database changes)
python -m doc_refresh.main --dry-run

# Force reprocess all files (ignore unchanged)
python -m doc_refresh.main --force

# Debug logging
python -m doc_refresh.main --log-level DEBUG
```

### Pipeline stages

1. **Scan** - Compares folders against PostgreSQL, detects new/changed/deleted files
2. **Extract** - Converts PDF (pymupdf4llm) and DOCX (LibreOffice headless) to text
3. **Process** - LLM-based metadata extraction, section detection, summarization, embeddings
4. **Validate** - Validates processed documents
5. **Database** - Syncs to PostgreSQL (`iris_document_metadata` + `iris_document_chunks`)
6. **Report** - Generates a JSON summary report

### Testing individual stages

```bash
# Test stage 1 only (scan)
python -m doc_refresh.testing.test_stages --stage 1

# Test all stages with dry-run
python -m doc_refresh.testing.test_stages --stage all
```

## Environment Variables Reference

See `.env.example` for the full list. Key groups:

| Group | Variables | Purpose |
|-------|-----------|---------|
| Database | `VECTOR_POSTGRES_DB_*` | PostgreSQL connection |
| Auth | `OAUTH_URL`, `CLIENT_ID`, `CLIENT_SECRET` | OAuth (production only) |
| LLM | `OPENAI_API_KEY`, `AZURE_BASE_URL` | LLM provider |
| Models | `IRIS_MODEL_SMALL`, `IRIS_MODEL_LARGE`, `IRIS_MODEL_EMBEDDING` | Model selection |
| Logging | `IRIS_LOG_LEVEL` | Log verbosity |
| Doc Refresh | `BASE_PATH`, `DATABASE_NAMES`, `FILE_SOURCE_MODE` | Pipeline config |

## Project Structure

```
iris-project/
├── services/src/          # IRIS chat API (FastAPI + agents)
│   ├── api.py             # FastAPI endpoints
│   ├── agents/            # Router, clarifier, planner, summarizer
│   └── connections/       # LLM, OAuth, PostgreSQL connectors
├── doc_refresh/           # Document ingestion pipeline
│   ├── main.py            # Pipeline entry point
│   ├── stages/            # 6-stage processing pipeline
│   ├── connections/       # File source, LLM, database connectors
│   └── utils/             # Config, logging, prompt loading
├── db_config/             # Database schemas and initial data
│   ├── schemas/           # CREATE TABLE SQL files
│   └── populate_initial_data.py
├── chat_interface.html    # Browser-based chat UI
├── start_server.py        # Server launcher
├── setup.py               # Python package definition
├── .env.example           # Environment variable template
├── .env.local             # Local development overrides
├── classes/               # IT compatibility stub (do not modify)
├── config/                # IT compatibility stub (do not modify)
└── m9db/                  # IT compatibility stub (do not modify)
```

## License

Proprietary and confidential - RBC Financial Group.
