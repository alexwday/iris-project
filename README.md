# IRIS Project - Comprehensive Overview

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Overview

IRIS (Intelligent Retrieval & Interaction System) is an advanced AI agent-based system designed to answer user queries by interacting with a diverse set of internal and external financial data sources. It employs a modular pipeline of specialized agents to route, clarify, plan, query, and synthesize responses efficiently and accurately.

## Core Features

- **Agent Pipeline:** A structured flow of agents including Router, Clarifier, Planner, Database Router, Summarizer, and Direct Response agents.
- **Multi-Source Data Integration:** Connects to various internal databases (e.g., Memos, Wiki, PAR, ICFR, Cheatsheets, CAPM) and external sources (EY, IASB, KPMG, PwC) through dedicated subagents.
- **Intelligent Query Handling:** Routes queries to appropriate agents, clarifies research goals, and plans database queries.
- **Concurrent Database Access:** Executes parallel queries across multiple databases for faster results.
- **Response Synthesis:** Aggregates and summarizes findings into coherent, traceable answers.

## Project Structure

```
iris-project/
├── .gitignore
├── init-schema.sql
├── README.md                 # This file
├── setup.py
├── iris/
│   └── src/
│       ├── agents/           # Core AI agents and subagents ([README](./iris/src/agents/README.md))
│       ├── chat_model/       # Orchestration logic ([README](./iris/src/chat_model/README.md))
│       ├── conversation_setup/ # Conversation management ([README](./iris/src/conversation_setup/README.md))
│       ├── global_prompts/   # Shared prompts and statements ([README](./iris/src/global_prompts/README.md))
│       ├── initial_setup/    # Configuration, DB, logging, OAuth, SSL ([README](./iris/src/initial_setup/README.md))
│       └── llm_connectors/   # LLM API connectors ([README](./iris/src/llm_connectors/README.md))
├── notebooks/                # Jupyter notebooks for testing and analysis ([README](./notebooks/README.md))
└── venv/                    # Python virtual environment (if created)
```

## Detailed Module Descriptions

### Agents (`iris/src/agents/`)

The core AI agents form the processing pipeline for user queries:

- **Agent Router:** Determines if a query requires database research or direct response.
- **Agent Clarifier:** Refines the research goal and scope.
- **Agent Planner:** Plans which database subagents to query.
- **Database Subagents:** Specialized subagents for querying specific internal and external data sources. See [Database Subagents README](./iris/src/agents/database_subagents/README.md) for details.
- **Agent Summarizer:** Synthesizes research findings into coherent responses.
- **Agent Direct Response:** Provides direct answers from conversation history when research is unnecessary.

Each agent has its own directory with implementation and configuration files.

### Database Subagents (`iris/src/agents/database_subagents/`)

This directory contains subagents tailored to specific data sources:

- **Internal Sources:** e.g., CAPM, Cheatsheets, Compliance, ESG, Ext Reporting, Global Finance Standards, ICFR, Management Reporting, Memos, PAR, Process and Controls, Wiki.
- **External Sources:** e.g., EY, IASB, KPMG, PwC.

Each subagent directory includes querying logic, prompt templates, and integration with process monitoring.

Example: The Internal CAPM subagent ([README](./iris/src/agents/database_subagents/internal_capm/README.md)) implements a multi-step querying and synthesis process for RBC accounting policy manuals.

### Chat Model Orchestration (`iris/src/chat_model/`)

Contains the main orchestration logic managing the agent pipeline, environment setup, concurrent database querying, and response generation. Key files include `model.py` and `model_settings.py`.

### Conversation Setup (`iris/src/conversation_setup/`)

Manages conversation history processing, filtering, and formatting to provide consistent input to agents. Includes conversation processing logic and configuration.

### Global Prompts (`iris/src/global_prompts/`)

Provides shared prompt utilities and statements to ensure consistent context and instructions across agents. Includes project context, database descriptions, fiscal calendar, and usage restrictions.

### Initial Setup (`iris/src/initial_setup/`)

Handles foundational configuration such as database connections, centralized logging, process monitoring, OAuth authentication, and SSL setup.

### LLM Connectors (`iris/src/llm_connectors/`)

Implements connectors to large language model APIs, primarily OpenAI, handling authentication, retries, streaming, and usage logging.

### Notebooks (`notebooks/`)

Contains Jupyter notebooks for testing, debugging, data export, process monitoring analysis, and end-to-end pipeline testing.

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL installed and running

### Installation & Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd iris-project
   ```

2. Set up the PostgreSQL database named `maven-finance` with the schema in `init-schema.sql`.

3. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   ```

4. Install dependencies:
   ```bash
   pip install -e .
   pip install -e ".[dev]"
   ```

### Usage

Run the primary test notebook:
```bash
jupyter notebook
```
Open `notebooks/test_notebook.ipynb` and modify the `conversation` variable to input queries.

## Development

- Code style enforced with Black.
- Type checking with MyPy.
- Testing with Pytest.

Run quality checks:
```bash
black iris/
mypy iris/
pytest
```

## Troubleshooting

- Ensure PostgreSQL is running and accessible.
- Verify database credentials in `iris/src/initial_setup/db_config.py`.
- Activate the virtual environment before running notebooks.

## Contributing

Follow existing code style and add tests for new features. Use feature branches and pull requests.

## License

Proprietary and confidential.

## Acknowledgments

- OpenAI API for language model capabilities.
- PostgreSQL for database integration.
