# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# IRIS Project Guidelines for Claude

## Project Structure
```
iris-project/
├── services/src/        # Main application code (DO NOT MODIFY - matches IT version)
├── testing/             # Local testing scripts
│   ├── diff_tool.py     # Directory comparison tool
│   ├── test_local_openai.py      # Individual agent tests
│   └── test_full_pipeline.py     # Full pipeline tests
├── notes/               # Documentation
│   ├── LOCAL_TESTING_SETUP.md    # How to test locally
│   └── RESEARCH_DB_ENHANCEMENTS.md  # Database schema planning
├── classes/             # Compatibility layer classes
├── config/              # Configuration wrappers
├── m9db/                # Mock reporting database
└── [config files]
```

## IMPORTANT: Source Code Restrictions

**DO NOT MODIFY `services/src/` CODE**
- The `services/src/` folder must exactly match IT's version (commit 5c1ded0)
- Any changes to src will break synchronization with IT's deployment
- For local testing modifications, use monkey-patching in test scripts only
- See `notes/LOCAL_TESTING_SETUP.md` for local testing approach

## Build Commands
- Install: `pip install -e .`
- Install dev tools: `pip install -e ".[dev]"`
- Start server: `python start_server.py`
- Lint: `black services/`
- Type check: `mypy services/src/`

## Testing

### Local Testing with OpenAI
```bash
# Set your OpenAI API key
export OPENAI_API_KEY='sk-...'

# Test individual agents (Router, Clarifier, Planner, Direct Response)
python testing/test_local_openai.py

# Test full pipeline with monkey-patches
python testing/test_full_pipeline.py
```

### Local Setup Requirements
1. PostgreSQL running on port 34532
2. Databases: `maven-finance`, `finance-dev`
3. SSL cert symlink (create if needed):
   ```bash
   ln -sf /etc/ssl/cert.pem services/src/initial_setup/rbc-ca-bundle.cer
   ```

See `notes/LOCAL_TESTING_SETUP.md` for complete setup instructions.

## Code Style

### Source Code (`services/src/`)
- **DO NOT MODIFY** - Must match IT version exactly
- Includes specific formatting: trailing spaces, line endings
- Any changes must be coordinated with IT team

### Testing Scripts (`testing/`)
- Follow standard Python conventions
- Use monkey-patching for local modifications
- Document any patches clearly

### Imports
- External imports first, then relative imports
- Import specific functions rather than entire modules
- Group related imports together

### Formatting
- 4-space indentation (enforced by Black)
- 88 character line limit (Black default)
- Triple double quotes for docstrings (`"""`)
- Google-style docstrings with Args/Returns/Raises sections

### Naming & Types
- snake_case for functions and variables
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- Document types in docstrings and use type hints

### Error Handling
- Use custom exception classes when appropriate
- Catch specific exceptions
- Provide detailed error messages
- Log errors at appropriate levels
- Truncate sensitive information in logs

## Local Development Workflow

1. **Never modify `services/src/` directly**
2. Use test scripts in `testing/` for local development
3. Use monkey-patching to override functions at runtime (see examples in test scripts)
4. Test changes with local OpenAI API before any src modifications
5. Coordinate any necessary src changes with IT team

## Database

### Local PostgreSQL Setup
- Host: localhost
- Port: 34532 (non-standard)
- Databases:
  - `maven-finance`: Contains `apg_catalog`, `apg_content` tables
  - `finance-dev`: Contains `process_monitor_logs` table

### Missing for Full Functionality
- `iris_textbook_database` table (for semantic search)
- Embedding columns in `apg_catalog`
- pgvector extension

See `notes/RESEARCH_DB_ENHANCEMENTS.md` for planned schema enhancements.

## Deployment

This codebase is designed for RBC's production environment:
- OAuth authentication via RBC's API gateway
- SSL-enabled PostgreSQL
- RBC CA certificate bundle
- Azure OpenAI endpoints

For production deployment, all IT modifications in `services/src/` must be preserved exactly.
