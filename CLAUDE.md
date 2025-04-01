# IRIS Project Guidelines for Claude

## Build Commands
- Install: `pip install -e .`
- Run notebook: `jupyter notebook notebooks/test_notebook.ipynb`

## Testing
- Run tests: `pytest`
- Single test: `pytest path/to/test.py::test_function_name`

## Code Style

### Imports
- External imports first, then relative imports
- Import specific functions rather than entire modules
- Group related imports together

### Formatting
- 4-space indentation
- 80-100 character line limit
- Triple double quotes for docstrings (`"""`)
- Google-style docstrings with Args/Returns/Raises sections

### Naming & Types
- snake_case for functions and variables
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- Document types in docstrings

### Error Handling
- Use custom exception classes when appropriate
- Catch specific exceptions
- Provide detailed error messages
- Log errors at appropriate levels
- Truncate sensitive information in logs