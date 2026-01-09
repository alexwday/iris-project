# Staged Implementation Plan

## Executive Summary

This plan implements the IRIS enhancement roadmap from `IMPLEMENTATION_PLAN_STEP_BY_STEP.md` in discrete, testable stages. Each stage delivers working functionality and maintains system stability.

**Key Changes:**
1. Database registry in PostgreSQL (replacing hardcoded Python dicts)
2. Universal Metadata Subagent for ALL databases (unifying catalog_search + semantic_search_v2)
3. Two-stage cascading retrieval: Stage 1 (metadata/summaries) → Stage 2 (file research)
4. Standardized return formats across all subagents

**Risk Assessment:**
- **Highest Risk:** Database router refactoring (central to all queries)
- **Medium Risk:** New Metadata Subagent (new component, many edge cases)
- **Lower Risk:** Database registry (additive, can coexist with existing code)

---

## Stage Overview

| Stage | Name | Dependencies | Risk | Est. Files |
|-------|------|--------------|------|------------|
| 1 | Database Registry Foundation | None | Low | 3-4 |
| 2 | Repository Layer + Fallback | Stage 1 | Low | 2-3 |
| 3 | Context Dict Infrastructure | None | Low | 4-5 |
| 4 | Clarifier Scope Refactor | Stage 3 | Medium | 2-3 |
| 5 | New Document Tables | Stage 1 | Low | 2-3 |
| 6 | Metadata Subagent (Core) | Stages 3, 5 | High | 3-4 |
| 7 | File Research Subagent | Stage 6 | Medium | 2-3 |
| 8 | Database Router Unification | Stages 4, 6, 7 | High | 2-3 |
| 9 | Summarizer Updates | Stages 4, 8 | Medium | 2-3 |
| 10 | Cleanup + Migration | All | Low | 5+ |

**Parallelization:** Stages 1-2 and 3-4 can proceed in parallel. Stages 5 can run alongside 3-4.

---

## Stage 1: Database Registry Foundation

### Objective
Create the `iris_database_registry` PostgreSQL table and verify it's accessible from the application.

### Files to Modify/Create
- `testing/create_database_registry.sql` (update existing)
- `testing/local_data/setup_local_db.sql` (add registry table creation)

### Implementation Steps

1. **Finalize registry schema** - Update `create_database_registry.sql` to match the schema in `NEW_DATABASE_REGISTRY_SCHEMA.md`:
   ```sql
   CREATE TABLE IF NOT EXISTS iris_database_registry (
       db_source VARCHAR(100) PRIMARY KEY,
       db_name VARCHAR(255) NOT NULL,
       db_summary TEXT NOT NULL,
       db_description TEXT NOT NULL,
       research_config JSONB NOT NULL DEFAULT '{}',
       search_modes TEXT[] NOT NULL DEFAULT ARRAY['catalog', 'semantic'],
       sample_questions JSONB,
       enabled BOOLEAN NOT NULL DEFAULT true,
       ad_groups TEXT[],
       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Add indexes** for common query patterns:
   ```sql
   CREATE INDEX idx_iris_db_registry_enabled ON iris_database_registry(enabled);
   CREATE INDEX idx_iris_db_registry_ad_groups ON iris_database_registry USING GIN(ad_groups);
   ```

3. **Create data seeding script** - `testing/populate_database_registry.py` to migrate data from `AVAILABLE_DATABASES` dict to the new table.

4. **Run migration locally** - Execute SQL and Python scripts against local PostgreSQL.

### Testing Checkpoint

**Verify table creation:**
```bash
psql -h localhost -p 34532 -d maven-finance -c "\d iris_database_registry"
```
Expected: Table schema displayed with all columns.

**Verify data population:**
```bash
psql -h localhost -p 34532 -d maven-finance -c "SELECT db_source, db_name, enabled FROM iris_database_registry;"
```
Expected: 16 rows (matching `AVAILABLE_DATABASES` count).

**Existing tests must still pass:**
```bash
cd /Users/alexwday/Projects/iris-project
python testing/local_data/test_full_local.py
```
Expected: All 4 tests pass (Stage 1 is additive, no code changes).

### Acceptance Criteria
- [ ] `iris_database_registry` table exists in local PostgreSQL
- [ ] All 16 databases from `AVAILABLE_DATABASES` are populated
- [ ] `research_config` JSONB contains per-DB parameters (batch_size, max_selected_files, etc.)
- [ ] All existing integration tests pass unchanged

### Rollback Plan
```sql
DROP TABLE IF EXISTS iris_database_registry;
```
No code changes to revert - this stage is purely database.

---

## Stage 2: Repository Layer + Fallback

### Objective
Create a repository layer that reads from `iris_database_registry` with graceful fallback to the existing hardcoded dict.

### Files to Modify/Create
- **NEW:** `services/src/global_prompts/database_metadata_repo.py`
- **MODIFY:** `services/src/global_prompts/database_statement.py`

### Implementation Steps

1. **Create repository module** (`database_metadata_repo.py`):
   ```python
   class DatabaseMetadataRepository:
       def __init__(self, cache_ttl_seconds: int = 300):
           self._cache = None
           self._cache_timestamp = None
           self._cache_ttl = cache_ttl_seconds

       def get_all_databases(self, use_cache: bool = True) -> Dict[str, Any]:
           """Returns all enabled databases with full config."""
           # Try DB first, fallback to AVAILABLE_DATABASES

       def get_database_config(self, db_source: str) -> Optional[Dict[str, Any]]:
           """Returns config for a specific database."""

       def get_research_config(self, db_source: str) -> Dict[str, Any]:
           """Returns research_config JSONB for a specific database."""

       def invalidate_cache(self):
           """Force cache refresh on next query."""
   ```

2. **Implement DB query with fallback**:
   ```python
   def _fetch_from_database(self) -> Optional[Dict[str, Any]]:
       try:
           conn = connect_to_db()
           cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
           cursor.execute("""
               SELECT db_source, db_name, db_summary, db_description,
                      research_config, search_modes, sample_questions, ad_groups
               FROM iris_database_registry
               WHERE enabled = true
           """)
           # Transform rows to dict format matching AVAILABLE_DATABASES
           ...
       except Exception as e:
           logger.warning(f"DB query failed, falling back to dict: {e}")
           return None
   ```

3. **Update `get_available_databases()`** in `database_statement.py`:
   ```python
   def get_available_databases(filtered=False):
       repo = DatabaseMetadataRepository()
       databases = repo.get_all_databases()
       # ... rest of existing logic
   ```

### Testing Checkpoint

**Test 1: Repository reads from DB:**
```python
# Quick script to verify
from services.src.global_prompts.database_metadata_repo import DatabaseMetadataRepository
repo = DatabaseMetadataRepository()
dbs = repo.get_all_databases()
assert len(dbs) == 16
assert "internal_capm" in dbs
print("DB read: PASS")
```

**Test 2: Fallback works when DB unavailable:**
```python
# Stop PostgreSQL temporarily, then test
dbs = repo.get_all_databases()
assert len(dbs) == 16  # Should get from AVAILABLE_DATABASES fallback
print("Fallback: PASS")
```

**Test 3: Full integration tests:**
```bash
python testing/local_data/test_full_local.py
```
Expected: All 4 tests pass (behavior identical to before).

### Acceptance Criteria
- [ ] `DatabaseMetadataRepository` class created and functional
- [ ] `get_available_databases()` reads from DB with cache
- [ ] Fallback to `AVAILABLE_DATABASES` dict works when DB unavailable
- [ ] Cache invalidation works
- [ ] All existing tests pass

### Rollback Plan
1. Revert `database_statement.py` to previous version
2. Delete `database_metadata_repo.py`
```bash
git checkout services/src/global_prompts/database_statement.py
rm services/src/global_prompts/database_metadata_repo.py
```

---

## Stage 3: Context Dict Infrastructure

### Objective
Introduce the `query_context` dict pattern for passing parameters through the agent pipeline, replacing individual parameter threading.

### Files to Modify
- `services/src/chat_model/model.py`
- `services/src/agents/database_subagents/database_router.py`
- `services/src/agents/database_subagents/catalog_search/subagent.py`
- `services/src/agents/database_subagents/semantic_search_v2/subagent.py`

### Implementation Steps

1. **Define context dict structure**:
   ```python
   # In model.py, after clarifier returns
   query_context = {
       "research_statement": research_statement,
       "scope": scope,  # Keep for now, will be deprecated in Stage 4
       "require_deep_research": False,  # New flag, default false
       "selected_files": None,  # For Stage 2 file research
   }
   ```

2. **Update `_execute_query_worker()`** to accept context dict:
   ```python
   def _execute_query_worker(
       db_name: str,
       query_context: Dict[str, Any],  # NEW: replaces query_text, scope
       token: str,
       db_display_name: str,
       query_index: int,
       total_queries: int,
   ) -> Dict[str, Any]:
   ```

3. **Update `route_query_sync()`** signature:
   ```python
   def route_query_sync(
       database: str,
       query_context: Dict[str, Any],  # NEW: replaces query, scope
       token: Optional[str] = None,
       process_monitor=None,
       query_stage_name: Optional[str] = None,
   ) -> SubagentResult:
   ```

4. **Update subagent functions** to extract from context:
   ```python
   def query_database_sync(
       query_context: Dict[str, Any],  # NEW
       document_source: str,
       token: Optional[str] = None,
       ...
   ) -> SubagentResult:
       research_statement = query_context["research_statement"]
       scope = query_context.get("scope", "research")
       # ... rest unchanged
   ```

### Testing Checkpoint

**Test 1: Context flows through correctly:**
Add logging at each level to verify context dict is received:
```python
logger.info(f"Router received context keys: {list(query_context.keys())}")
logger.info(f"Subagent received research_statement: {query_context['research_statement'][:50]}...")
```

**Test 2: Full integration tests:**
```bash
python testing/local_data/test_full_local.py
```
Expected: All 4 tests pass (functionally identical behavior).

### Acceptance Criteria
- [ ] `query_context` dict created in `model.py` after clarifier
- [ ] Context dict passed through router to subagents
- [ ] All subagents extract parameters from context dict
- [ ] Backward compatibility maintained (scope still works)
- [ ] All existing tests pass

### Rollback Plan
```bash
git checkout services/src/chat_model/model.py
git checkout services/src/agents/database_subagents/database_router.py
git checkout services/src/agents/database_subagents/catalog_search/subagent.py
git checkout services/src/agents/database_subagents/semantic_search_v2/subagent.py
```

---

## Stage 4: Clarifier Scope Refactor

### Objective
Replace the `scope` parameter (metadata/research) with `require_deep_research` boolean. The metadata vs research distinction is replaced by the cascading architecture.

### Files to Modify
- `services/src/agents/agent_clarifier/clarifier.py`
- `services/src/agents/agent_clarifier/clarifier_prompt.yaml`
- `services/src/chat_model/model.py` (minor updates)

### Implementation Steps

1. **Update clarifier tool definition** in `clarifier.py`:
   ```python
   tools = [{
       "type": "function",
       "function": {
           "name": "make_clarifier_decision",
           "parameters": {
               "type": "object",
               "properties": {
                   "action": {
                       "type": "string",
                       "enum": ["request_essential_context", "create_research_statement"],
                   },
                   "output": {
                       "type": "string",
                       "description": "Research statement or context questions",
                   },
                   "require_deep_research": {
                       "type": "boolean",
                       "description": "True if user explicitly requested deeper analysis after a metadata-level response",
                       "default": False,
                   },
               },
               "required": ["action", "output"],
           },
       },
   }]
   ```

2. **Update clarifier prompt** (`clarifier_prompt.yaml`):
   - Remove scope determination logic
   - Add footer detection: "If the previous assistant response contains 'document summaries' and user says 'yes/go deeper/analyze', set require_deep_research: true"
   - When user references specific files, include file names in research statement

3. **Update `model.py`** to use new flag:
   ```python
   # After clarifier returns
   require_deep_research = clarifier_decision.get("require_deep_research", False)

   query_context = {
       "research_statement": research_statement,
       "require_deep_research": require_deep_research,
       # scope removed - will be determined by Metadata Subagent
   }
   ```

4. **Maintain backward compatibility** during transition:
   ```python
   # Temporary: derive scope from require_deep_research for existing subagents
   if require_deep_research:
       scope = "research"  # Force deep research
   else:
       scope = "research"  # Default to research, let new architecture decide
   ```

### Testing Checkpoint

**Test 1: Default behavior unchanged:**
```bash
python testing/local_data/test_full_local.py
```
Expected: Tests 2, 3, 4 still work (internal/external research).

**Test 2: New flag detection (manual):**
Create conversation with metadata-level response + follow-up:
```python
conversation = {
    "messages": [
        {"role": "user", "content": "What documents do we have about IFRS 16?"},
        {"role": "assistant", "content": "Based on document summaries... [footer text]"},
        {"role": "user", "content": "Yes, go deeper on the first one"},
    ]
}
# Verify clarifier sets require_deep_research: true
```

### Acceptance Criteria
- [ ] `scope` parameter removed from clarifier tool definition
- [ ] `require_deep_research` boolean added
- [ ] Clarifier detects "go deeper" follow-ups correctly
- [ ] File names included in research statement when user references them
- [ ] All existing tests pass

### Rollback Plan
```bash
git checkout services/src/agents/agent_clarifier/clarifier.py
git checkout services/src/agents/agent_clarifier/clarifier_prompt.yaml
git checkout services/src/chat_model/model.py
```

---

## Stage 5: New Document Tables

### Objective
Create the consolidated `iris_document_metadata` and `iris_document_chunks` tables that will replace the split `apg_catalog` / `apg_content` / `iris_textbook_database` tables.

### Files to Modify/Create
- **NEW:** `testing/create_unified_document_tables.sql`
- **NEW:** `testing/populate_unified_tables.py`
- **UPDATE:** `testing/local_data/setup_local_db.sql`

### Implementation Steps

1. **Create `iris_document_metadata` table**:
   ```sql
   CREATE TABLE iris_document_metadata (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       db_source VARCHAR(100) NOT NULL,
       document_name VARCHAR(500) NOT NULL,
       document_summary TEXT NOT NULL,
       summary_embedding VECTOR(2000),
       page_count INTEGER,
       file_path TEXT,
       file_name VARCHAR(500),
       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

       CONSTRAINT fk_db_source FOREIGN KEY (db_source)
           REFERENCES iris_database_registry(db_source)
   );

   CREATE INDEX idx_doc_metadata_db_source ON iris_document_metadata(db_source);
   CREATE INDEX idx_doc_metadata_embedding ON iris_document_metadata
       USING ivfflat (summary_embedding vector_cosine_ops);
   ```

2. **Create `iris_document_chunks` table**:
   ```sql
   CREATE TABLE iris_document_chunks (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       document_id UUID NOT NULL REFERENCES iris_document_metadata(id),
       db_source VARCHAR(100) NOT NULL,
       chunk_number INTEGER NOT NULL,
       chapter_section_name VARCHAR(500),
       chapter_section_hierarchy VARCHAR(100),
       chunk_content TEXT NOT NULL,
       chunk_embedding VECTOR(2000),
       page INTEGER,
       page_reference VARCHAR(50),
       file_name VARCHAR(500),
       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
   );

   CREATE INDEX idx_chunks_document_id ON iris_document_chunks(document_id);
   CREATE INDEX idx_chunks_db_source ON iris_document_chunks(db_source);
   CREATE INDEX idx_chunks_embedding ON iris_document_chunks
       USING ivfflat (chunk_embedding vector_cosine_ops);
   ```

3. **Create population script** that migrates existing sample data:
   - Read from `apg_catalog` → write to `iris_document_metadata`
   - Read from `apg_content` → write to `iris_document_chunks`
   - Read from `iris_semantic_search` → write to `iris_document_chunks` (external DBs)

4. **Run locally** and verify data integrity.

### Testing Checkpoint

**Verify table creation:**
```bash
psql -h localhost -p 34532 -d maven-finance -c "\d iris_document_metadata"
psql -h localhost -p 34532 -d maven-finance -c "\d iris_document_chunks"
```

**Verify data population:**
```bash
psql -h localhost -p 34532 -d maven-finance -c "SELECT COUNT(*) FROM iris_document_metadata;"
# Expected: 5 (matching sample internal docs)

psql -h localhost -p 34532 -d maven-finance -c "SELECT COUNT(*) FROM iris_document_chunks;"
# Expected: ~30+ (sections/chunks from sample data)
```

**Existing tests still pass** (old tables still exist):
```bash
python testing/local_data/test_full_local.py
```

### Acceptance Criteria
- [ ] `iris_document_metadata` table created with embeddings
- [ ] `iris_document_chunks` table created with embeddings
- [ ] Sample data migrated from existing tables
- [ ] Foreign key to `iris_database_registry` works
- [ ] Vector indexes created and functional
- [ ] All existing tests pass (old tables unchanged)

### Rollback Plan
```sql
DROP TABLE IF EXISTS iris_document_chunks;
DROP TABLE IF EXISTS iris_document_metadata;
```

---

## Stage 6: Metadata Subagent (Core)

### Objective
Create the new universal Metadata Subagent that processes ALL databases through a unified batch flow.

### Files to Create
- **NEW:** `services/src/agents/database_subagents/metadata_subagent/__init__.py`
- **NEW:** `services/src/agents/database_subagents/metadata_subagent/subagent.py`
- **NEW:** `services/src/agents/database_subagents/metadata_subagent/metadata_prompt.yaml`

### Implementation Steps

1. **Create directory structure:**
   ```
   services/src/agents/database_subagents/metadata_subagent/
   ├── __init__.py
   ├── subagent.py
   └── metadata_prompt.yaml
   ```

2. **Implement core batch processing logic** (`subagent.py`):
   ```python
   def query_database_sync(
       query_context: Dict[str, Any],
       db_source: str,
       token: Optional[str] = None,
       process_monitor=None,
       query_stage_name: Optional[str] = None,
   ) -> SubagentResult:
       """
       Universal Metadata Subagent - processes files in batches.

       For each batch:
       1. Load metadata + summaries + top chunk per file
       2. LLM decides: answer from metadata OR select files for Stage 2
       3. Accumulate findings across batches
       """
       research_config = get_research_config(db_source)
       batch_size = research_config.get("batch_size", 50)

       # Get all files for this database
       all_files = fetch_document_metadata(db_source)

       # Process in batches
       metadata_findings = ""
       selected_files = []

       for batch in chunk_list(all_files, batch_size):
           batch_result = process_batch(
               batch,
               query_context,
               metadata_findings,
               selected_files,
               token
           )
           metadata_findings = batch_result["findings"]
           selected_files = batch_result["selected_files"]

       # Determine outcome
       if selected_files:
           return _build_stage2_handoff(selected_files, metadata_findings)
       else:
           return _build_metadata_response(metadata_findings)
   ```

3. **Implement batch processing**:
   ```python
   def process_batch(
       batch_files: List[Dict],
       query_context: Dict[str, Any],
       previous_findings: str,
       previous_selected: List[Dict],
       token: str,
   ) -> Dict[str, Any]:
       """Process one batch of files through LLM."""

       # Fetch top chunk per file based on query similarity
       enriched_files = fetch_top_chunks_for_batch(
           batch_files,
           query_context["research_statement"]
       )

       # Build prompt with batch context
       prompt = build_batch_prompt(
           enriched_files,
           query_context,
           previous_findings,
           previous_selected
       )

       # LLM call with tool for decision
       response = call_llm_with_metadata_tool(prompt, token)

       return {
           "findings": response["metadata_findings"],
           "selected_files": response["selected_files"],
       }
   ```

4. **Create prompt YAML** (`metadata_prompt.yaml`):
   - Instructions for reviewing document summaries
   - When to answer from metadata vs select files
   - Handling `require_deep_research` flag
   - Output format specifications

5. **Define tool schema** for LLM decision:
   ```python
   METADATA_TOOL = {
       "type": "function",
       "function": {
           "name": "process_metadata_batch",
           "parameters": {
               "type": "object",
               "properties": {
                   "metadata_findings": {
                       "type": "string",
                       "description": "Research findings from metadata review"
                   },
                   "selected_files": {
                       "type": "array",
                       "items": {
                           "type": "object",
                           "properties": {
                               "file_id": {"type": "string"},
                               "file_name": {"type": "string"},
                               "reason": {"type": "string"}
                           }
                       }
                   },
                   "can_answer_from_metadata": {"type": "boolean"}
               },
               "required": ["metadata_findings", "selected_files", "can_answer_from_metadata"]
           }
       }
   }
   ```

### Testing Checkpoint

**Unit test the new subagent:**
```python
# Test script
from services.src.agents.database_subagents.metadata_subagent.subagent import query_database_sync

query_context = {
    "research_statement": "What is RBC's policy on lease classification?",
    "require_deep_research": False,
}

result = query_database_sync(query_context, "internal_capm", token="...")
print(f"Result type: {type(result[0])}")
print(f"Selected files: {len(result[5].get('selected_files', []))}")
```

**Integration test via direct call:**
```python
# Temporarily wire up metadata_subagent in router for one DB
# Verify it produces valid output format
```

### Acceptance Criteria
- [ ] Metadata Subagent processes files in configurable batches
- [ ] Top chunk per file fetched via embedding similarity
- [ ] LLM correctly decides: answer from metadata OR select files
- [ ] `require_deep_research` flag forces file selection
- [ ] Returns standardized `SubagentResult` tuple
- [ ] Handles edge cases: no relevant docs, all docs selected, empty batches

### Rollback Plan
```bash
rm -rf services/src/agents/database_subagents/metadata_subagent/
```
No other files modified yet - router still uses old subagents.

---

## Stage 7: File Research Subagent

### Objective
Create the Stage 2 File Research Subagent that performs deep analysis on selected files.

### Files to Create/Modify
- **NEW:** `services/src/agents/database_subagents/file_research/__init__.py`
- **NEW:** `services/src/agents/database_subagents/file_research/subagent.py`
- **NEW:** `services/src/agents/database_subagents/file_research/file_research_prompt.yaml`

### Implementation Steps

1. **Create directory structure:**
   ```
   services/src/agents/database_subagents/file_research/
   ├── __init__.py
   ├── subagent.py
   └── file_research_prompt.yaml
   ```

2. **Implement per-file decision logic**:
   ```python
   def research_file(
       file_info: Dict[str, Any],
       query_context: Dict[str, Any],
       research_config: Dict[str, Any],
       token: str,
   ) -> Dict[str, Any]:
       """
       Research a single file using appropriate method.

       - ≤page_threshold: Load full content
       - >page_threshold: Chunk similarity search
       """
       page_count = file_info.get("page_count", 0)
       threshold = research_config.get("page_threshold_for_full_content", 150)

       if page_count <= threshold:
           return research_full_content(file_info, query_context, token)
       else:
           return research_via_chunks(file_info, query_context, research_config, token)
   ```

3. **Implement full content mode**:
   ```python
   def research_full_content(
       file_info: Dict[str, Any],
       query_context: Dict[str, Any],
       token: str,
   ) -> Dict[str, Any]:
       """Load all chunks, send full content to LLM."""
       chunks = fetch_all_chunks_for_file(file_info["id"])
       full_content = reconstruct_content(chunks)

       response = call_llm_for_research(
           full_content,
           query_context["research_statement"],
           token
       )

       return {
           "file_id": file_info["id"],
           "file_name": file_info["file_name"],
           "research_method": "full_content",
           "findings": response["findings"],
           "citations": response["citations"],
       }
   ```

4. **Implement chunk search mode**:
   ```python
   def research_via_chunks(
       file_info: Dict[str, Any],
       query_context: Dict[str, Any],
       research_config: Dict[str, Any],
       token: str,
   ) -> Dict[str, Any]:
       """Similarity search on chunks, send top-K to LLM."""
       top_k = research_config.get("max_chunks_per_file", 20)
       expansion = research_config.get("chunk_expansion_window", 2)

       top_chunks = fetch_top_chunks_by_similarity(
           file_info["id"],
           query_context["research_statement"],
           top_k
       )

       expanded_chunks = expand_chunk_context(top_chunks, expansion)

       response = call_llm_for_research(
           format_chunks(expanded_chunks),
           query_context["research_statement"],
           token
       )

       return {
           "file_id": file_info["id"],
           "file_name": file_info["file_name"],
           "research_method": "chunk_search",
           "findings": response["findings"],
           "citations": response["citations"],
       }
   ```

5. **Implement parallel file processing**:
   ```python
   def research_selected_files(
       selected_files: List[Dict[str, Any]],
       query_context: Dict[str, Any],
       db_source: str,
       token: str,
   ) -> List[Dict[str, Any]]:
       """Process multiple files in parallel."""
       research_config = get_research_config(db_source)
       max_parallel = research_config.get("max_parallel_files", 5)

       results = []
       with ThreadPoolExecutor(max_workers=max_parallel) as executor:
           futures = {
               executor.submit(research_file, f, query_context, research_config, token): f
               for f in selected_files
           }
           for future in as_completed(futures):
               results.append(future.result())

       return results
   ```

### Testing Checkpoint

**Unit test full content mode:**
```python
# Test with small sample document
result = research_full_content(sample_file, query_context, token)
assert "findings" in result
assert "citations" in result
print("Full content mode: PASS")
```

**Unit test chunk search mode:**
```python
# Test with mocked large document
result = research_via_chunks(large_file, query_context, config, token)
assert result["research_method"] == "chunk_search"
print("Chunk search mode: PASS")
```

**Test parallel processing:**
```python
results = research_selected_files([file1, file2, file3], query_context, "internal_capm", token)
assert len(results) == 3
print("Parallel processing: PASS")
```

### Acceptance Criteria
- [ ] Full content mode works for files ≤threshold pages
- [ ] Chunk search mode works for files >threshold pages
- [ ] Parallel processing respects `max_parallel_files` config
- [ ] Citations in standardized format with page references
- [ ] Returns results compatible with summarizer expectations

### Rollback Plan
```bash
rm -rf services/src/agents/database_subagents/file_research/
```

---

## Stage 8: Database Router Unification

### Objective
Update the database router to route ALL databases through the new Metadata Subagent, replacing the split between `catalog_search` and `semantic_search_v2`.

### Files to Modify
- `services/src/agents/database_subagents/database_router.py`

### Implementation Steps

1. **Remove hardcoded database dicts**:
   ```python
   # DELETE these:
   # INTERNAL_DATABASES = {...}
   # EXTERNAL_DATABASES = {...}
   ```

2. **Update routing logic**:
   ```python
   def route_query_sync(
       database: str,
       query_context: Dict[str, Any],
       token: Optional[str] = None,
       process_monitor=None,
       query_stage_name: Optional[str] = None,
   ) -> SubagentResult:
       """
       Routes ALL database queries through the unified Metadata Subagent.
       The Metadata Subagent handles Stage 1 (metadata review) and triggers
       Stage 2 (file research) when needed.
       """
       # Get database config from registry
       repo = DatabaseMetadataRepository()
       db_config = repo.get_database_config(database)

       if not db_config:
           return _build_error_response(f"Unknown database: {database}")

       if not db_config.get("enabled", True):
           return _build_error_response(f"Database disabled: {database}")

       # Route to unified Metadata Subagent
       from .metadata_subagent.subagent import query_database_sync as metadata_query

       stage1_result = metadata_query(
           query_context=query_context,
           db_source=database,
           token=token,
           process_monitor=process_monitor,
           query_stage_name=query_stage_name,
       )

       # Check if Stage 2 is needed
       if _needs_file_research(stage1_result):
           return _execute_file_research(
               stage1_result,
               query_context,
               database,
               token,
               process_monitor,
               query_stage_name
           )

       return stage1_result
   ```

3. **Implement Stage 2 trigger**:
   ```python
   def _needs_file_research(stage1_result: SubagentResult) -> bool:
       """Check if Stage 1 selected files for deeper research."""
       reference_index = stage1_result[5]  # 6th element
       if reference_index and "selected_files" in reference_index:
           return len(reference_index["selected_files"]) > 0
       return False

   def _execute_file_research(
       stage1_result: SubagentResult,
       query_context: Dict[str, Any],
       db_source: str,
       token: str,
       process_monitor,
       query_stage_name: str,
   ) -> SubagentResult:
       """Execute Stage 2 file research on selected files."""
       from .file_research.subagent import research_selected_files

       selected_files = stage1_result[5]["selected_files"]

       file_results = research_selected_files(
           selected_files,
           query_context,
           db_source,
           token,
       )

       return _combine_stage_results(stage1_result, file_results)
   ```

### Testing Checkpoint

**Critical: Full integration tests must pass:**
```bash
python testing/local_data/test_full_local.py
```
Expected: All 4 tests pass with new routing.

**Test internal database routing:**
```python
# Verify internal_capm goes through metadata subagent
result = route_query_sync("internal_capm", query_context, token)
# Check logs for "Using metadata_subagent"
```

**Test external database routing:**
```python
# Verify external_ey goes through same flow
result = route_query_sync("external_ey", query_context, token)
# Check logs for "Using metadata_subagent"
```

**Test cascading to Stage 2:**
```python
# Use query that should trigger file research
query_context = {
    "research_statement": "Explain the detailed requirements for IFRS 16 transition",
    "require_deep_research": True,
}
result = route_query_sync("internal_capm", query_context, token)
# Verify Stage 2 was executed
```

### Acceptance Criteria
- [ ] `INTERNAL_DATABASES` and `EXTERNAL_DATABASES` dicts removed
- [ ] All databases route through Metadata Subagent
- [ ] Stage 2 file research triggers correctly
- [ ] Results combined properly for summarizer
- [ ] All existing integration tests pass
- [ ] No degradation in response quality

### Rollback Plan
```bash
git checkout services/src/agents/database_subagents/database_router.py
```
Critical stage - maintain backup and test thoroughly before committing.

---

## Stage 9: Summarizer Updates

### Objective
Update the summarizer to handle the new input format and add the metadata-level response footer.

### Files to Modify
- `services/src/agents/agent_summarizer/summarizer.py`
- `services/src/agents/agent_summarizer/summarizer_prompt.yaml`

### Implementation Steps

1. **Update input handling** in `summarizer.py`:
   ```python
   def generate_streaming_summary(
       aggregated_research: Dict[str, Dict[str, Any]],  # New structure
       token: Optional[str],
       available_databases: Dict[str, Any],
       research_statement: Optional[str] = None,
       reference_index: Optional[Dict[str, Dict[str, Any]]] = None,
   ) -> Generator[Any, None, None]:
       """
       New input structure per database:
       {
           "db_name": {
               "source": "metadata" | "file_research",
               "findings": "Research text...",
               "citations": [...]
           }
       }
       """
   ```

2. **Detect metadata-only responses**:
   ```python
   def _all_metadata_responses(aggregated_research: Dict) -> bool:
       """Check if ALL databases answered from metadata level."""
       for db_data in aggregated_research.values():
           if db_data.get("source") == "file_research":
               return False
       return True
   ```

3. **Add metadata footer** when appropriate:
   ```python
   # At end of generate_streaming_summary, before final usage_details:
   if _all_metadata_responses(aggregated_research):
       footer = (
           "\n\n---\n"
           "*This response includes information generated from document summaries. "
           "If you need more detailed research into specific documents, please confirm "
           "and I'll perform exhaustive analysis.*"
       )
       yield footer
   ```

4. **Update prompt YAML** to handle mixed citations:
   - Both metadata-level citations (page from top chunk or page 1)
   - File-research citations (actual page references)
   - Same `[REF:x]` format for both

### Testing Checkpoint

**Test metadata-only response:**
```python
# Query that can be answered from summaries
conversation = {
    "messages": [
        {"role": "user", "content": "How many documents do we have about IFRS 16?"}
    ]
}
# Verify response includes footer
```

**Test mixed response:**
```python
# Query that triggers Stage 2 for some DBs
# Verify NO footer (at least one DB did file research)
```

**Full integration tests:**
```bash
python testing/local_data/test_full_local.py
```

### Acceptance Criteria
- [ ] Summarizer handles new input structure
- [ ] Footer appears when ALL DBs answered from metadata
- [ ] Footer does NOT appear when any DB did file research
- [ ] Citations work for both metadata and file-research sources
- [ ] All existing tests pass

### Rollback Plan
```bash
git checkout services/src/agents/agent_summarizer/summarizer.py
git checkout services/src/agents/agent_summarizer/summarizer_prompt.yaml
```

---

## Stage 10: Cleanup + Migration

### Objective
Remove deprecated code, finalize migration, and ensure production readiness.

### Files to Modify/Delete
- **DELETE:** `services/src/agents/database_subagents/catalog_search/` (entire folder)
- **DELETE:** `services/src/agents/database_subagents/semantic_search_v2/` (entire folder)
- **DELETE:** `services/src/agents/database_subagents/semantic_search/` (if exists)
- **CLEANUP:** `services/src/global_prompts/database_statement.py` (remove `AVAILABLE_DATABASES` dict)
- **CLEANUP:** `services/src/chat_model/model.py` (remove backward compatibility shims)

### Implementation Steps

1. **Verify all tests pass** with new architecture before any deletions.

2. **Remove deprecated subagent folders**:
   ```bash
   rm -rf services/src/agents/database_subagents/catalog_search/
   rm -rf services/src/agents/database_subagents/semantic_search_v2/
   rm -rf services/src/agents/database_subagents/semantic_search/
   ```

3. **Remove fallback dict** from `database_statement.py`:
   - Delete `AVAILABLE_DATABASES` dict (now only in DB)
   - Remove fallback logic from repository
   - Keep `DOCUMENT_SOURCE_MAPPING` if still used

4. **Clean up `model.py`**:
   - Remove `scope` parameter handling
   - Remove backward compatibility for old tuple formats
   - Clean up any TODO comments from migration

5. **Update imports** across codebase to remove references to deleted modules.

6. **Run full test suite**:
   ```bash
   python testing/local_data/test_full_local.py
   ```

7. **Manual smoke testing**:
   - Test direct response path
   - Test internal database research
   - Test external database research
   - Test "go deeper" follow-up flow
   - Test multi-database queries

### Testing Checkpoint

**All automated tests pass:**
```bash
python testing/local_data/test_full_local.py
```

**Manual test: Complete user journey:**
1. Greeting → direct response
2. "What is IFRS 16?" → research from internal DBs
3. User asks for more detail → Stage 2 research
4. "What does EY say?" → external DB research
5. Follow-up question → uses context

### Acceptance Criteria
- [ ] All deprecated subagent folders deleted
- [ ] `AVAILABLE_DATABASES` dict removed from code
- [ ] No import errors after cleanup
- [ ] All automated tests pass
- [ ] Manual smoke tests pass
- [ ] No regression in response quality

### Rollback Plan
This stage has significant deletions. Before executing:
1. Create a git tag: `git tag pre-cleanup-migration`
2. If issues found: `git reset --hard pre-cleanup-migration`

---

## Integration Testing

After all stages complete, run comprehensive integration tests:

### Test Suite 1: Core Functionality
```bash
python testing/local_data/test_full_local.py
```
- Direct response
- Internal research
- External research
- Follow-up conversation

### Test Suite 2: New Architecture Tests
Create `testing/local_data/test_new_architecture.py`:

```python
def test_metadata_only_response():
    """Query answerable from summaries should show footer."""
    pass

def test_file_research_trigger():
    """Deep query should trigger Stage 2."""
    pass

def test_require_deep_research_flag():
    """Follow-up 'go deeper' should force file research."""
    pass

def test_database_registry_config():
    """Verify per-DB research_config is applied."""
    pass

def test_batch_processing():
    """Large DB should process in batches correctly."""
    pass

def test_parallel_file_research():
    """Multiple files researched in parallel."""
    pass
```

### Test Suite 3: Regression Tests
- Response quality comparison (before/after)
- Citation accuracy
- Response time benchmarks
- Token usage comparison

---

## Risk Mitigation

### 1. Database Connection Failures
- Repository layer has fallback to hardcoded dict
- Graceful degradation if `iris_database_registry` unavailable

### 2. LLM Response Variations
- Tool schema constrains LLM output format
- Validation on all LLM responses
- Fallback behaviors for unexpected outputs

### 3. Performance Regression
- Batch processing limits context size
- Parallel file research maintains concurrency
- Config-driven parameters allow tuning

### 4. Breaking Changes
- Each stage maintains backward compatibility
- Staged rollout allows quick reversion
- Git tags at each stage boundary

### 5. Data Migration Issues
- Old tables preserved during transition
- New tables additive (no destructive changes)
- Population scripts idempotent

---

## Post-Implementation Tasks

1. **Documentation**
   - Update `CLAUDE.md` with new architecture
   - Create operator guide for registry management
   - Document new configuration options

2. **Monitoring**
   - Add metrics for Stage 1 vs Stage 2 usage
   - Track per-DB research_config effectiveness
   - Alert on registry query failures

3. **Future Enhancements**
   - Admin UI for registry management
   - A/B testing infrastructure for config tuning
   - Automated reprocessing pipeline for new schema
