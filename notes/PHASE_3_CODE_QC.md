# Phase 3: Code Quality Control & Standardization

**Created:** 2024-12-14
**Status:** In Progress

---

## Objective

Comprehensive code review and standardization of all Python files in `services/src/`. Each file will be analyzed, documented, and brought to 10/10 quality standards using flake8, pylint, and black.

---

## Files to Review (23 files)

### Root Level
1. `api.py`

### agent/
2. `agent/clarifier.py`
3. `agent/direct_response.py`
4. `agent/planner.py`
5. `agent/router.py`
6. `agent/summarizer.py`

### agent/tools/
7. `agent/tools/database_metadata.py`
8. `agent/tools/database_router.py`
9. `agent/tools/file_research_subagent.py`
10. `agent/tools/metadata_subagent.py`

### auth/
11. `auth/auth_security.py`

### connections/
12. `connections/llm.py`
13. `connections/oauth.py`
14. `connections/postgres.py`

### model/
15. `model/main.py`

### reporting/
16. `reporting/reporting.py`

### utils/
17. `utils/env_config.py`
18. `utils/fiscal_context.py`
19. `utils/input_sanitizer.py`
20. `utils/logging_format.py`
21. `utils/process_monitoring.py`
22. `utils/prompt_loader.py`
23. `utils/rbc_security.py`

---

## Process for Each File

### Step 1: Analysis (Before Any Changes)

Provide a comprehensive analysis including:

#### 1.1 File Overview
- **Purpose**: What does this file do?
- **Role in System**: Why does it exist? What part of IRIS does it serve?
- **Dependencies**: What does it import? What imports it?

#### 1.2 Function Inventory

For each function in the file, document:
| Function Name | Description | Parameters | Returns |
|---------------|-------------|------------|---------|
| `function_name` | Brief description | List params | Return type |

#### 1.3 Defaults, Fallbacks & Overrides

**Critical**: List ALL instances of:
- Default parameter values (e.g., `def foo(x=10)`)
- Fallback values (e.g., `value = x or default`)
- Environment variable defaults (e.g., `os.getenv("VAR", "default")`)
- Configuration overrides
- Magic numbers or hardcoded values

Format:
| Location | Type | Value | Explanation |
|----------|------|-------|-------------|
| Line X | env default | `"value"` | **Why it exists**: Detailed explanation of what this controls and why this default was chosen |

**Each default/fallback MUST include an explanation of:**
- What the value controls
- Why this specific default was chosen
- Any implications of changing it

#### 1.4 Classes (if any)

For each class:
- Class name and purpose
- All methods with descriptions
- Class-level attributes

#### 1.5 Logging Review

For each file, assess:
- **Uses logging util?**: Does it import from `utils/logging_format.py`?
- **Logging appropriateness**: Is the logging meaningful and relevant?
- **Remove debug logging**: Identify excessive debug/trace logging that should be removed
- **Standardize logging**: Ensure consistent log levels (INFO for progress, WARNING for issues, ERROR for failures)

Logging should provide:
- Meaningful progress updates (INFO)
- Warning for recoverable issues (WARNING)
- Error details for failures (ERROR)

Logging should NOT include:
- Excessive variable dumps
- Step-by-step debug traces
- Redundant "entering/exiting function" logs

#### 1.6 Shared Utils/Connections Review

Check if the file:
- **Uses shared utilities**: Does it import from `utils/` for common operations?
- **Uses shared connections**: Does it import from `connections/` for LLM/DB access?
- **Has duplicate functionality**: Does it implement something already in utils/connections?

If duplicates found:
1. Document what functionality is duplicated
2. Recommend consolidation into shared module
3. Implement the consolidation during standardization

---

### Step 2: Standardization

#### 2.1 Module Docstring
Every file must have a module-level docstring at the top:
```python
"""
Module Name

Brief description of what this module does.

Functions:
    function_name: Brief description
    another_function: Brief description

Classes:
    ClassName: Brief description (if applicable)
"""
```

#### 2.2 Function Docstrings
Every function must have a Google-style docstring:
```python
def function_name(param1: str, param2: int = 10) -> bool:
    """
    Brief description of what the function does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised
    """
```

#### 2.3 Remove All Comments
- Remove inline comments (`# comment`)
- Remove block comments
- Keep docstrings (they are documentation, not comments)
- Exception: Keep `# type: ignore` if genuinely needed for type checker issues

#### 2.4 Logging Cleanup
- Ensure file uses `from .utils.logging_format import configure_logging`
- Remove excessive debug/trace logging
- Keep meaningful progress, warning, and error logs
- Use lazy formatting: `logger.info("message %s", var)` not f-strings

#### 2.5 Consolidate to Shared Utils
- Replace any local implementations with shared utils/connections imports
- If local implementation is better, move it to shared module
- Remove duplicate code

#### 2.6 Code Formatting
Run in order:
1. `black <file>` - Auto-format
2. `flake8 <file>` - Check style (must be clean, no ignores)
3. `pylint <file>` - Check quality (must be 10/10, no disables)

---

### Step 3: Verification

After changes:
1. Run `black --check <file>` - Must pass
2. Run `flake8 <file>` - Must return no output
3. Run `pylint <file>` - Must return 10.00/10
4. Run relevant tests to ensure no regressions

---

## Quality Standards

### Flake8 Rules
- No line length violations (88 chars for black compatibility)
- No unused imports
- No undefined names
- No style violations
- **NO** `# noqa` comments allowed

### Pylint Rules
- Must achieve 10.00/10 score
- **NO** `# pylint: disable` comments allowed
- All functions documented
- All classes documented
- No code smells

### Black Rules
- 88 character line length
- Standard black formatting
- No manual overrides

### Logging Standards
- Use shared logging utility
- INFO: Meaningful progress updates
- WARNING: Recoverable issues
- ERROR: Failures with context
- No excessive debug output
- Lazy % formatting, not f-strings

### Shared Code Standards
- Use `utils/` for common utilities
- Use `connections/` for LLM/DB connections
- No duplicate implementations across files

---

## Progress Tracking

| # | File | Analysis | Logging | Utils | Docstrings | Comments | Black | Flake8 | Pylint | Status |
|---|------|----------|---------|-------|------------|----------|-------|--------|--------|--------|
| 1 | api.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 2 | agent/clarifier.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 3 | agent/direct_response.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 4 | agent/planner.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 5 | agent/router.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 6 | agent/summarizer.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 7 | agent/tools/database_metadata.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 8 | agent/tools/database_router.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 9 | agent/tools/file_research_subagent.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 10 | agent/tools/metadata_subagent.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 11 | auth/auth_security.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 12 | connections/llm.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 13 | connections/oauth.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 14 | connections/postgres.py | [x] | [x] | [x] | [x] | [x] | [x] | [x] | [x] | ✅ Complete |
| 15 | model/main.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 16 | reporting/reporting.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 17 | utils/env_config.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 18 | utils/fiscal_context.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 19 | utils/input_sanitizer.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 20 | utils/logging_format.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 21 | utils/process_monitoring.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 22 | utils/prompt_loader.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |
| 23 | utils/rbc_security.py | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Pending |

---

## Completed Files

### File #1: api.py ✅

**Changes Made:**
- Added `API_VERSION` constant to eliminate duplicate "1.0.0" strings
- Added `_lazy_import()` helper function for circular import avoidance
- Added `StreamingError` exception class for proper exception hierarchy
- Fixed all exception chaining with `from exc` syntax
- Changed logging from f-strings to lazy % formatting
- Removed 26 inline comments
- Updated all function docstrings to Google-style
- Fixed variable shadowing (`config` → `db_config`)
- Removed unused imports (`time`, `json`)

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes (88 char limit)
- Pylint: ✅ 10.00/10

### File #2: clarifier.py ✅

**Changes Made:**
- Added config constants: MODEL_CAPABILITY, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
- Removed legacy "scope" field from validation
- Changed `require_deep_research` default from False to True
- Extracted helper functions: `_build_messages`, `_extract_tool_response`, `_validate_decision_fields`
- Removed all inline comments
- Changed logging from f-strings to lazy % formatting

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #3: direct_response.py ✅

**Changes Made:**
- Added config constants: MODEL_CAPABILITY, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
- Changed temperature from 0.7 to 0.0
- Extracted helper function: `_build_messages`
- Renamed unused parameter to `_available_databases`
- Removed all inline comments
- Changed logging from f-strings to lazy % formatting

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #4: planner.py ✅

**Changes Made:**
- Added config constants: MODEL_CAPABILITY, MODEL_MAX_TOKENS, MODEL_TEMPERATURE, PLANNER_TOOL_NAME, MAX_CONTEXT_DOCUMENTS
- **MAJOR**: Renamed `apg_catalog_context` parameter to `document_metadata_context`
- Updated context formatting to use new field names (db_source, document_summary)
- Extracted helper functions: `_build_user_message`, `_extract_tool_response`, `_validate_selected_databases`, `_get_system_prompt`, `_call_planner_llm`
- Removed all inline comments
- Changed logging from f-strings to lazy % formatting

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #5: router.py ✅

**Changes Made:**
- Replaced MODEL_CONFIG dict with individual constants: MODEL_CAPABILITY, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
- Extracted helper functions: `_build_messages`, `_extract_tool_response`, `_validate_routing_decision`
- Renamed unused parameter to `_available_databases`
- Removed legacy placeholder replacement code (`{{CONTEXT_START}}`)
- Removed all inline comments (15 total)
- Changed logging from f-strings to lazy % formatting
- Changed broad `Exception` catch to specific exception tuple
- Removed `pass` from RouterError class (docstring is sufficient)

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #6: summarizer.py ✅

**Changes Made:**
- Replaced MODEL_CONFIG dict with individual constants: MODEL_CAPABILITY, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
- Changed temperature from 0.1 to 0.0 for consistency
- **INTERFACE CHANGE**: Renamed `all_metadata_only` to `any_metadata_used` (show footer if ANY db used metadata)
- **INTERFACE CHANGE**: Bundled optional params into `summary_context` dict to reduce argument count
- Renamed constant `METADATA_ONLY_FOOTER` to `METADATA_FOOTER` with updated text
- Extracted helper functions: `_format_research_context`, `_format_reference_context`, `_build_user_message`, `_build_messages`
- Removed all inline comments (15 total)
- Changed logging from f-strings to lazy % formatting
- Removed excessive DEBUG logging
- Changed broad `Exception` catch to specific exception tuple
- Removed `pass` from SummarizerError class
- Updated call site in main.py to use new interface

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #7: database_metadata.py ✅

**Changes Made:**
- **REMOVED**: `search_modes` field from returned dict (dead code - never used)
- **REMOVED**: Legacy fields `query_type`, `content_type`, `use_when` from data dict
- **REMOVED**: `filtered` parameter from `get_available_databases()` (no longer needed)
- **BREAKING**: `get_research_config()` now raises `DatabaseNotFoundError` if db not in registry (instead of returning defaults)
- Added new `DatabaseNotFoundError` exception class
- Simplified XML prompt format (removed CONTENT_TYPE/QUERY_TYPE tags, kept USAGE with db_description)
- Extracted helper `_format_database_xml()` to reduce duplication
- Changed singleton pattern to use dict cache (avoids pylint global-statement warning)
- Moved `Config` import to top level (fixes import-outside-toplevel)
- Removed all inline comments (14 total)
- Changed logging from f-strings to lazy % formatting
- Removed DEBUG logging
- Changed broad `Exception` catch to `RuntimeError` with proper chaining
- Updated callers:
  - api.py: Removed `filtered=True` parameter
  - file_research_subagent.py: Removed try/except around get_research_config, removed DEFAULT_RESEARCH_CONFIG
  - metadata_subagent.py: Same cleanup

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #8: database_router.py ✅

**Changes Made:**
- **BEHAVIOR CHANGE**: `require_deep_research` now defaults to `True` (prefer deep research when in doubt)
- Moved `get_available_databases()` call inside function (avoid import-time database query)
- Extracted helper functions: `_build_error_result()`, `_build_metadata_response()`, `_build_file_research_response()`
- Added type aliases: `MetadataResponse`, `ResearchResponse`, `DatabaseResponse`, `FileLink`, `PageSectionRefs`, `SectionContentMap`, `ReferenceIndex`, `SubagentResult`, `QueryContext`
- Inlined variables to reduce local count under pylint limit (15): `stage1_name`, `stage2_name`, `action`, `error_msg`
- Changed logging from f-strings to lazy % formatting
- Changed broad `Exception` catch to specific exception tuple
- Removed all inline comments

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #9: file_research_subagent.py ✅

**Changes Made:**
- **INTERFACE CHANGE**: `synthesize_single_document()` now takes `synthesis_context` dict instead of individual params
- **INTERFACE CHANGE**: `query_file_research_sync()` now takes `research_context` dict instead of individual params
- Updated caller in `database_router.py` to use new context dict interface
- Added config constants: `MODEL_CAPABILITY`, `MODEL_MAX_TOKENS`, `MODEL_TEMPERATURE`, `DEFAULT_MAX_CHUNKS_PER_FILE`, `DEFAULT_MAX_PARALLEL_FILES`
- Added type aliases: `SynthesisContext`, `ResearchContext`
- Extracted helper functions:
  - `_build_llm_messages()` - Build message list for LLM call
  - `_parse_tool_response()` - Parse LLM tool call response
  - `_track_llm_usage()` - Track LLM usage if process monitor available
  - `_build_structured_output()` - Build structured output from results
  - `_build_status_summary()` - Build status summary string
  - `_process_documents_parallel()` - Process documents in parallel
- Removed all inline comments (14 total)
- Changed logging from f-strings to lazy % formatting
- Changed broad `Exception` catches to specific exception tuples
- Removed DEBUG logging
- Updated module docstring with all functions and classes

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #10: metadata_subagent.py ✅

**Changes Made:**
- **INTERFACE CHANGE**: `query_metadata_sync()` now takes `query_context` dict instead of individual `token`, `process_monitor`, `stage_name` params
- **INTERFACE CHANGE**: `make_metadata_decision()` now takes `decision_context` dict instead of individual params
- Updated caller in `database_router.py` to use new context dict interface
- Added config constants: `MODEL_CAPABILITY`, `MODEL_MAX_TOKENS`, `MODEL_TEMPERATURE`, `EMBEDDING_DIMENSIONS`, `DEFAULT_TOP_K`, `DEFAULT_TOP_CHUNKS_PER_DOC`
- Added type alias: `MetadataContext`
- Extracted helper functions:
  - `_parse_metadata_tool_response()` - Parse LLM tool call response for metadata decision
  - `_build_embedding_error_result()` - Build error result when embedding generation fails
  - `_build_no_documents_result()` - Build result when no documents are found
  - `_build_status_summary()` - Build status summary from decision
- Removed all inline comments (5 total: "Step 1", "Step 2", "Step 3", "Step 4", "Build status summary")
- Changed logging from f-strings to lazy % formatting
- Changed broad `Exception` catches to specific exception tuples
- Updated module docstring with all functions and classes
- Fixed SQL line length issues by breaking long lines

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #11: auth_security.py ✅

**Changes Made:**
- Added module docstring with all functions documented
- Added config constant: `REQUEST_TIMEOUT_SECONDS = 30`
- Added type alias imports: `Dict`, `Any`, `Union`
- Added module logger: `logger = logging.getLogger(__name__)`
- Fixed import order (stdlib before third-party before local)
- Added `timeout=REQUEST_TIMEOUT_SECONDS` to all `requests.get/post` calls
- Changed `logging.info/error()` to `logger.info/error()` with lazy % formatting
- Removed `elif` after `raise` (simplified to `if` statements)
- Removed `except HTTPException: raise` patterns (let exceptions propagate naturally)
- Added exception chaining with `from general_error`
- Updated all docstrings to Google-style
- Added type hints to all function signatures
- Removed inline comments (3 total)
- Fixed line length issues by shortening error messages

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

### File #12: llm.py ✅

**Changes Made:**
- Updated module docstring with proper format and function list
- Removed unused imports: `Dict`
- Removed unused config constant: `TOKEN_PREVIEW_LENGTH`
- Added type aliases: `UsageDetails`, `LLMResponse`
- Removed unnecessary `pass` statement after exception class
- Extracted helper functions:
  - `_build_usage_details()` - Build usage details dict from API response
  - `_make_embedding_call()` - Make an embedding API call
- Refactored `call_llm()` to reduce local variables (from 25 to 15):
  - Removed unused `database_name` parameter (was kept for compatibility but unused)
  - Removed unused variables: `token_preview`, `has_tools`
  - Inlined `response_time_ms`, `usage_details`, `attempt_time_secs`
- Changed `except Exception` to specific exception tuple
- Added exception chaining with `from last_exception`
- Changed logging from f-strings to lazy % formatting
- Removed all inline comments (12 total)
- Updated all docstrings to Google-style

**Linter Results:**
- Black: ✅ Passes
- Flake8: ✅ Passes
- Pylint: ✅ 10.00/10

---

## Notes

- Work through files in order listed above
- Complete all steps for one file before moving to the next
- User will review analysis before proceeding with changes
- Use ultrathink mode for thorough analysis
- Always explain defaults/fallbacks with context
- Prioritize logging cleanup and shared utils consolidation
