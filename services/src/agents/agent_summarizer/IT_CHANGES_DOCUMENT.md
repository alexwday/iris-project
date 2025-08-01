# IT Implementation Changes Document

## Overview
This document contains all the changes needed to reduce the size and visual prominence of research output in the IRIS system.

## Changes Required

### 1. File: services/src/chat_model/model.py

#### Line 1034 - Remove "Research Statement" title
- **Current:** `yield f"## Research Statement\n{research_statement}\n\n"`
- **Change to:** `yield f"{research_statement}\n\n"`

#### Line 1049 - Remove/comment out the database list line
- **Current:** `yield f"Searching the following databases: {names_str}.\n\n---\n"`
- **Change to:** Comment out or remove this entire line

#### Line 1184 - Update database status format with icon replacement
- **Current:** 
  ```python
  status_block = f"**Database:** {db_display_name}\n{status_summary}\n---\n"
  ```
- **Change to:**
  ```python
  status_summary = status_summary.replace('✅', '-').replace('📄', '-').replace('❌', '-').replace('ℹ️', '-').replace('⚠️', '-').replace('❓', '-')
  status_block = f"{db_display_name}: {status_summary}\n\n---\n"
  ```
  Note: The extra newline before `---` prevents the database name from being interpreted as a header.

#### Line 1420 - Remove bold from metadata database headers
- **Current:** `yield f"\n**{db_display_name}:**\n"`
- **Change to:** `yield f"\n{db_display_name}:\n"`

#### Line 1435 - Remove bold from document names
- **Current:** `yield f"- **{doc_name}:** {doc_desc}\n"`
- **Change to:** `yield f"- {doc_name}: {doc_desc}\n"`

### 2. File: services/src/agents/agent_summarizer/summarizer_prompt.yaml

**Replace the entire file** with the updated version: `summarizer_prompt_updated.yaml`

The key changes in this file are:
- All references to `***Document Name, Pages X-Y*** [REF:Z]` format have been changed to just `[REF:Z]`
- Instructions updated to specify REF tags only at the end of paragraphs
- Document names and page numbers can still be referenced naturally within paragraph text
- The REF tags will be converted to hyperlinks that display the document name and page number

## Summary of Changes

These changes will:
1. Remove the "Research Statement" heading to reduce redundancy
2. Remove the "Searching the following databases:" text
3. Remove all bold formatting from database names, status messages, and document names
4. Replace emoji icons (✅, 📄, ❌, etc.) with simple dashes (-)
5. Fix the markdown header interpretation issue by adding extra newlines
6. Eliminate redundant document name/page citations that appear before [REF:X] tags
7. Maintain the ability to reference documents naturally within paragraph text

## Implementation Notes

1. Ensure all changes are made exactly as specified, including the extra newline characters
2. The summarizer prompt file should be completely replaced with the updated version
3. After making changes, restart the service to ensure they take effect
4. Clear browser cache to see the updated formatting