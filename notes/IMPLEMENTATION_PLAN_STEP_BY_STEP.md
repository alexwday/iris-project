# IRIS Enhancement Implementation Plan

Step-by-step analysis and implementation notes for the new cascading retrieval architecture.

**Last Updated:** Post-Expert Review (18 clarifying questions resolved)

---

## Overview

Moving from "each database locked to one retrieval method" to "universal cascading retrieval":
1. Every file processed for both methods:
   - Metadata + summary (for Stage 1)
   - Chunks with embeddings (for Stage 2 and top chunk in Stage 1)
2. Every query starts at Metadata Subagent (Stage 1)
3. Metadata Subagent either answers directly OR selects files for deeper research (Stage 2)
4. Stage 2 automatically chooses full-file or chunk retrieval per file based on page count

### Key Architecture Decisions (from Expert Review)

| Decision | Choice |
|----------|--------|
| Embedding strategy | Single `summary_embedding` (not dual usage/description) |
| Database routing | Universal path - all DBs use same flow (no routing type needed) |
| Parameter passing | Context dict instead of individual parameters |
| Migration strategy | Reprocess all files fresh into new tables (no data migration) |
| Parallel processing | Yes, with configurable `max_parallel_files` per DB |
| Pre-filtering | No similarity pre-filtering - process ALL files in batches |
| Observability | Build diagnostic logging from the start |

---

## Step 1: Router

### Current Behavior
- Binary decision via `route_query` tool:
  - `response_from_conversation` → direct response (greetings, follow-ups to previous research, system questions)
  - `research_from_database` → research pipeline

### Change Needed
**None.**

Router stays as-is. The "how deep should research go" decision happens at the Clarifier level, not the Router level.

### Rationale
- Router's job is simple: does this need research or not?
- Depth/scope decisions belong downstream where more context analysis happens

---

## Step 2: Clarifier

### Current Behavior
- Receives full conversation history
- Two possible actions via `make_clarifier_decision` tool:
  - `request_essential_context` → ask user for more info (numbered questions)
  - `create_research_statement` → proceed with research

- When creating research statement, sets **scope**:
  - `metadata` → user wants list/catalog of items ("find documents", "list policies")
  - `research` → user wants detailed analysis ("analyze", "explain", "what does X say")

- **Critical**: Research statement is the ONLY context passed downstream. No conversation history.

### Current Tool Output
```python
{
    "action": "create_research_statement",
    "output": "Research IFRS 16 lease classification criteria...",  # research statement
    "scope": "research"  # or "metadata"
}
```

### Proposed Changes

**Remove `scope` field entirely.** The old `metadata` vs `research` distinction (file search vs content research) is being replaced by the new cascading architecture where everything goes through the Metadata Subagent first.

**Add new flag: `require_deep_research`** (or similar name TBD)

| Flag Value | Meaning |
|------------|---------|
| `false` / not set | Default. Metadata Subagent uses judgment. |
| `true` | User explicitly requested deeper research after a metadata-level response. Don't re-answer from metadata, just select files and proceed to Stage 2. |

### New Tool Output
```python
{
    "action": "create_research_statement",
    "output": "Research IFRS 16 lease classification criteria...",
    "require_deep_research": false  # or true for follow-ups
}
```

### When Clarifier Sets `require_deep_research: true`
- Previous assistant response was a metadata-level answer (detected by reading footer text: "This response includes information from document summaries...")
- User's current message is an affirmative follow-up ("yes", "go deeper", "analyze the first two")
- When user references specific files, include file names in research statement: "Research [topic] focusing on: Policy Manual, Implementation Guide"

### How This Affects Metadata Subagent

**First pass (flag = false):**
Metadata Subagent sees metadata + summaries + top chunks and decides:
- **Database-wide query** ("how many files mention X?") → Answer directly (can't pick specific files anyway)
- **Can definitively answer from summaries** → Answer directly
- **Needs specific file content** → Select files → proceed to Stage 2

**Second pass (flag = true):**
Metadata Subagent knows user already got a summary and wants more:
- **Don't re-answer from metadata**
- Select files and proceed to Stage 2

---

## Step 3: Planner

### Current Behavior
- Receives `research_statement` from Clarifier
- Receives `available_databases` (filtered by user access)
- Receives `apg_catalog_context` (similarity search results from pre-Planner step)
- Selects 1-5 databases via `select_databases` tool
- Hardcoded max of 5 databases in tool definition

### Pre-Planner Step (Currently Exists)
Between Clarifier and Planner, there's already a similarity search:
```
search_apg_catalog_by_embedding()
    - Embeds research statement
    - Searches apg_catalog.document_usage_embedding
    - Returns top 5 docs with document_source, document_description, similarity_score
    - Passed to Planner as apg_catalog_context
```
This helps Planner know which DBs have relevant content.

### Proposed Changes

**1. Max DB selection should be configurable**
- Move from hardcoded `maxItems: 5` to env config
- Config location: environment file (not per-database)

**2. Pre-Planner similarity search updates**
- Currently searches `apg_catalog.document_usage_embedding`
- Will need to search new `iris_document_metadata` table instead (see Table Consolidation below)
- Same purpose: help Planner identify which DBs have relevant documents

### New Tool Output (unchanged structure)
```python
{
    "databases": ["internal_capm", "internal_wiki"]  # 1 to MAX_DB_SELECTION (from env)
}
```

---

## Step 4: Database Router

### Current Behavior
- Routes queries to subagents based on database type:
  - Internal DBs (`internal_*`) → `catalog_search/subagent.py`
  - External DBs (`external_*`) → `semantic_search_v2/subagent.py`
- Takes `scope` parameter ("metadata" or "research")
- Returns 6-element tuple (result, doc_ids, file_links, page_refs, section_content, reference_index)
- Parallel processing happens in `model.py` via `ThreadPoolExecutor`

### Changes Needed
- Route ALL databases to **Metadata Subagent first** (no more catalog_search vs semantic_search_v2 split)
- Replace `scope` parameter with context dict approach
- Handle two-stage flow: Metadata Subagent → (optionally) File Research Subagent
- Config-driven from `iris_database_registry` instead of hardcoded mappings
- Remove hardcoded `INTERNAL_DATABASES` and `EXTERNAL_DATABASES` dicts entirely

### Context Dict Approach (Expert Review Decision)
Instead of passing individual parameters through the call chain, use a context dict:

```python
query_context = {
    "research_statement": "Research IFRS 16 lease classification...",
    "require_deep_research": False,
    # Future fields can be added without changing signatures
}
```

### Flow
```
Clarifier outputs: {research_statement, require_deep_research}
    ↓
Build query_context dict
    ↓
Pre-Planner similarity search (context passes through)
    ↓
Planner (context passes through)
    ↓
model.py ThreadPoolExecutor - for each DB:
    ↓
    Database Router receives context
        ↓
        Metadata Subagent receives context
```

---

## Step 4a: Metadata Subagent (NEW)

### Overview
New subagent that processes each database's files in batches. Same process regardless of DB size.

### Unified Batch Process

```
For each database selected by Planner:
    ↓
Get all files for this DB from iris_document_metadata
    ↓
Split into batches of 50 (configurable in iris_database_registry)
    ↓
BATCH 1:
    Metadata Subagent receives:
        - Research statement
        - require_deep_research flag
        - Batch 1: metadata + summaries (+ top chunks per file)
        - Previous context: (none - first batch)
    Outputs:
        - metadata_findings: research/answer so far
        - selected_files: files to deep research
    ↓
BATCH 2 (if needed):
    Metadata Subagent receives:
        - Research statement
        - require_deep_research flag
        - Batch 2: metadata + summaries (+ top chunks per file)
        - Previous context: findings + selected_files from batch 1
    Outputs:
        - Updated metadata_findings
        - Updated selected_files
    ↓
... continue until all batches processed ...
    ↓
FINAL OUTPUT for this DB:
    - metadata_findings (text)
    - selected_files (list) → goes to Stage 2 if not empty
```

### Configurable Parameters (in iris_database_registry.research_config per DB)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `batch_size` | Files per batch | 50 |
| `max_selected_files` | Max files for Stage 2 | 10 |
| `max_parallel_files` | Max concurrent file research LLM calls | 5 |

**Note (Expert Review):** No similarity pre-filtering before batching. ALL files in a database are processed through batch loop. Batch size of 50 with ~500 token summaries = ~25k tokens per batch, well within 100k context limit.

### Behavior Based on Flags

| require_deep_research | Metadata Subagent Behavior |
|-----------------------|---------------------------|
| `false` | Use judgment: answer from metadata if sufficient, OR select files for Stage 2 |
| `true` | Don't answer from metadata. Select files and proceed to Stage 2. |

### Output Structure Per Batch
```python
{
    "metadata_findings": "Based on documents reviewed, [accumulated research]...",
    "selected_files": [
        {"file_id": "123", "file_name": "policy.pdf", "reason": "Contains detailed X"},
        ...
    ],
}
```

### What Metadata Subagent Sees Per File
- `document_name`
- `document_summary` (combined description/summary/usage - single field)
- `page_count`
- Top N chunks (similarity-matched to research statement) - configurable per DB via `top_chunks_in_metadata` (default: 1)

### How Top Chunks Are Fetched
- Pre-fetched before LLM call (not during)
- Single query per DB: get top chunk per file for all files in DB, using research statement embedding
- Appended to metadata for each file before passing to Metadata Subagent

### Metadata Subagent Output Outcomes (Expert Review)

Three valid outcomes - never "0 files selected but continue":

| Outcome | Description |
|---------|-------------|
| **Select files** | Files selected → proceeds to Stage 2 |
| **No content available** | Responds indicating database has nothing relevant |
| **Metadata-level answer** | Responds from summaries + footer asking if user wants deeper research |

---

## Step 5: File-Level Research (Stage 2)

### Overview
For each file selected by Metadata Subagent, perform deep research. Files processed in **parallel LLM calls**.

### Per-File Decision: Full Content vs. Chunk Search

| File Size | Method | Description |
|-----------|--------|-------------|
| ≤150 pages | **Full Content** | Load all chunks/pages, send entire file content for research |
| >150 pages | **Chunk Search** | Similarity search on chunks → top K chunks → expand sections → research |

Page threshold (150) configurable per DB via `page_threshold_for_full_content` in `research_config`.

### Full Content Mode (≤150 pages)

```
Selected file: policy_manual.pdf (45 pages)
    ↓
Load all chunks from iris_document_chunks for this file
    ↓
Reconstruct full content (ordered by chunk_number/page)
    ↓
Send to File Research Subagent
    ↓
Output: research findings with page citations
```

### Chunk Search Mode (>150 pages)

```
Selected file: comprehensive_guide.pdf (800 pages)
    ↓
Similarity search on iris_document_chunks.chunk_embedding
    WHERE document_id = this file
    ↓
Return top K chunks (configured per DB: max_chunks_per_file)
    ↓
NEW: Reranking/expansion logic for page-based chunks (TBD)
    - Will include intelligent expansion method
    - Design details to be determined during implementation
    ↓
Send processed chunks to File Research Subagent
    ↓
Output: research findings with page citations
```

**Note (Expert Review):** New chunk retrieval method to be designed. Will include reranking/expansion logic for page-based chunks. Parking detailed design for implementation phase.

### Parallel Processing (Expert Review Decision)

```
Metadata Subagent selected: [file_1, file_2, file_3]
    ↓
ThreadPoolExecutor (max_workers = research_config.max_parallel_files)
    ↓
Parallel LLM calls:
    - file_1 (30 pages) → Full Content → Research Subagent
    - file_2 (200 pages) → Chunk Search → Research Subagent
    - file_3 (80 pages) → Full Content → Research Subagent
    ↓
Collect all results (as_completed pattern)
    ↓
Pass to Summarizer
```

**Configurable per-DB:** `max_parallel_files` in `research_config` (default: 5)

### Configurable Parameters (in iris_database_registry.research_config)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `page_threshold_for_full_content` | Above this, use chunk search | 150 |
| `max_chunks_per_file` | Top K chunks in chunk search mode | 20 |
| `chunk_expansion_window` | Surrounding chunks to include for context | 2 |

### Output Structure Per File
```python
{
    "file_id": "123",
    "file_name": "policy_manual.pdf",
    "research_method": "full_content",  # or "chunk_search"
    "findings": "Based on the document, [detailed research]...",
    "citations": [
        {"ref_id": "1", "doc_name": "policy_manual.pdf", "page": 12, "content_snippet": "...relevant text..."},
        {"ref_id": "2", "doc_name": "policy_manual.pdf", "page": 45, "content_snippet": "...relevant text..."},
    ]
}
```

### Standardized Citation Format (Used Throughout System)
```python
{
    "ref_id": "1",           # Unique reference ID for this citation
    "doc_name": "file.pdf",  # Document name
    "page": 12,              # Page number (or 1 if general reference)
    "content_snippet": "..." # Optional - relevant text snippet
}
```
This format is used by:
- Metadata Subagent (page from top chunk, or page 1 for general references)
- File Research Subagent (actual pages from content)
- Summarizer (receives and formats for final output)

### Changes Needed
- Update to handle per-file parallel results
- Remove reliance on old `scope` parameter
- Handle mixed citation formats (full research vs metadata-level)

---

## Step 6: Summarizer

### Current Behavior
- Receives `aggregated_detailed_research` (dict: db_name → research text)
- Receives `scope` ("research" or "metadata")
- Receives `research_statement` and `reference_index`
- Synthesizes into structured response with `## Summary` and `## Detailed Research`
- Uses `[REF:x]` citation format with page ranges

### Changes Needed

**1. Remove `scope` parameter**
- Old `metadata` vs `research` distinction is gone
- All responses go through same summarization

**2. Handle mixed input (metadata-level + file-level research)**

New input structure:
```python
{
    "internal_capm": {
        "source": "metadata",  # answered from metadata stage
        "findings": "Based on document summaries...",
        "citations": [
            {"ref_id": "1", "doc_name": "Policy Manual", "page": 47},  # from top chunk
            {"ref_id": "2", "doc_name": "Quick Ref Guide", "page": 1},  # no specific page, use 1
        ]
    },
    "internal_par": {
        "source": "file_research",  # went to Stage 2
        "findings": "Based on detailed analysis...",
        "citations": [
            {"ref_id": "3", "doc_name": "PAR Guide", "page": 12},
            {"ref_id": "4", "doc_name": "PAR Guide", "page": 15},
            ...
        ]
    }
}
```

**3. Metadata-level citations**
- Use specific page references where content supports it (e.g., from top chunk page)
- Fallback to page 1 when referencing document generally (no specific page in metadata)
- Same `[REF:x]` format as file-level research

**4. Add footer for metadata-level responses (Expert Review Decision)**

When **ALL** databases answered from metadata level (not Stage 2), append:

> "This response includes information generated from document summaries. If you need more detailed research into specific documents, please confirm and I'll perform exhaustive analysis."

**Important:** If ANY database did file-level research, no footer is shown.

**5. Transparency (optional/TBD)**
- Could indicate which DBs used metadata vs file-level research
- Or keep invisible to user

---

## Step 7: Database Registry (Postgres)

### Current State
- Database definitions hardcoded in `AVAILABLE_DATABASES` dict
- Schema designed: `iris_database_registry` table (needs updates)
- SQL creation script exists: `testing/create_database_registry.sql`
- Population script exists: `testing/populate_database_registry.py`

### Changes Needed
- Implement repository layer
- Add per-database search configs
- Move ALL database metadata from hardcoded dict to Postgres
- **Expert Review Decision:** All fields from `AVAILABLE_DATABASES` (name, description, query_type, content_type, use_when) combined into single rich `description` text field

### Updated Schema - `iris_database_registry`

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `db_source` | VARCHAR | Database identifier (e.g., "internal_capm") |
| `display_name` | VARCHAR | User-facing name |
| `description` | TEXT | **Combined** description (includes old query_type, content_type, use_when guidance) |
| `research_config` | JSONB | Per-database configurable parameters |
| `is_active` | BOOLEAN | Enable/disable database |
| `created_at` | TIMESTAMP | Creation timestamp |

### Per-Database Config Parameters (in `research_config` JSONB)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `batch_size` | Files per batch for Metadata Subagent | 50 |
| `max_selected_files` | Max files Metadata Subagent can select for Stage 2 | 10 |
| `max_parallel_files` | Max concurrent file research LLM calls | 5 |
| `top_chunks_in_metadata` | Top chunks to include with metadata (per file) | 1 |
| `page_threshold_for_full_content` | Above this page count, use chunk search | 150 |
| `max_chunks_per_file` | Top K chunks in Stage 2 chunk search mode | 20 |

Example `research_config` JSONB:
```json
{
    "batch_size": 50,
    "max_selected_files": 10,
    "max_parallel_files": 5,
    "top_chunks_in_metadata": 1,
    "page_threshold_for_full_content": 150,
    "max_chunks_per_file": 20
}
```

**Note:** No `routing_type` needed - all databases follow universal path.

---

## Table Consolidation Plan

### Current State: 3 Tables
| Table | Purpose |
|-------|---------|
| `apg_catalog` | Document metadata (name, description, usage, embeddings) |
| `apg_content` | Document sections/chapters (section_id, section_name, section_content, page_number) |
| `iris_textbook_database` | Semantic chunks with embeddings (chunk_content, embedding, page refs) |

### Migration Strategy (Expert Review Decision)

**Reprocess everything fresh** - no data migration from old tables:
- Old tables remain (no migration of existing data)
- Create new `iris_document_metadata` + `iris_document_chunks` tables
- Reprocess ALL source files through updated pipeline into new format
- Update refresh pipeline to output to new schema

### Proposed State: 2 Tables

**Table 1: `iris_document_metadata`** (replaces `apg_catalog`)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `db_source` | VARCHAR | Which database this file belongs to |
| `document_name` | VARCHAR | Filename |
| `document_summary` | TEXT | Combined description/summary (single field) |
| `summary_embedding` | VECTOR | Embedding of summary (for similarity search) |
| `page_count` | INTEGER | Number of pages |
| `file_path` | TEXT | S3 path or file location |
| `file_name` | VARCHAR | Original filename |
| `created_at` | TIMESTAMP | Timestamp |

**Used by:**
- Pre-Planner similarity search (find relevant DBs)
- Metadata Subagent (see all files + summaries)

**Table 2: `iris_document_chunks`** (replaces `apg_content` + `iris_textbook_database`)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `document_id` | UUID | FK to iris_document_metadata |
| `db_source` | VARCHAR | Which database (denormalized for query efficiency) |
| `chunk_number` | INTEGER | Order within document |
| `chapter_section_name` | VARCHAR | Derived from MD heading |
| `chapter_section_hierarchy` | VARCHAR | Hierarchy (e.g., "1.2.3" from heading levels) |
| `chunk_content` | TEXT | Actual text content |
| `chunk_embedding` | VECTOR | Embedding for semantic search |
| `page` | INTEGER | PDF page number (for navigation) |
| `page_reference` | VARCHAR | Display page text (e.g., "3-15" for chapter 3, page 15) |
| `file_name` | VARCHAR | Filename (denormalized) |
| `created_at` | TIMESTAMP | Timestamp |

**Used by:**
- Metadata Subagent (top X chunks per file based on query similarity)
- Stage 2 semantic search (when file is too large for full retrieval)

### Key Changes (Expert Review Finalized)
1. **Page-based chunking** - each chunk = one page, hierarchy derived from MD headings
2. **Single summary embedding** - no dual usage/description embeddings
3. **Dual page references** - `page` (PDF navigation) + `page_reference` (display string)
4. **File path in BOTH tables** - `iris_document_metadata` for primary, denormalized `file_name` in chunks
5. **Single chunking strategy** - no more separate catalog vs semantic processing
6. **Embeddings on both tables** - summaries for broad search, chunks for deep search

---

## Open Questions (Expert Review Status)

### Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | New scope values? | Remove `scope`, add `require_deep_research` boolean |
| 2 | Go deeper detection? | Clarifier reads footer text from previous response |
| 3 | Footer always shown? | Only when ALL DBs answered from metadata level |
| 4 | Page threshold config? | Per-DB in `research_config.page_threshold_for_full_content` |
| 5 | Top chunks per file? | Per-DB in `research_config.top_chunks_in_metadata` (default: 1) |
| 6 | Migration strategy? | **RESOLVED**: Reprocess all files fresh into new tables |
| 7 | Flag propagation? | Context dict passed through entire chain |
| 8 | User specifies files? | File names included in research statement |
| 9 | No relevant docs? | Metadata Subagent responds explaining no relevant content |
| 10 | Multi-DB processing? | Parallel ThreadPoolExecutor, results aggregated |
| 11 | document_usage field? | Single `document_summary` field |
| 12 | Citation structure? | Standardized format with page + page_reference |
| 13 | Dual embeddings? | Single `summary_embedding` only |
| 14 | File link columns? | Added to BOTH metadata and chunks tables |
| 15 | Section metadata? | Page-based chunking with MD-derived hierarchy |
| 16 | Routing type? | Not needed - universal path for all DBs |
| 17 | AVAILABLE_DATABASES? | All fields combined into single `description` |
| 18 | Pre-filtering? | No pre-filtering - process ALL files in batches |

### Remaining Open Items

1. **Chunk retrieval method** - New reranking/expansion logic for page-based chunks (design TBD)
2. **Standardized return format** - Exact structure for unified subagent returns (see below)
3. **Diagnostic logging patterns** - Specific logging for new subagents

---

## Standardized Return Format (Expert Review Decision)

All databases now share the same flow, so one standardized return format for all subagent results.

### Format TBD - Key Requirements:
- Same structure whether metadata-level response OR file selection
- Must indicate `source` type ("metadata" or "file_research")
- Must include citations in consistent format
- Must work with existing aggregation in model.py

### Proposed Structure (to be finalized):
```python
{
    "source": "metadata" | "file_research",
    "findings": "Research text...",
    "selected_files": [...] | None,  # Only for metadata → Stage 2 handoff
    "citations": [
        {
            "ref_id": "1",
            "doc_name": "Policy Manual.pdf",
            "page": 47,           # PDF navigation
            "page_reference": "3-15",  # Display text
            "file_path": "s3://...",
            "content_snippet": "..."  # Optional
        }
    ]
}
```

---

## Files to Modify

| File | Change Type | Expert Review Notes |
|------|-------------|---------------------|
| `services/src/agents/agent_clarifier/clarifier.py` | Remove `scope`, add `require_deep_research` | ~45 lines removed, ~65 added |
| `services/src/agents/agent_clarifier/clarifier_prompt.yaml` | Update prompt for new flag logic, footer detection | Go deeper detection via footer text |
| `services/src/agents/agent_planner/planner.py` | Make max DB selection configurable, accept context dict | Minimal changes |
| `services/src/agents/database_subagents/database_router.py` | Remove hardcoded dicts, route to metadata subagent | Remove INTERNAL/EXTERNAL_DATABASES dicts |
| `services/src/agents/database_subagents/metadata_subagent/subagent.py` | **NEW FILE** | ~500-800 lines estimated |
| `services/src/agents/database_subagents/metadata_subagent/metadata_prompt.yaml` | **NEW FILE** | ~300-400 lines estimated |
| `services/src/agents/database_subagents/file_research/subagent.py` | **NEW FILE** (or adapt existing) | For Stage 2 file research |
| `services/src/agents/agent_summarizer/summarizer.py` | Add metadata response footer, handle new input format | Footer only when ALL DBs metadata |
| `services/src/agents/agent_summarizer/summarizer_prompt.yaml` | Update for new citation format | ~70 lines modified |
| `services/src/global_prompts/database_statement.py` | Use registry instead of dict | May become thin wrapper or removed |
| `services/src/chat_model/model.py` | Update queries, context dict passing, aggregation | Significant changes to call chain |
| Environment config (`.env` or similar) | Add `MAX_DB_SELECTION`, other configurable limits | |

## New Tables to Create

| Table | Purpose | Status |
|-------|---------|--------|
| `iris_database_registry` | Database config with research_config JSONB | Schema finalized |
| `iris_document_metadata` | File metadata + summaries + embeddings | Schema finalized |
| `iris_document_chunks` | Page-based chunks + embeddings | Schema finalized |

## Files to Eventually Remove (After Migration)

| File | Reason |
|------|--------|
| `services/src/agents/database_subagents/catalog_search/` | Replaced by unified metadata + file research |
| `services/src/agents/database_subagents/semantic_search_v2/` | Replaced by unified metadata + file research |

---

## Expert Review Summary

Five expert subagents reviewed this plan against actual code:

### Architecture Expert Findings
- Hardcoded routing dictionaries must be removed (INTERNAL_DATABASES, EXTERNAL_DATABASES)
- Context dict approach recommended over individual parameters
- Batch processing complexity is manageable with proper design

### Data Flow Expert Findings
- 15+ function signatures will need updates
- Scope parameter traced through 8+ functions in call chain
- Citation format needs both `page` and `page_reference` fields

### Database Schema Expert Findings
- Dual embeddings can be merged to single `summary_embedding`
- `file_path` and `file_name` columns MUST be preserved
- Section metadata derived from MD headings (page-based chunking)
- Migration strategy: reprocess fresh (no data migration)

### Prompts Expert Findings
- Metadata Subagent prompt estimated at 300-400 lines
- Batch processing is viable with 100k context (50 files × 500 tokens = 25k/batch)
- Clarifier changes: ~45 lines removed, ~65 lines added

### Subagent Integration Expert Findings
- Must preserve: parallel processing pattern (ThreadPoolExecutor)
- Must preserve: diagnostic logging for production debugging
- Gap filling/expansion logic TBD for new page-based chunking

---

## Related Documentation

- `notes/RESEARCH_DB_ENHANCEMENTS.md` - Original enhancement roadmap
- `notes/NEW_DATABASE_REGISTRY_SCHEMA.md` - Database registry schema design
- `notes/DATABASE_SCHEMAS.md` - Existing table schemas
- `notes/IRIS_Architecture_Comparison.html` - Visual before/after comparison
- `notes/IRIS_Query_Paths_Detailed.html` - Detailed flow diagrams
