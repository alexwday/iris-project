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
- Type hints where practical
- snake_case for functions/variables, PascalCase for classes
- No inline comments - code should be self-documenting through clear naming

## Documentation Standard

All Python files must follow this documentation format consistently.

### Module Docstrings

Every module starts with a paragraph-style docstring explaining:
- What the module does (its responsibility)
- Where it fits in the IRIS architecture (which components use it)
- Key concepts, constants, or patterns worth noting

Written from a developer's perspective for IT staff or future maintainers.

```python
"""
Prompt Loader - Database-backed prompt management.

This module provides prompt loading and caching for all IRIS agents. It connects
to PostgreSQL to fetch versioned prompts at startup, caches them in memory, and
supports runtime context injection for fiscal dates and database availability.
Used by router, clarifier, planner, and summarizer agents during initialization.

Key behavior: Prompts are lazy-loaded on first access if not pre-warmed via
load_all_prompts() at application startup.
"""
```

### Function Docstrings

**Public functions** (no underscore prefix): Brief description + Args + Returns + Raises (if intentional).

```python
def get_prompt(layer: str, name: str, model: str = "iris") -> Tuple[str, List, str]:
    """Retrieve a cached prompt with optional context injection.

    Args:
        layer: Prompt layer (e.g., "agent", "subagent").
        name: Prompt identifier (e.g., "router", "clarifier").
        model: Model namespace for prompt lookup.

    Returns:
        Tuple of (system_prompt, tools_list, user_prompt).

    Raises:
        ValueError: If the requested prompt is not found in cache.
    """
```

**Internal functions** (underscore prefix `_`) and **nested functions**: Brief 1-2 line description only. No Args/Returns/Raises.

```python
def _inject_fiscal_context(prompt: str) -> str:
    """Replace {{FISCAL_CONTEXT}} placeholder with current fiscal period."""
```

### Class Docstrings

Classes get a 1-2 line description. Methods follow function rules (public vs internal).

```python
class ProcessMonitoringManager:
    """Tracks timing, token usage, and stage metrics for pipeline execution."""

    def start_stage(self, stage_name: str) -> None:
        """Begin timing a named stage, creating it if necessary.

        Args:
            stage_name: Identifier for the pipeline stage.
        """

    def _prepare_records(self) -> List[Dict]:
        """Convert stage metrics to database-ready record format."""
```

### Documentation Rules Summary

| Element | Rule |
|---------|------|
| Module docstring | Paragraph: purpose, architecture context, key concepts |
| Module constants | Mentioned in module docstring narrative |
| Public functions | 1-2 lines + Args + Returns + Raises (if intentional) |
| Internal functions (`_`) | 1-2 lines only |
| Nested functions | 1-2 lines only |
| Classes | 1-2 line description |
| Public methods | Same as public functions |
| Private methods (`_`) | Same as internal functions |
| Inline comments | None - use clear naming instead |

### Docstring Content Guidelines

- **Args**: Describe semantic meaning, not type (type hints handle that)
  - ✗ `layer: str - The layer string`
  - ✓ `layer: Prompt layer (e.g., "agent", "subagent")`
- **Returns**: Explain what the value represents, not just its type
- **Raises**: Only document exceptions the function intentionally raises for callers to handle
- **Brevity**: Public functions can exceed 1-2 lines when complexity demands clarity

## Current Enhancement Work

We are implementing architectural changes to IRIS:
- Universal cascading retrieval (Metadata Subagent + File Research)
- Database registry in PostgreSQL (replacing hardcoded dicts)
- Standardized return formats across all subagents

See `notes/IMPLEMENTATION_PLAN_STEP_BY_STEP.md` for the full plan.
