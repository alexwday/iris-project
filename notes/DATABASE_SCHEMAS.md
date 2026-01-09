# IRIS Database Schemas

This document provides detailed schema information for all existing and planned tables in the IRIS system.

## Existing Tables (Production)

### `apg_catalog` - Document Catalog/Metadata

Primary table for document metadata and catalog search. Each row represents one document/file.

| Column Name | Type | Description | Notes |
|------------|------|-------------|-------|
| `id` | `SERIAL` (auto-increment integer) | Primary key | Auto-generated |
| `created_at` | `TIMESTAMP` | When the document was added | |
| `document_source` | `VARCHAR` | Database this file belongs to | Maps to database keys like `internal_par`, `external_wcm`, etc. |
| `document_type` | `VARCHAR` | Document type classifier | **Currently unused** - originally meant to separate different types within a database, but all files are treated the same |
| `document_name` | `VARCHAR` | Filename with extension | Full filename including file type |
| `document_description` | `TEXT` | GPT-generated description | AI-generated summary of document content |
| `document_usage` | `TEXT` | GPT-generated usage summary | AI-generated description of when/how to use this document |
| `document_usage_embedding` | `VECTOR(3072)` | Embedding of usage text | text-embedding-3-large, 3072 dimensions |
| `document_description_embedding` | `VECTOR(3072)` | Embedding of description text | text-embedding-3-large, 3072 dimensions |
| `file_name` | `VARCHAR` | Document name with type | Duplicate of `document_name` |
| `file_type` | `VARCHAR` | File extension | e.g., `pdf`, `xlsx`, `docx` |
| `file_size` | `BIGINT` | File size in bytes | |
| `file_path` | `TEXT` | Local NAS path | Path to file on network storage |
| `file_link` | `VARCHAR` | Filename with type | **Used for S3 link generation** - duplicate of `document_name`/`file_name` |

**Usage:**
- Catalog search uses `document_usage_embedding` and `document_description_embedding` for similarity matching
- Current implementation searches by embedding similarity, returns top-k matches
- Files are retrieved from NAS using `file_path` or S3 using `file_link`

**Notes:**
- Several fields are duplicates (`document_name`, `file_name`, `file_link`)
- `document_type` is vestigial and should be considered for removal
- Embeddings are generated during document ingestion pipeline

---

### `apg_content` - Document Sections/Chapters

Stores document content broken down by sections/chapters. Each row represents one section within a document. Multiple rows per document for multi-section files.

| Column Name | Type | Description | Notes |
|------------|------|-------------|-------|
| `id` | `SERIAL` (auto-increment integer) | Primary key | Auto-generated |
| `created_at` | `TIMESTAMP` | When the section was added | |
| `document_source` | `VARCHAR` | Database this file belongs to | Same as in `apg_catalog` |
| `document_type` | `VARCHAR` | Document type classifier | **Currently unused** - same vestigial field as in catalog |
| `document_name` | `VARCHAR` | Filename **without** extension | Note: Different from `apg_catalog` which includes extension |
| `section_id` | `INTEGER` | Section order within file | Incrementing int representing chapter/section order (1, 2, 3, ...) |
| `section_name` | `VARCHAR` | Name of the section/chapter | e.g., "Chapter 1: Introduction", "Executive Summary" |
| `section_summary` | `TEXT` | Summary of this section | AI-generated summary of the section content |
| `section_content` | `TEXT` | Actual document content | The full text content of this specific section |
| `page_number` | `INTEGER` | PDF page number | Original page number in PDF where this content was found |

**Usage:**
- Catalog subagent retrieves sections for selected documents
- Sections retrieved in order using `section_id`
- Page references maintained via `page_number` for citation
- Allows partial document retrieval (specific sections vs. entire file)

**Notes:**
- **No direct foreign key to `apg_catalog`** - joins performed on `document_source` + `document_name`
- `document_name` format differs between tables (with/without extension) - requires careful joining
- Multiple rows per document, ordered by `section_id`
- `section_summary` can be used for section-level filtering before retrieving full `section_content`
- Page numbers support PDF citation in responses

---

### `process_monitor_logs` - Pipeline Stage Monitoring

Tracks processing stages for each query/conversation run. Each row represents one stage in the agent pipeline (e.g., router, clarifier, planner, database query).

| Column Name | Type | Description | Notes |
|------------|------|-------------|-------|
| `log_id` | `SERIAL` (auto-increment integer) | Primary key | Auto-generated |
| `run_uuid` | `UUID` | Unique run identifier | Groups all stages for a single user query/conversation |
| `model_name` | `VARCHAR` | LLM model used | e.g., `gpt-4`, `gpt-3.5-turbo` |
| `stage_name` | `VARCHAR` | Pipeline stage name | e.g., `router`, `clarifier`, `planner`, `direct_response`, `database_query` |
| `stage_start_time` | `TIMESTAMP` | Stage start timestamp | When this stage began processing |
| `stage_end_time` | `TIMESTAMP` | Stage end timestamp | When this stage completed |
| `duration_ms` | `INTEGER` | Stage duration | Milliseconds taken for this stage (`stage_end_time - stage_start_time`) |
| `llm_calls` | `INTEGER` | Number of LLM calls | Count of API calls to LLM during this stage |
| `total_tokens` | `INTEGER` | Total token count | Sum of input + output tokens for this stage |
| `total_cost` | `DECIMAL` | Total cost in dollars | Calculated cost for this stage (tokens × rate) |
| `status` | `VARCHAR` | Stage completion status | e.g., `success`, `failed`, `timeout`, `skipped` |
| `decision_details` | `TEXT` | Stage decision/output | Router decision, clarifier response, planner output, etc. |
| `error_message` | `TEXT` | Error details if failed | Stack trace or error message if `status = 'failed'` |
| `log_timestamp` | `TIMESTAMP` | Log creation time | When this log entry was written to database |
| `user_id` | `VARCHAR` | User identifier | From OAuth/authentication |
| `environment` | `VARCHAR` | Deployment environment | e.g., `production`, `staging`, `dev` |
| `custom_metadata` | `JSONB` | Additional context | Flexible storage for stage-specific data |
| `notes` | `TEXT` | Additional notes | Free-form notes field |

**Usage:**
- Monitor pipeline performance stage-by-stage
- Debug failed queries by tracing stage decisions
- Cost tracking per stage and per user
- Analytics on model performance and bottlenecks
- Audit trail for user queries

**Query Patterns:**
```sql
-- Get all stages for a specific run
SELECT * FROM process_monitor_logs
WHERE run_uuid = '<uuid>'
ORDER BY stage_start_time;

-- Calculate total cost for a user
SELECT user_id, SUM(total_cost)
FROM process_monitor_logs
WHERE user_id = '<user>'
GROUP BY user_id;

-- Find slow stages
SELECT stage_name, AVG(duration_ms)
FROM process_monitor_logs
WHERE status = 'success'
GROUP BY stage_name
ORDER BY AVG(duration_ms) DESC;
```

**Notes:**
- Each run creates multiple log entries (one per stage)
- `run_uuid` groups all stages for a single user query
- Failed stages still logged with error details for debugging
- Cost tracking enables usage-based billing and budget monitoring

---

### `iris_textbook_database` - Semantic Search Chunks

**Note: This table exists in production but is NOT in local dev environment.**

Stores hierarchical document chunks for semantic search: Document → Chapters → Sections → Chunks. Each row represents one chunk (the smallest searchable unit).

| Column Name | Type | Description | Notes |
|------------|------|-------------|-------|
| `id` | `SERIAL` (auto-increment integer) | Primary key | Auto-generated |
| `document_id` | `VARCHAR` | Database identifier | Used to filter chunks by database (e.g., `internal_par`, `external_wcm`) |
| `filename` | `VARCHAR` | Processed document name | Name after processing (chapters split into separate files) |
| `filepath` | `TEXT` | Path to processed file | Path to document on NAS (post-split) |
| `source_filename` | `VARCHAR` | Original document name | Single document name before chapter splitting |
| `chapter_number` | `INTEGER` | Chapter sequence number | Chapter/section number in sequence for this file |
| `chapter_name` | `VARCHAR` | Chapter/section title | Name of the chapter |
| `chapter_summary` | `TEXT` | Chapter summary | GPT-generated summary of entire chapter |
| `chapter_page_count` | `INTEGER` | Pages in chapter | Total page count within this chapter |
| `section_number` | `INTEGER` | Section sequence number | Section number within current chapter |
| `section_summary` | `TEXT` | Section summary | GPT-generated summary of current section |
| `section_start_page` | `INTEGER` | Section start page (PDF) | Starting page number of section (PDF page number) |
| `section_end_page` | `INTEGER` | Section end page (PDF) | Ending page number of section (PDF page number) |
| `section_page_count` | `INTEGER` | Pages in section | Total page count within this section |
| `chunk_number` | `INTEGER` | Chunk sequence number | Chunk number within the current section |
| `chunk_content` | `TEXT` | Actual chunk text | The actual content text for this chunk |
| `chunk_start_page` | `INTEGER` | Chunk start page (PDF) | PDF page number where chunk starts |
| `chunk_end_page` | `INTEGER` | Chunk end page (PDF) | PDF page number where chunk ends |
| `embedding` | `VECTOR(3072)` | Chunk content embedding | text-embedding-3-large, 3072 dimensions |
| `extra1` | `TEXT` | Reserved field | **Not currently used** |
| `extra2` | `TEXT` | Reserved field | **Not currently used** |
| `extra3` | `TEXT` | Reserved field | **Not currently used** |
| `created_at` | `TIMESTAMP` | Creation timestamp | When chunk was created |
| `last_modified` | `TIMESTAMP` | Last update timestamp | When chunk was last modified |
| `section_start_reference` | `VARCHAR` | Publisher page ref (start) | Publisher-defined page reference from source text (section start) |
| `section_end_reference` | `VARCHAR` | Publisher page ref (end) | Publisher-defined page reference from source text (section end) |
| `chunk_start_reference` | `VARCHAR` | Publisher page ref (start) | Publisher-defined page reference from source text (chunk start) |
| `chunk_end_reference` | `VARCHAR` | Publisher page ref (end) | Publisher-defined page reference from source text (chunk end) |

**Hierarchical Structure:**
```
Source Document (source_filename)
  └─> Chapters (chapter_number, chapter_name, chapter_summary)
       └─> Sections (section_number, section_summary, section_start_page, section_end_page)
            └─> Chunks (chunk_number, chunk_content, chunk_start_page, chunk_end_page)
```

**Usage:**
- Semantic search uses `embedding` for vector similarity matching
- Search filters by `document_id` to limit to specific databases
- Results include full hierarchy context (chunk → section → chapter → document)
- Page references support precise citation in responses

**Page Number vs. Page Reference:**
- **PDF page numbers** (`*_page` fields): Digital PDF page numbers (includes title, TOC, etc.)
- **Publisher references** (`*_reference` fields): Page numbers printed in the source text by publisher
- Publisher references often don't align with PDF page numbers due to front matter
- Both are needed: PDF pages for extraction, publisher references for citation

**Notes:**
- Three-level hierarchy allows granular retrieval (chunk) with broader context (section, chapter)
- `filename` differs from `source_filename` due to processing that splits chapters into separate files
- `extra1`, `extra2`, `extra3` reserved for future use without schema changes
- **Missing from local dev** - semantic search functionality not available locally

---

## Planned Tables (See RESEARCH_DB_ENHANCEMENTS.md)

### `iris_database_metadata` - Database Configuration

Stores metadata and configuration for each research database (replaces hardcoded YAML).

**Purpose:** Move database definitions from code to database for easier updates.

### `iris_research_documents` - Unified Document Table

Consolidates `apg_catalog` and `apg_content` into single table with enhanced metadata.

**Purpose:**
- Reduce joins between catalog and content
- Add structured page/section information
- Support all three search modes (catalog, semantic, metadata_summary)

### `iris_semantic_search_v2` - Semantic Chunks

Chunk-level embeddings for semantic search within documents.

**Purpose:** Enable precise section-level retrieval from large documents without loading full content.

---

## Schema Evolution Notes

### Current Issues
1. **Duplicate fields** in `apg_catalog` (`document_name`, `file_name`, `file_link` all store the same value)
2. **Unused fields** like `document_type` add complexity without value
3. **Separate tables** require joins for catalog + content queries
4. **No size limits** on document content retrieval
5. **No semantic search infrastructure** (missing chunk table, pgvector not fully utilized)

### Migration Path
1. Create new consolidated tables (`iris_research_documents`, `iris_semantic_search_v2`)
2. Create views over new tables that match old schema (`apg_catalog`, `apg_content`)
3. Update subagent code to use new tables
4. Backfill data from old tables to new
5. Deprecate old tables once migration validated

See `RESEARCH_DB_ENHANCEMENTS.md` for detailed implementation plan.

---

## Related Documentation
- `LOCAL_TESTING_SETUP.md` - How to set up local PostgreSQL with these tables
- `RESEARCH_DB_ENHANCEMENTS.md` - Detailed plan for new schema and search modes
