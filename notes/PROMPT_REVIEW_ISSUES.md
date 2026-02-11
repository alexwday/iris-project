# Prompt & Registry Quality Review - Issue Tracker

Generated: 2026-02-10

## Issues

### P1: Fix "finanical" typo in internal_capm sample_questions
- **File:** `db_config/schemas/initial_data/iris_database_registry.sql`
- **Fix:** "finanical" → "financial"
- **Status:** DONE

### P2: Collapse clarifier's triple-redundant decision logic
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Merged DECISION TREE + DECISION FRAMEWORK + KEY DISTINCTION + CRITICAL DISTINCTION into single ordered DECISION FRAMEWORK with 3 steps
- **Status:** DONE

### P3: Remove hardcoded database names from direct_response
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Replaced "CAPM, PAR, APG memos, Wiki, cheatsheets; IASB, EY guidance" with references to AVAILABLE_DATABASES. Fixed 3 locations (constraints + examples 4, 6)
- **Status:** DONE

### P4: Fix extract_document_metadata NULL tool_definition
- **File:** `db_config/schemas/initial_data/doc_refresh_prompts.sql`
- **Resolution:** BY DESIGN. Code builds schema dynamically from metadata_fields.json via `_build_metadata_tool_schema()` and intentionally discards DB value. No fix needed.
- **Status:** DONE (no change needed)

### P5: Verify generate_document_fields prompt usage
- **File:** `doc_refresh/stages/stage_3_process.py`
- **Resolution:** IS an LLM call (calls `_call_llm_tracked` with MODEL_SMALL). Memory note was incorrect. Updated MEMORY.md.
- **Status:** DONE (memory corrected)

### P6+P7: Fix sample_questions count and quality
- **File:** `db_config/schemas/initial_data/iris_database_registry.sql`
- **Fix:** Added 2 questions to external_iasb (2→4). Replaced 3 shallow internal_sab_99 questions with 4 analytical ones matching the db_description depth.
- **Status:** DONE

### P8: Remove file_research mathematical precision section
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Removed MATHEMATICAL PRECISION section (research-paper-specific, irrelevant for finance Q&A). Also removed related items from MUST DO/MUST NOT.
- **Status:** DONE

### P9+P13: Standardize subagent role sections
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Restructured catalog_batch_selection, file_research, and metadata_unified_findings roles to use consistent "Your capabilities" / "Your approach" pattern matching agent prompts. Moved task steps out of role sections.
- **Status:** DONE

### P10: Fix planner example indices
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Replaced hardcoded [2], [5], [2, 5] with descriptive placeholders like "[index of the matching internal policy database]"
- **Status:** DONE

### P11: Parallelize structure_guidance prompts
- **File:** `db_config/schemas/initial_data/doc_refresh_prompts.sql`
- **Fix:** Restructured all four prompts (chapters, sections, topic_based, semantic) to use identical bullet categories: "What to look for", "Only capture", "Target section size", "Naming convention"
- **Status:** DONE

### P12: Standardize metadata_unified_findings example format
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Replaced loose "Query-Type Examples" section with numbered EXAMPLE 4 (counting query) and EXAMPLE 5 (mixed batch with all three statuses)
- **Status:** DONE

### P14: Add summarizer output example
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Fix:** Expanded EXAMPLE 1 with a partial output showing the expected format: heading, cited findings with [REF:N], closing disclaimer
- **Status:** DONE

### P15: Evaluate adding document_usage to metadata_context_fields
- **File:** `db_config/schemas/initial_data/iris_database_registry.sql`
- **Fix:** Added document_description and document_usage to metadata_context_fields across all 17 registry entries. Code already supports these fields in `_format_batch_documents()`.
- **Status:** DONE

### P16: Planner sees db_summary instead of db_description
- **File:** `services/src/utils/prompt_loader.py`, `services/src/agent/tools/database_metadata.py`
- **Issue:** `database_metadata.py:105` maps `row["db_summary"]` → key `"description"`. `prompt_loader.py:218` renders `db_info.get("description")` into `<DESCRIPTION>` XML. The planner never sees tier, usage guidance, query tips, or "when to select" — only the 1-sentence summary. The full `db_description` is stored in `db_info["db_description"]` but never rendered.
- **Fix:** Changed `prompt_loader.py:218` to use `db_info.get("db_description") or db_info.get("description", "")` — prefers full structured description, falls back to summary.
- **Status:** DONE

### P17: metadata_subagent.py SQL doesn't SELECT document_description/document_usage
- **File:** `services/src/agent/tools/metadata_subagent.py`
- **Issue:** P15 added these fields to `metadata_context_fields` config, but the actual query at `metadata_subagent.py:174` only SELECTs: id, document_name, document_summary, document_type, page_count, file_name, similarity_score, chunk_count. The `_format_batch_documents()` method checks for these fields but they're never present in the fetched data.
- **Fix:** Added `m.document_description` and `m.document_usage` to the SQL SELECT, and added both fields to the document dict construction with `or ""` fallback.
- **Status:** DONE

### P18: Router tool schema missing reasoning field
- **File:** `db_config/schemas/initial_data/iris_prompts.sql`
- **Issue:** Router prompt says "Always provide reasoning" and "Provide clear reasoning with your routing decision", but the tool schema only has `function_name` — no `reasoning` parameter. The LLM has nowhere to put its reasoning.
- **Fix:** Added required `reasoning` string field to the route_query tool schema (before `function_name`). Router.py code only reads `function_name` from the parsed dict so the extra field is safely ignored.
- **Status:** DONE

### P19: DOMAIN EXPERT tier overused (10/16 databases)
- **File:** `db_config/schemas/initial_data/iris_database_registry.sql`
- **Issue:** 10 of 16 production databases share DOMAIN EXPERT tier, providing no differentiation signal to the planner. Tier system should distinguish between core operational databases vs. narrow specialist tools.
- **Fix:** Introduced NARROW SPECIALIST tier for 6 databases with very specific scope (aio, esg, intragroup_memos, pafe, par, sab_99). Kept DOMAIN EXPERT for 4 broader operational policy databases (ext_reporting, global_finance_standards, management_reporting, process_and_controls). Each NARROW SPECIALIST description starts with "Only for..." to signal limited applicability.
- **Status:** DONE
