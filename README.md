# IRIS Financial Assistant

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**IRIS** (Intelligent Retrieval & Interaction System) is an advanced AI agent-based system designed to answer user queries by interacting with diverse financial data sources at RBC.

## Quick Start

### Automated Setup (Recommended for fresh clones)

```bash
# One-command setup for fresh clones
./setup_fresh_clone.sh

# Edit environment variables (required)
nano .env

# Start the server
python start_server.py
```

### Manual Setup

```bash
# Install dependencies
pip install -e .
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Start the API server
python start_server.py

# Test the API
python test_api.py

# Open the chat interface
open chat_interface.html
```

## Documentation

- **[🚀 Complete Deployment Guide](docs/production-deployment.md)** - Full setup, testing, and deployment
- **[📖 Project Overview](docs/project-overview.md)** - Detailed system documentation  
- **[🗃️ Database Schema](docs/database-schema.sql)** - PostgreSQL schema
- **[🤖 Agent Documentation](docs/agents/)** - Individual agent guides

## System Architecture

IRIS uses a modular pipeline of specialized agents:

```
User Query → Router → Clarifier → Planner → Database Subagents → Summarizer → Response
                                    ↓
                              Direct Response Agent
```

### Key Components

- **FastAPI Backend** (`iris/src/api.py`) - REST API with streaming support
- **Agent Pipeline** (`iris/src/agents/`) - Specialized AI agents for different tasks
- **Database Subagents** (`iris/src/agents/database_subagents/`) - Query internal/external sources
- **Chat Interface** (`chat_interface.html`) - Modern web UI for conversations
- **LLM Connectors** (`iris/src/llm_connectors/`) - OpenAI API integration

## Development

```bash
# Code quality
black iris/
mypy iris/
pytest

# Build and run
python start_server.py
```

## License

Proprietary and confidential - RBC Financial Group.