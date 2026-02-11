# Doc Refresh - Testing Feedback Issues

Tracked issues from testing feedback (2026-02-09). Each issue includes current code behavior, analysis, and proposed fix.

---

## Issue 1: --force should clean-slate the database

**Status:** To Fix

**Question:** When using --force does it delete all existing files in the DB, and process all existing files in the input folder into a fresh DB?

**Current Behavior:** `--force` marks all source files with `action="update"` regardless of hash match (`stage_1_scan.py:220-234`). During Stage 5, each document to be inserted first has its old entry removed via `remove_document()` (`stage_5_database.py:103-105`), then the new data is inserted. Files that exist in the DB but NOT in the source folder are still detected and added to `files_to_remove`. However, if a file fails extraction/processing in stages 2-4, its old DB entry survives since removal only happens in stage 5 right before insert.

**Proposed Fix:** Add an explicit "delete all documents for these db_sources" step at the beginning of Stage 5 when `force=True`. This ensures a clean slate before inserting. Pass the `force` flag through to `stage_5_database.run_stage()`.

**Files:** `stage_5_database.py`, `main.py`

---

## Issue 2: Auto-discover database folders from BASE_PATH

**Status:** To Fix

**Question:** Instead of using DATABASE_NAMES env var, can we just set BASE_PATH and auto-discover subfolders?

**Current Behavior:** Requires both `BASE_PATH` and `DATABASE_NAMES` (comma-separated). `DATABASE_NAMES` is validated as required in `env_config.py:126`. Each subfolder in BASE_PATH is a "database" (db_source).

**Proposed Fix:** Modify `get_database_names()` to auto-discover subfolders when `DATABASE_NAMES` is not set. When `DATABASE_NAMES` is provided, use it as a filter/override. Update `validate()` to not require `DATABASE_NAMES` when `BASE_PATH` is set. Add `list_subfolders()` to FileSource.

**Files:** `env_config.py`, `file_source.py`

---

## Issue 3: Use both MODEL_SMALL and MODEL_LARGE

**Status:** To Fix

**Question:** Why only MODEL_SMALL? Should have both small and large available for different LLM calls.

**Current Behavior:** `env_config.py` defines both `MODEL_SMALL` (gpt-4.1-mini) and `MODEL_LARGE` (gpt-4.1) with separate cost configs. However, **every LLM call in `stage_3_process.py` uses `config.MODEL_SMALL`**. `MODEL_LARGE` is never referenced.

**Proposed Fix:** Update specific `_call_llm_tracked` calls to use `config.MODEL_LARGE` where quality matters. Suggested split:
- **Large model:** metadata extraction, section summary generation, document catalog generation, consolidation
- **Small model:** classification, section break detection, subsection analysis
- **Embedding model:** already separate

**Files:** `stage_3_process.py`

---

## Issue 4: Backup format clarification

**Status:** Clarification Only

**Question:** Where does backup save? Is it a zip?

**Current Behavior:** Backup saves as **CSV files** (not a zip) in a timestamped subfolder: `{BACKUP_PATH}/backup_YYYYMMDD_HHMMSS/iris_document_metadata.csv` and `iris_document_chunks.csv`. Enabled via `BACKUP_ENABLED=true`. Runs before Stage 5 (`main.py:202-209`).

**Answer:** CSV to `{BACKUP_PATH}/backup_{timestamp}/`. Not zipped. If zip is desired, that's a separate enhancement.

---

## Issue 5: Hash change handling

**Status:** Clarification Only (Working Correctly)

**Question:** When there is an existing file but the hash has changed, we process the new file AND remove the old file from the DB right?

**Current Behavior:** Yes. Stage 1 detects hash change and adds to `files_to_process` with `action="update"` (`stage_1_scan.py:243-256`). In Stage 5, before inserting each validated document, `remove_document()` is called first (`stage_5_database.py:103-105`), which deletes the old metadata row and all associated chunks (FK cascade). Then the new document is inserted.

**Answer:** Working as expected. Old data removed, new data inserted.

---

## Issue 6: DOCX page handling + PDF output folder

**Status:** To Fix (Major)

**Question:** Fix DOCX processing to respect actual page numbers. Convert all input files to PDF. Page numbers in DB must match actual document pages for UI page-linking.

**Current Behavior:** DOCX uses mammoth (HTML conversion) and creates **synthetic pages** of ~4000 chars (`content_extractor.py:220-239`). These have NO relationship to actual Word page numbers. PDF extraction correctly uses pymupdf4llm which respects real page boundaries.

**Proposed Fix:**
1. **DOCX-to-PDF conversion:** Add conversion step using `python-docx2pdf` or LibreOffice headless. This gives real page numbers matching the rendered document.
2. **Process converted PDF** through normal PDF extraction pipeline (real page numbers).
3. **PDF output folder:** Create output structure mirroring input: `{OUTPUT_PATH}/{db_source}/{relative_path}.pdf`. All files stored as PDF (DOCX converted, PDF copied). Supports downstream S3 upload + UI page linking.
4. Add `OUTPUT_PATH` env var.
5. Remove mammoth/synthetic page logic (replaced by convert-then-extract-PDF).

**Files:** `content_extractor.py`, `stage_2_extract.py`, `env_config.py`

---

## Issue 7: Remove PyMuPDF fallback

**Status:** To Fix

**Question:** Remove the pymupdf fallback. If extraction fails, we want to know so we can fix it.

**Current Behavior:** In `content_extractor.py:142-148`, if pymupdf4llm fails, it silently falls back to basic PyMuPDF text extraction (lower quality, no markdown). This masks extraction issues.

**Proposed Fix:** Remove the try/except fallback in `_extract_pdf_with_pymupdf4llm`. Remove `_extract_pdf_with_pymupdf` function entirely. Make pymupdf4llm a hard requirement. Errors propagate so they can be investigated.

**Files:** `content_extractor.py`

---

## Issue 8: Strip images during cleaning

**Status:** To Fix

**Question:** Can we strip images/image tags/base64 image data during text cleaning?

**Current Behavior:** `clean_text()` (`content_extractor.py:282-325`) does unicode normalization, control character removal, and whitespace normalization. Does NOT strip markdown images, HTML img tags, data URIs, or base64 image data. pymupdf4llm uses `write_images=False` but artifacts may remain.

**Proposed Fix:** Add image stripping patterns to `clean_text()`:
- Markdown images: `![...](...)`
- HTML img tags: `<img ...>`
- Base64 data URIs: `data:image/...`
- Long hex/base64 strings that look like embedded image data

**Files:** `content_extractor.py`

---

## Issue 9: Metadata extraction should use first 5 pages

**Status:** To Fix

**Question:** Can the metadata extraction input be the first 5 pages instead of 2?

**Current Behavior:** `extract_document_metadata()` (`stage_3_process.py:553`) uses `pages[:2]` (first 2 pages) and truncates to 3750 tokens. May miss metadata on pages 3-5 (abstracts, author affiliations, etc.).

**Proposed Fix:** Change `pages[:2]` to `pages[:5]`. Increase token limit from 3750 to ~9000.

**Files:** `stage_3_process.py`

---

## Issue 10: Purpose of abstract field

**Status:** Clarification Only

**Question:** What is the purpose of the abstract field in metadata extraction?

**Answer:** `DocumentMetadata.abstract` captures the document's own summary (author-written abstract for papers, executive summary for reports). Truncated to 500 chars (`stage_3_process.py:596`). Used in `build_document_summary()` as an "# Abstract" section (`stage_3_process.py:1291-1294`). Becomes part of the embedded document_summary for retrieval. It's the most information-dense section of many documents, useful for matching queries during retrieval.

---

## Issue 11: Customizable metadata fields

**Status:** To Fix (Major)

**Question:** Make metadata fields configurable - editable list of fields with descriptions, some optional (only extracted if found in the document).

**Current Behavior:** Fields hardcoded in `DocumentMetadata` dataclass: title, authors, publication_date, publication_venue, abstract. LLM tool call schema defined in database prompt.

**Proposed Fix:**
1. Create metadata fields config (JSON file or DB table): field_name, description, type, required (bool)
2. Dynamically build tool call function schema from config
3. Store extracted metadata as a dict instead of fixed dataclass
4. Update `build_document_summary()` to iterate over whatever fields were extracted
5. Optional fields only included if LLM finds them in content

**Files:** `stage_3_process.py`, `env_config.py` or new config, database prompts

---

## Issue 12: Classification page truncation unnecessary

**Status:** To Fix

**Question:** Do we need to truncate pages in classification? A page of content is ~500 tokens.

**Current Behavior:** `format_pages_for_prompt()` truncates each page to 2000 tokens (`stage_3_process.py:1572`). Typical pages are 300-600 tokens, so the truncation rarely activates.

**Proposed Fix:** Remove `truncate_to_tokens` call from `format_pages_for_prompt()`. If total prompt exceeds context limits, that's a different problem to solve at the batch level, not per-page.

**Files:** `stage_3_process.py`

---

## Issue 13: Section break detection page truncation risks cutting break markers

**Status:** To Fix (same fix as Issue 12)

**Question:** Truncating pages during section break detection could truncate where the breaks are, throwing off detection.

**Current Behavior:** `detect_sections_batch()` also uses `format_pages_for_prompt()` which truncates each page to 2000 tokens. Section break indicators (headings, titles) could be removed if they appear late in a dense page.

**Proposed Fix:** Same as Issue 12 - remove per-page truncation in `format_pages_for_prompt()`.

**Files:** `stage_3_process.py`

---

## Issue 14: Remove consolidation fallback, keep smart fixes

**Status:** To Fix

**Question:** Don't want a fallback that masks LLM section detection failures. OK to smartly fix minor inconsistencies.

**Current Behavior:** In `detect_structure()` lines 691-695, if `consolidate_sections_llm()` returns no sections, falls back to `consolidate_sections_simple()` (deduplicates, enforces max section size). Lines 698-707 ensure "Document Start" section at page 1.

**Proposed Fix:**
1. Remove `consolidate_sections_simple()` fallback
2. If `consolidate_sections_llm()` returns empty, raise an error (fail the document)
3. Keep the "Document Start" at page 1 insertion as a smart fix
4. Keep smart consistency fixes within consolidation: dedup exact duplicates, validate page numbers within range, sort by page number

**Files:** `stage_3_process.py`

---

## Issue 15: LLM validation clarification

**Status:** Clarification Only

**Question:** Do we use an LLM to validate how a previous LLM broke down sections?

**Answer:** Stage 4 (`stage_4_validate.py`) does **NOT** use an LLM. It's entirely programmatic: page range checks, ID uniqueness, embedding presence, field population. The `consolidate_sections_llm()` in Stage 3 is the "LLM reviewing LLM" pattern - it takes raw section breaks from batch detection and uses the LLM to merge duplicates, correct errors, and align with TOC. This is a refinement/correction step, not a separate validation pass.

---

## Issue 16: Section summary should use full content

**Status:** To Fix

**Question:** Don't truncate pages for section summaries - use the full section content.

**Current Behavior:** `generate_section_summary_json()` takes `pages[:20]` (max 20 pages) and truncates to 10,000 tokens (`stage_3_process.py:1214-1215`). Large sections lose content.

**Proposed Fix:** Remove both truncations. Use full section content. For very large sections, consider using MODEL_LARGE (from Issue 3) which has larger context. If context limits are hit, that's a signal to investigate, not silently truncate.

**Files:** `stage_3_process.py`

---

## Issue 17: Summary should indicate what's NOT covered

**Status:** To Fix

**Question:** Section summaries should tell the LLM what's not fully covered, so retrieval knows when to expand to deep research.

**Current Behavior:** Summaries include: overview, key_topics, key_metrics, key_findings, notable_facts. No indication of what's omitted.

**Proposed Fix:** Add `not_fully_covered` field to section summary JSON. The LLM identifies:
- Topics mentioned but not detailed in the summary
- Numerical data/tables not fully captured
- Complex analyses simplified in summary
- Specific sub-topics requiring full text access

Update prompt, tool schema, and `build_document_summary()` to include this field.

**Files:** `stage_3_process.py`, database prompts for `generate_section_summary_json`

---

## Issue 18: Skip subsection summaries

**Status:** To Fix

**Question:** Only need main section summaries. Skip summarizing subsections.

**Current Behavior:** `generate_enhanced_summaries()` generates summaries for BOTH primary sections AND subsections (`stage_3_process.py:1181-1197`). Extra LLM calls and cost for subsections.

**Proposed Fix:** Remove subsection summary loop (lines 1189-1197). Keep subsection detection in `analyze_subsections()` for hierarchy (title, page range). Update `build_document_summary()` to not include subsection summary content.

**Files:** `stage_3_process.py`

---

## Issue 19: Catalog entry should be richer

**Status:** To Fix

**Question:** Step 7 (catalog fields) reduces too much vs Step 6 (document summary). Want the metadata entry to look more like the document summary - metadata plus each section summary.

**Current Behavior:**
- **Step 6** (`build_document_summary`): Rich markdown with metadata, abstract, section summaries (overview, key_topics, key_metrics, key_findings, notable_facts)
- **Step 7** (`generate_document_fields`): LLM generates brief `description` (2-3 sentences) and `usage` paragraph from compressed input (section titles, unique topics, abbreviated summaries)

**Proposed Fix:** Instead of LLM re-summarization, build catalog fields directly from existing structured data:
- `document_description`: Metadata header + section overviews (from existing summaries)
- `document_usage`: Rich version with section summaries + `not_fully_covered` from Issue 17

This may make the separate LLM call unnecessary - just format the existing data.

**Files:** `stage_3_process.py`

---

## Issue 20: Remove document summary truncation for embeddings

**Status:** To Fix

**Question:** Remove 8000 token truncation for summary embeddings. If summary exceeds model limits, fix the summary, don't silently truncate.

**Current Behavior:** `generate_summary_embedding()` truncates to 8,000 tokens (`stage_3_process.py:1462`). Embedding model (text-embedding-3-large) limit is 8,191 tokens.

**Proposed Fix:** Remove silent truncation. Add warning/error if summary exceeds embedding model limit. Let the API error propagate if exceeded, consistent with "fail loud" philosophy from Issues 7 and 14.

**Files:** `stage_3_process.py`

---

## Summary

### By priority

| Priority | Issues | Description |
|----------|--------|-------------|
| Quick fixes | 7, 8, 9, 12/13, 18, 20 | Remove fallbacks/truncations, adjust inputs |
| Medium | 1, 3, 14, 16, 17 | Logic changes, new fields |
| Major | 2, 6, 11, 19 | Architecture/new features |
| Clarification only | 4, 5, 10, 15 | No code change |

### By file

| File | Issues |
|------|--------|
| `stage_3_process.py` | 3, 9, 12, 13, 14, 16, 17, 18, 19, 20 |
| `content_extractor.py` | 6, 7, 8 |
| `env_config.py` | 2, 6 |
| `stage_5_database.py` | 1 |
| `main.py` | 1 |
| `stage_2_extract.py` | 6 |
| `file_source.py` | 2 |
| Database prompts | 11, 17 |
