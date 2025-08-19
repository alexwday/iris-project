# IT Implementation Guide for Semantic Search V2
**Date**: January 19, 2025  
**Author**: Alex Day

## Overview
This document outlines ALL changes needed to implement the new semantic search v2 functionality that addresses the vector similarity NULL score issue and improves reference extraction. These changes span commits from January 18-19, 2025.

## Complete List of Changes Required

### 1. Database Router Update
**File**: `services/src/agents/database_subagents/database_router.py`

**Changes (Commit `bc57fe3`)**:
- Changed import from `semantic_search.subagent` to `semantic_search_v2.subagent`
- Updated all references from "semantic_search" to "semantic_search_v2"
- Router now directs external database queries to the new v2 subagent

```python
# Line 169: Changed from
from .semantic_search.subagent import query_database_sync
# To:
from .semantic_search_v2.subagent import query_database_sync
```

### 2. New Subagent Folder (Complete Implementation)
**Location**: `services/src/agents/database_subagents/semantic_search_v2/`

This is a completely new folder that needs to be deployed. It contains:
- `__init__.py` - Module initialization (6 lines)
- `subagent.py` - Main subagent implementation (1127 lines)
- `content_synthesis_prompt.yaml` - LLM prompt configuration (122 lines)

### 3. Key Fixes Implemented in the New Subagent

#### A. NULL Vector Score Fix (Commit `0839eb8`)
The main issue was that if ANY vector in the database contains NaN or Infinity values, ALL similarity calculations return NULL.

**Solution in `subagent.py` lines 258-273**:
- Added SQL filtering to exclude invalid vectors
- Validates embeddings don't contain NaN/Infinity values
- Ensures vectors have exactly 2000 dimensions
- Uses CASE statement for safe NULL handling
- Orders results with `NULLS LAST`

```sql
CASE 
    WHEN embedding IS NULL THEN NULL
    WHEN embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' THEN NULL
    ELSE 1 - (embedding::vector <=> %s::vector)
END AS vector_score
WHERE 
    embedding IS NOT NULL
    AND NOT embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
    AND array_length(embedding::real[], 1) = 2000
```

#### B. Reference Extraction Fix (Commit `5537e85`)
The reference system was failing because the LLM couldn't properly extract filename, page numbers, and references from the unstructured context.

**Solution in `subagent.py` lines 656-781**:
- Changed from plain text to XML-like structured format
- Ensures all metadata (filename, source_filename, filepath) is available at every level
- Clear hierarchy: `<DOCUMENT> → <CHAPTER> → <SECTION> → <content>`
- Updated YAML prompt to match new structure

## Files to Deploy

1. **New folder and all contents**:
   ```
   services/src/agents/database_subagents/semantic_search_v2/
   ├── __init__.py
   ├── subagent.py
   └── content_synthesis_prompt.yaml
   ```

2. **Modified file**:
   ```
   services/src/agents/database_subagents/database_router.py  (import change only)
   ```
   
   **Note**: The planner.py changes have been reverted and are NOT needed.

## No Database Changes Required

The fixes are all in the query layer - no changes to the database structure or data are needed. The invalid vectors can optionally be cleaned up later using the provided scripts, but the new query filters handle them automatically.

## Testing

To verify the implementation:

1. Test a query that was returning NULL vector scores:
   ```python
   # Should now return valid scores (0.0 to 1.0) instead of NULL
   query = "lease accounting requirements"
   ```

2. Check that references are properly extracted with:
   - `filename`: The chapter PDF file (e.g., "03_Lease_Accounting.pdf")
   - `page_number`: The actual page in the PDF
   - `page_reference`: The display reference (e.g., "3-15")
   - `source_filename`: The original document name

## Summary

The implementation requires only TWO changes:

1. **Deploy the new `semantic_search_v2` folder** to `services/src/agents/database_subagents/`
   - Contains 3 files: `__init__.py`, `subagent.py`, `content_synthesis_prompt.yaml`

2. **Update one import in `database_router.py`** (line 169)
   - Change from: `from .semantic_search.subagent import query_database_sync`
   - Change to: `from .semantic_search_v2.subagent import query_database_sync`

**No other changes needed:**
- No planner changes required (we reverted those)
- No database structure changes needed
- No data migration required

The main improvements are:
- Fixes NULL vector scores by filtering out invalid embeddings
- Provides structured XML-like context to LLM for better reference extraction
- Ensures all necessary metadata is available for proper S3 link generation

## Evolution of the Implementation (January 18-19)

The implementation went through several iterations to fix issues:

1. **Initial implementation** (`bc57fe3`): Created basic v2 subagent
2. **Fixed config errors** (`a4886c5`, `abf8192`): Resolved naming conflicts
3. **Fixed relevance filtering** (`aa87e00`, `3ff12fd`): Made filtering less aggressive
4. **Added debugging** (`5de7e13`, `bedcc0a`, `32ec217`, `79e5eb4`, `4342877`): To diagnose NULL scores
5. **Fixed NULL vector scores** (`0839eb8`): Added SQL filtering for invalid vectors
6. **Improved context formatting** (`5537e85`): Changed to XML structure for better parsing