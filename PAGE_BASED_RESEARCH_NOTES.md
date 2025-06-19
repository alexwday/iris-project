# Page-Based Research Enhancement - Current Status & Next Steps

## Project Summary
Converting internal_capm subagent from section-based to page-based research extraction with REF numbering system for precise citations.

## Current Status ✅ MOSTLY COMPLETE

### ✅ Completed Changes
1. **Enhanced internal_capm subagent** (Commit: 85f5758, a4ddc3a, 730f8f1)
   - New `extract_page_based_research` tool schema
   - Page-sorted document reconstruction 
   - Parallel processing maintained
   - Returns structured JSON: `{doc_name: {page_x: {research_content, file_link, page_number}}}`

2. **Complete REF numbering system** (Commit: 0be8d2f, 3f64480)
   - Smart detection of new vs old reference formats in model.py
   - Automatic REF assignment: `[REF:1]`, `[REF:2]`, etc.
   - Consistent ordering: subagent → document → page
   - Master reference index for PDF href links
   - Backward compatibility with old subagents

3. **Template for other subagents** 
   - `TEMPLATE_page_based_update.py` with all code snippets needed

### 🚨 Current Issues (Need to Debug)
1. **JSON parsing error**: "unterminated string starting at" - LLM generating malformed JSON
2. **Variable scope error**: "name 'doc_research_with_refs' is not defined" 
3. **LLM returning file_link**: Should only return page_number + research_content

## File Locations
- **Enhanced subagent**: `services/src/agents/database_subagents/internal_capm/subagent.py`
- **Updated prompts**: `services/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py`
- **REF numbering**: `services/src/chat_model/model.py` (lines 853-957)
- **Template**: `services/src/agents/database_subagents/TEMPLATE_page_based_update.py`

## Key Architecture

### New Flow:
1. **internal_capm** → Returns structured research in `reference_index` position
2. **model.py** → Detects new format, assigns REF numbers, builds master index
3. **agent_summarizer** → Receives research text with `[REF:X]` tags + reference index  
4. **model.py** → Replaces `[REF:X]` with clickable PDF links

### Target JSON Structure:
```json
{
  "internal_capm": {
    "Document_Name.pdf": {
      "page_3": {
        "research_content": "Research findings from page 3",
        "file_link": "path/to/file",
        "page_number": 3
      }
    }
  }
}
```

## Debugging Added (Commit: a4ddc3a)
- Comprehensive JSON parsing error logging in `process_single_document()`
- Shows raw tool arguments and line-by-line breakdown
- Variable scope protection in model.py

## Prompt Simplifications (Commit: 730f8f1)
- Removed complex markdown formatting to prevent JSON issues
- Emphasized plain text output
- Should reduce "unterminated string" errors

## Next Steps to Debug

### 1. Check Debug Logs
When testing, look for:
```
DEBUG JSON: Raw tool arguments for {doc_name}: {...}
Failed to parse tool arguments JSON for {doc_name}: {error}
Line 0: {first line of JSON}
Line 1: {second line of JSON}
```

### 2. Common JSON Issues & Fixes
- **Unescaped quotes**: `"text with "quotes" inside"` → breaks JSON
- **Line breaks in strings**: Multi-line content breaks JSON
- **Backslashes**: `\n`, `\t` need escaping
- **Solution**: Make prompt even more explicit about plain text only

### 3. LLM File Link Issue
- **Expected**: LLM returns only `page_number` + `research_content`
- **Actual**: LLM might be returning `file_link` (shouldn't be)
- **Check**: Raw tool arguments in debug logs
- **Fix**: Make tool schema more explicit about what NOT to include

### 4. Variable Scope Issue
- **Location**: model.py lines 938+ 
- **Issue**: `structured_research_with_refs` might be empty
- **Added**: Safety check `if structured_research_with_refs:`

## Testing Strategy
1. **Test with internal_capm only** (other subagents will break temporarily)
2. **Use simple query** to minimize LLM complexity
3. **Check logs** for exact JSON malformation
4. **Verify href links** work with empty highlight_text

## After Debugging Complete
1. **Apply template** to all other internal_x subagents:
   - internal_wiki, internal_memos, internal_aio, etc.
   - Use `TEMPLATE_page_based_update.py` as guide
2. **Test full system** with multiple subagents
3. **Verify REF numbering** across all sources

## Technical Details

### Parallel Processing Confirmed ✅
```python
with ThreadPoolExecutor(max_workers=min(len(documents), 5)) as executor:
    # All relevant documents processed simultaneously
```

### Status Summary Format ✅
```python
if research_result:
    doc_count = len(research_result)
    total_pages = sum(len(doc_data) for doc_data in research_result.values())
    status_summary = f"✅ Found relevant information in {doc_count} document(s) across {total_pages} page(s)."
```

### Href Generation ✅
```javascript
javascript:window.maven.openPdf("file_link", page_number, "")
// highlight_text is empty string as requested
```

## Contact Points for Continuation
- **Main issue**: JSON parsing errors in tool calls
- **Debug logs**: Look for "DEBUG JSON" and "unterminated string" 
- **Key files**: internal_capm/subagent.py, model.py
- **Template ready**: For applying to other subagents once debugging complete

## Most Recent Commits
- `730f8f1` - Simplified prompts to prevent JSON errors
- `a4ddc3a` - Added comprehensive debugging 
- `3f64480` - Fixed variable scope error
- `0be8d2f` - Implemented REF numbering system
- `85f5758` - Enhanced internal_capm with page-based approach