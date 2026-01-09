# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Structure

```
iris-project/
├── services/src/        # Main application code (CAN BE MODIFIED for enhancements)
├── testing/             # Local testing scripts
│   └── local_data/      # Local development environment setup
├── notes/               # Implementation documentation
│   ├── IMPLEMENTATION_PLAN_STEP_BY_STEP.md  # Main enhancement plan
│   ├── NEW_DATABASE_REGISTRY_SCHEMA.md      # Registry schema design
│   └── DATABASE_SCHEMAS.md                  # Current schema reference
├── classes/             # IT compatibility stub (DO NOT MODIFY)
├── config/              # IT compatibility stub (DO NOT MODIFY)
├── m9db/                # IT compatibility stub (DO NOT MODIFY)
└── venv/                # Python virtual environment
```

## Compatibility Stubs (DO NOT MODIFY)

The following folders are **compatibility shims** for IT's infrastructure:

| Folder | Purpose |
|--------|---------|
| `classes/` | Stub for IT's exception classes import path |
| `config/` | Wrapper for IT's `config.config.Config` interface |
| `m9db/` | Mock for IT's reporting database ORM |

**These must remain unchanged** - they allow the code to run locally without IT's infrastructure while maintaining import compatibility.

## Source Code (`services/src/`)

The `services/src/` folder contains the main IRIS application. **This code CAN be modified** for implementing enhancements. When making changes:

- Follow existing code patterns and style
- Maintain compatibility with IT's deployment expectations
- Test locally before committing

## Local Development

### Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Start local server (uses OpenAI API)
export OPENAI_API_KEY='sk-...'
python testing/local_data/start_local_server.py

# Run integration tests
python testing/local_data/test_full_local.py
```

### Local Environment Details

- **Database**: PostgreSQL on port 34532, database `maven-finance`
- **LLM**: OpenAI API (gpt-4o-mini) via environment variable
- **Sample Data**: 5 internal docs, 30 external chunks with embeddings

See `testing/local_data/README.md` for complete setup instructions.

## Code Style

- 4-space indentation (Black formatter)
- 88 character line limit
- Google-style docstrings
- Type hints where practical
- snake_case for functions/variables, PascalCase for classes

## Current Enhancement Work

We are implementing architectural changes to IRIS:
- Universal cascading retrieval (Metadata Subagent + File Research)
- Database registry in PostgreSQL (replacing hardcoded dicts)
- Standardized return formats across all subagents

See `notes/IMPLEMENTATION_PLAN_STEP_BY_STEP.md` for the full plan.
