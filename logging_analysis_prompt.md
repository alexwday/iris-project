# IRIS Project Logging Security Analysis - Assistant Prompt

## Objective
You are helping complete a comprehensive security audit of all logging statements in the IRIS project. You need to analyze Python files one by one, looking for ALL forms of logging and assessing their security implications for an internal enterprise deployment.

## Context
- **Deployment:** Internal enterprise environment with controlled access
- **Security Focus:** Passwords, API keys, tokens, credentials, PII
- **Purpose:** Demonstrate that logging provides operational value while maintaining security
- **Access:** Only authorized developers have backend/log access

## Your Task

### 1. File Analysis Process
For each Python file in the checklist:

1. **Read the entire file** line by line carefully
2. **Look for ALL forms of logging:**
   - `import logging`
   - `logger = logging.getLogger()`
   - `logging.debug()`, `logging.info()`, `logging.warning()`, `logging.error()`, `logging.critical()`
   - `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`, `logger.critical()`, `logger.exception()`
   - `print()` statements used for output
   - Any other logging frameworks

3. **Document EVERY logging statement** with:
   - Exact line number
   - Complete logging statement text
   - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - What data is being logged
   - Purpose/reasoning for the logging

4. **Security Assessment:**
   - **SAFE:** No sensitive data, operational/debugging value
   - **RISK:** Contains passwords, full tokens, credentials, PII

5. **Operational Value:** Explain why this logging is useful

### 2. Markdown Update Format
Update the markdown checklist file by replacing the "TBD" entries for each file you complete:

**For files WITH logging:**
```markdown
#### [x] iris/src/api.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 155: `logger.error(f"Streaming error: {str(e)}")`
  - Line 170: `logger.info(f"Received chat request with {len(request.messages)} messages")`
- **Security Assessment:** SAFE - Only logs request counts and error messages, no sensitive data
- **Notes:** Essential for API monitoring and debugging. Provides operational visibility without exposing credentials.
```

**For files WITHOUT logging:**
```markdown
#### [x] iris/src/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.
```

### 3. Starting and Continuing Work

**Starting Fresh:** Begin with the first file marked `[ ]` in the checklist

**Continuing Work:** Look for the first file still marked `[ ]` with "Status: PENDING" and continue from there

### 4. Security Assessment Guidelines

**SAFE Examples:**
- Operational metrics (request counts, timing)
- Error messages without sensitive data
- System status and health checks
- Agent routing decisions
- Database operation logging (without credentials)
- Configuration verification (without secrets)
- Token previews (partial tokens for debugging)

**RISK Examples:**
- Full passwords, API keys, tokens
- Database connection strings with passwords
- Personal identifiable information
- Full credential strings

### 5. Token Previews - Special Case
For token preview logging (showing first few characters), mark as **SAFE** since:
- Only partial tokens shown (typically 4-7 characters)
- Provides debugging value for internal developers
- Full credentials are not exposed
- Internal deployment with controlled access

### 6. Progress Tracking
As you complete files, also update the Progress Summary at the top:
- Increment "Completed" count
- Update "Files with Logging" count
- Update "Total Logging Statements" count
- Note any "Security Issues" found

## Working Example

```markdown
#### [x] iris/src/api.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 25: `import logging`
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 155: `logger.error(f"Streaming error: {str(e)}", exc_info=True)`
  - Line 170: `logger.info(f"Received chat request with {len(request.messages)} messages")`
  - Line 185: `logger.debug(f"Processing {total_queries} database queries")`
- **Security Assessment:** SAFE - Only logs operational metrics, error messages, and request counts. No sensitive data exposed.
- **Notes:** Critical for API monitoring, performance tracking, and error debugging. Provides essential operational visibility for internal developers.
```

## Process Checklist
For each file you analyze:

1. ✅ Read entire file line by line
2. ✅ Found all logging statements (imports, setup, calls)
3. ✅ Documented exact line numbers and complete statements
4. ✅ Assessed security risk appropriately for internal context
5. ✅ Explained operational value
6. ✅ Updated markdown checklist
7. ✅ Changed `[ ]` to `[x]` and status to COMPLETED

## File Locations and Tools

### Files You'll Work With:
1. **Checklist:** `/Users/alexwday/Projects/iris-project/logging_analysis_checklist.md`
2. **Python Files:** All located under `/Users/alexwday/Projects/iris-project/iris/` and project root

### Tool Usage:
1. **Read the checklist:** Use `Read` tool on `logging_analysis_checklist.md`
2. **Read Python files:** Use `Read` tool on each file path (e.g., `/Users/alexwday/Projects/iris-project/iris/src/api.py`)
3. **Update checklist:** Use `Edit` tool to update the checklist file with your findings

## Step-by-Step Process

### 1. Start Your Work:
```
1. Read the checklist file: logging_analysis_checklist.md
2. Find the first file marked with [ ] and "Status: PENDING"
3. Read that Python file completely
4. Analyze all logging statements
5. Edit the checklist to update that file's entry
6. Move to the next [ ] file
```

### 2. For Each Python File:
```
1. Use Read tool: /Users/alexwday/Projects/iris-project/[file_path]
2. Look for ALL logging (imports, getLogger, log calls, print statements)
3. Document line numbers and exact statements
4. Assess security (SAFE vs RISK)
5. Note operational value
```

### 3. Update the Checklist:
```
1. Use Edit tool on logging_analysis_checklist.md
2. Change [ ] to [x]
3. Change "Status: PENDING" to "Status: COMPLETED"
4. Replace all "TBD" with your findings
5. Update Progress Summary numbers at top
```

## Current Status
- **Checklist Location:** `logging_analysis_checklist.md` 
- **Total Files:** 89 Python files
- **Your Task:** Work through each `[ ]` file systematically
- **Update Progress:** Edit the Progress Summary at top of checklist as you go

**Important:** Always read the Python file completely before updating the checklist. Use the exact file paths shown in the checklist entries.