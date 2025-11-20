# IRIS database + research enhancements

Working from IT’s production-aligned drop, below is the implementation plan for moving database statements into Postgres, adding per-database research controls, introducing three search levels (catalog, semantic, metadata/summaries), and consolidating the underlying tables.

## 1) Database statements live in Postgres (not hardcoded YAML/Python)
- New table `iris_database_metadata` (one row per database):
  - `db_key` (pk), `display_name`, `description`, `content_type`, `use_when`, `ad_group`, `query_type_default`, `enabled`, `priority`, `sample_questions` (jsonb array), `search_modes_allowed` (text[]; any of `catalog`, `semantic`, `metadata_summary`), `routing_notes`.
  - Store prompt-safe strings; keep HTML/XML-free versions for prompts and UI.
- Loader:
  - Add a small repository module (e.g., `services/src/global_prompts/database_metadata_repo.py`) to read the table via `connect_to_db`, with caching and a TTL, and a “safe fallback” to the existing in-memory dict if the query fails (preserves local dev without DB).
  - `get_available_databases` in `services/src/global_prompts/database_statement.py` becomes a thin wrapper around the repo, enriching rows with AD group mapping from `Config` and the existing `questions_mapping`. It should preserve current return shape so agents stay compatible.
  - `get_database_statement` builds the XML-ish block from live rows instead of the static dict (use the same grouping rules by prefix `internal_` / `external_`).
- Data seeding/backfill:
  - One-time script to insert all current `AVAILABLE_DATABASES` rows (plus `sample_questions`) into `iris_database_metadata`.
  - Optional view `iris_database_metadata_view` to expose only prompt-safe fields for agents if IT wants stricter column permissions.

## 2) Per-database research parameters stored with the metadata
- Extend `iris_database_metadata` with a `research_config` jsonb column that holds per-database limits and preferences, e.g.:
  - `catalog`: `{max_files, max_file_size_mb, max_depth_pages, allow_full_file=true/false}`
  - `semantic`: `{top_k, max_chunks, min_similarity, expand_sections=true/false}`
  - `metadata_summary`: `{top_k, max_files, max_tokens}`
  - `defaults`: `{preferred_modes_order: ["semantic","catalog","metadata_summary"]}`
- Runtime usage:
  - `database_router.route_query_sync` pulls the `research_config` for the target db and passes the relevant portions to subagents.
  - Catalog subagent respects `max_files`, `max_file_size_mb`, `max_depth_pages` when selecting/reading documents.
  - Semantic subagent uses `top_k`/`max_chunks`/`min_similarity` to shape vector search and section expansion.
  - New metadata/summary subagent (see below) uses `metadata_summary` limits.
- Admin updates:
  - Small utility function to reload metadata into an in-process cache so changes to `research_config` take effect without restart (or low TTL cache).

## 3) Three search levels available to every database
- Search modes:
  - `catalog`: full-file retrieval with paging; ideal for small/medium files and “give me file X” use cases.
  - `semantic`: chunk/section-level vector search inside large files; ideal for precise questions.
  - `metadata_summary` (new): uses metadata + summaries across all files in a db to answer portfolio questions (“which files cover X?”, “classify all files”, “what’s in the db?”) without pulling full content.
- Routing logic:
  - Add lightweight intent classifier (can live in planner/router) that looks at user ask + explicit file requests; combine with per-db `preferred_modes_order` to pick modes.
  - Allow mixed strategies: e.g., metadata_summary to shortlist → semantic on shortlisted docs; or direct catalog when a specific file is named and within `max_file_size_mb`.
  - Add request-level overrides so callers can force a mode list (still capped by per-db limits).
- New metadata/summary subagent:
  - Lives at `services/src/agents/database_subagents/metadata_summary/subagent.py`.
  - Reads from the consolidated table (see Section 4) using precomputed `document_metadata_summary`, `document_usage`, and `metadata_embedding` to run vector/text search across all files, returning structured hits (document, why-selected, metadata highlights).
  - Provides research + status in the same tuple shape as other subagents (result, doc_ids, file_links, page_refs, section_content_map, reference_index) so router/summarizer stay unchanged.
  - Honors per-db limits (`metadata_summary.top_k`, `max_tokens`) and uses the small/large models consistent with existing subagents.
- Prompts/tools:
  - Add a concise system prompt for metadata_summary that forbids hallucinating content and requires citing file-level metadata; tooling can stay simple (no tool calls needed unless we want structured output).

## 4) Table reshape for catalog + semantic search
- Consolidate `apg_catalog` and `apg_content` into one document table, keeping a separate semantic chunk table:
  - New table `iris_research_documents` (per file):
    - `id` (uuid pk), `db_key`, `document_id` (human-friendly), `document_name`, `document_type`, `document_description`, `document_usage`, `file_link`, `file_name`, `file_size_mb`, `page_count`, `ingested_at`, `version`.
    - `full_text` (for catalog retrieval with size guard), `page_sections` (jsonb array of `{page_number, section_id, section_name, section_summary, section_content}`) for structured reconstruction.
    - `document_usage_embedding` vector (for catalog similarity), `document_metadata_summary` (short summary for metadata_summary agent), `metadata_embedding` vector.
    - Indexes: btree on `db_key`, `document_name`; gin on `page_sections`; vector indexes on embeddings.
  - Keep/refresh `iris_semantic_search` (or create `iris_semantic_search_v2`) for chunk-level semantic search:
    - `id` (pk), `db_key`, `document_id`, `document_name`, `chunk_number`, `section_path`, `chunk_text`, `page_number`, `section_number`, `embedding` vector, `metadata` jsonb, `ingested_at`.
    - Index `db_key`, (`document_id`, `chunk_number`), vector index on `embedding`.
- Backward compatibility:
  - Create views `apg_catalog` and `apg_content` over `iris_research_documents` for any legacy callers during migration.
  - Update catalog subagent fetches to read from `iris_research_documents` (or the view) with projections matching current expectations (`id`, `document_name`, `document_description`, `document_usage`, `file_link`, `file_name`).
  - Update `chat_model.search_apg_catalog_by_embedding` to point to the new table/column names.
- Ingestion/backfill:
  - Migration script to move existing `apg_catalog` + `apg_content` rows into `iris_research_documents`, populating `page_sections` and `document_metadata_summary`.
  - Rebuild embeddings (`document_usage_embedding`, `metadata_embedding`, semantic `embedding`) after migration to keep vector search accurate.

## Rollout steps
- Build migration SQL for `iris_database_metadata`, `iris_research_documents`, and (if needed) `iris_semantic_search_v2`, plus views for backward compatibility.
- Add repo/caching layer and refactor `get_available_databases`/`get_database_statement` to use Postgres with fallback.
- Thread `research_config` through `database_router` and subagents; add new `metadata_summary` subagent; add routing heuristics and per-request override handling.
- Redirect existing catalog + semantic code paths to new tables, validate limits are enforced, and keep IT’s connection/logging patterns intact.
