# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# IRIS Project Guidelines for Claude

## Build Commands
- Install: `pip install -e .`
- Install dev tools: `pip install -e ".[dev]"`
- Run notebook: `jupyter notebook notebooks/test_notebook.ipynb`
- Lint: `black iris/`
- Type check: `mypy iris/`

## Testing
- Run tests: `pytest`
- Single test: `pytest path/to/test.py::test_function_name`
- With coverage: `pytest --cov=iris`

## Code Style

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