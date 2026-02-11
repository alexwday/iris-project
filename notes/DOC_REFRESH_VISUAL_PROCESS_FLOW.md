# Doc Refresh Pipeline - Visual Process Flow

> **Audience:** Developer familiar with document processing and RAG concepts who needs exact
> parameter-level detail of THIS pipeline.
>
> **Source of truth:** This document describes the code as of 2026-02-09.

---

## Pipeline Overview

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT REFRESH PIPELINE                                  │
│                                                                                    │
│  python -m doc_refresh.main [--dry-run] [--force] [--log-level DEBUG]              │
│                                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────┐ │
│  │ Stage 1  │──▶│ Stage 2  │──▶│ Stage 3  │──▶│ Stage 4  │──▶│ Stage 5  │──▶│ Stage 6   │ │
│  │  SCAN    │   │ EXTRACT  │   │ PROCESS  │   │ VALIDATE │   │ DATABASE │   │  REPORT   │ │
│  │          │   │          │   │          │   │          │   │          │   │           │ │
│  │ Compare  │   │ PDF/DOCX │   │ LLM-based│   │ Data     │   │ Remove + │   │ Console + │ │
│  │ hashes   │   │ to pages │   │ structur-│   │ integrity│   │ Insert   │   │ JSON log  │ │
│  │ vs DB    │   │          │   │ ing      │   │ checks   │   │ (atomic) │   │           │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └───────────┘ │
│       │              │              │              │              │              │         │
│  files_to_     extracted_     processed_     validated_     database_      report_        │
│  process[]     documents[]    documents[]    documents[]    result         result         │
│  files_to_     failed_        failed_        failed_                                      │
│  remove[]      documents[]    documents[]    documents[]                                  │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### CLI Arguments

| Argument      | Default               | Effect                                          |
|---------------|-----------------------|-------------------------------------------------|
| `--dry-run`   | `REFRESH_DRY_RUN`     | Skip database writes; Stage 4 uses non-strict   |
| `--force`     | `REFRESH_FORCE`       | Ignore hash matches, reprocess all files         |
| `--log-level` | `IRIS_LOG_LEVEL`/INFO | DEBUG, INFO, WARNING, ERROR                      |
| `--output`    | `REFRESH_LOG_PATH`    | Path for JSON report file                        |

### Key Environment Variables

| Variable              | Purpose                                              | Example                |
|-----------------------|------------------------------------------------------|------------------------|
| `BASE_PATH`           | Root folder containing db_source subfolders           | `/data/iris_documents` |
| `DATABASE_NAMES`      | Comma-separated folder names to process               | `internal_capm,external_iasb` |
| `FILE_SOURCE_MODE`    | `local` or `nas`                                      | `local`                |
| `OPENAI_API_KEY`      | OpenAI API key (local dev)                            | `sk-...`               |
| `AZURE_BASE_URL`      | Azure OpenAI endpoint (RBC environment)               | `https://...`          |
| `IRIS_MODEL_SMALL`    | Model for all Stage 3 LLM calls                       | `gpt-4.1-mini`         |
| `IRIS_MODEL_EMBEDDING`| Model for all embedding calls                          | `text-embedding-3-large` |
| `VECTOR_POSTGRES_*`   | DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD   | --                     |
| `BACKUP_ENABLED`      | Run backup before Stage 5 writes                       | `true`                 |

### Reprocessing Logic

```
For each file in source folder:
    ┌─────────────────────────┐
    │ Is file in database?    │
    └────┬──────────┬─────────┘
         │ NO       │ YES
         ▼          ▼
    ┌─────────┐  ┌──────────────────┐
    │ NEW     │  │ --force flag set? │
    │ Process │  └──┬───────┬───────┘
    └─────────┘     │ YES   │ NO
                    ▼       ▼
               ┌─────────┐  ┌───────────────────┐
               │ UPDATE  │  │ Hash matches DB?   │
               │ Process │  └──┬──────────┬──────┘
               └─────────┘     │ YES      │ NO
                               ▼          ▼
                          ┌──────────┐ ┌─────────┐
                          │UNCHANGED │ │ UPDATE  │
                          │ Skip     │ │ Process │
                          └──────────┘ └─────────┘

For each file in database NOT in source folder:
    ┌──────────┐
    │ REMOVED  │
    │ Delete   │
    └──────────┘
```

---

## Stage 1: Scan

**Module:** `doc_refresh/stages/stage_1_scan.py`

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────┐
│ INPUT                │          │ OUTPUT: ScanResult            │
│                      │          │                               │
│ FileSource           │          │ files_to_process: [FileInfo]  │
│ (local or NAS)       │────────▶ │ files_to_remove:  [dict]      │
│                      │          │ files_unchanged:  int         │
│ Database names[]     │          │ scan_errors:      [str]       │
│ Force flag           │          │ databases_scanned:[str]       │
└──────────────────────┘          └──────────────────────────────┘
```

### Step-by-Step Flow

```
┌───────────────────────────────────────┐
│ 1. Get database names from            │
│    DATABASE_NAMES env var             │
│    (comma-separated)                  │
└──────────────────┬────────────────────┘
                   │
                   ▼ [N database folders]
┌───────────────────────────────────────┐
│ 2. For each db_name folder:           │
│    list_files(db_name,                │
│      extensions=[".pdf", ".docx"])     │
│    Uses rglob("*") for recursive scan │
└──────────────────┬────────────────────┘
                   │
                   ▼ [M files found]
┌───────────────────────────────────────┐
│ 3. Query existing DB files:           │
│    SELECT id, file_path,              │
│           document_name, file_hash    │
│    FROM iris_document_metadata        │
│    WHERE db_source = :db_source       │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│ 4. For each source file:              │
│    - Compute SHA-256 hash             │
│      (reads file in 8192-byte chunks) │
│    - Compare with DB hash             │
│    - Categorize as new/update/skip    │
│                                       │
│ 5. For each DB file NOT in source:    │
│    - Mark for removal                 │
└───────────────────────────────────────┘
```

### File Discovery

| Parameter           | Value           | Source                   |
|---------------------|-----------------|--------------------------|
| Extensions          | `.pdf`, `.docx` | `SUPPORTED_EXTENSIONS`   |
| Recursion           | Yes             | `rglob("*")`            |
| Hash algorithm      | SHA-256         | `hashlib.sha256()`      |
| Hash chunk size     | 8192 bytes      | Hardcoded                |

### FileInfo Dataclass

| Field          | Type   | Description                          |
|----------------|--------|--------------------------------------|
| file_path      | str    | Absolute path to file                |
| relative_path  | str    | Path relative to db_source folder    |
| file_name      | str    | Filename only                        |
| file_hash      | str    | SHA-256 hex digest                   |
| file_size      | int    | File size in bytes                   |
| db_source      | str    | Database source identifier (folder)  |
| modified_time  | float  | OS-reported modification timestamp   |
| action         | str    | "new" or "update"                    |

### Concrete Example

```
Source folder: BASE_PATH/internal_capm/
├── CAPM_Policy_Manual.pdf       (SHA: abc123...)   ← In DB, hash matches → UNCHANGED
├── CAPM_Revenue_Policy.pdf      (SHA: def456...)   ← In DB, hash differs → UPDATE
├── CAPM_Lease_Guidance.pdf      (SHA: ghi789...)   ← Not in DB           → NEW
├── CAPM_FX_Policy.pdf           (SHA: jkl012...)   ← In DB, hash matches → UNCHANGED
└── (DB has "CAPM_Old_Memo.pdf")                    ← Not in source       → REMOVED

Result:
  files_to_process = 2 (Revenue=update, Lease=new)
  files_to_remove  = 1 (Old_Memo)
  files_unchanged  = 2 (Policy_Manual, FX_Policy)
```

### Error Handling

- Individual file scan errors are captured in `scan_errors[]` and logged; pipeline continues
- If the entire database folder fails, error is appended and other folders still process
- If no DATABASE_NAMES configured, raises `ValueError` and pipeline exits

---

## Stage 2: Extract

**Module:** `doc_refresh/stages/stage_2_extract.py`

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────┐
│ INPUT                │          │ OUTPUT: ExtractionResult      │
│                      │          │                               │
│ files_to_process:    │          │ extracted_documents:           │
│   [FileInfo]         │────────▶ │   [ExtractedDocument]         │
│                      │          │ failed_documents:              │
│ FileSource           │          │   [ExtractedDocument]         │
│                      │          │ total_pages: int              │
└──────────────────────┘          └──────────────────────────────┘
```

### ExtractedDocument Dataclass

| Field             | Type         | Description                      |
|-------------------|--------------|----------------------------------|
| file_info         | FileInfo     | From Stage 1                     |
| pages             | List[str]    | One string per page              |
| page_count        | int          | len(pages)                       |
| extraction_error  | Optional str | Error message if failed          |

### Extraction Chain

```
┌────────────────────┐
│ Determine file type│
│ by extension       │
└───┬────────┬───────┘
    │ .pdf   │ .docx
    ▼        ▼
┌────────┐  ┌──────────────────────────────────┐
│  PDF   │  │  DOCX                             │
│ Chain  │  │  mammoth → HTML → _html_to_text   │
└───┬────┘  │  → clean_text                     │
    │       │  → _split_into_synthetic_pages     │
    ▼       └──────────────────────────────────┘
┌──────────────────────────────────────┐
│ pymupdf4llm.to_markdown(            │
│   page_chunks=True,                 │
│   write_images=False,               │
│   show_progress=False               │
│ )                                   │
│ → List of {text: "..."} per page    │
│ → clean_text() each page            │
└─────────────┬────────────────────────┘
              │ ✗ If pymupdf4llm fails
              ▼
┌──────────────────────────────────────┐
│ FALLBACK: pymupdf.open()            │
│ → page.get_text() per page          │
│ → clean_text() each page            │
└──────────────────────────────────────┘
```

### clean_text() Pipeline

Applied to every page of text in sequence:

```
Raw text
  │
  ▼ 1. Unicode normalize (NFKC)
  │    unicodedata.normalize("NFKC", text)
  │
  ▼ 2. Remove control characters (keep \n \t)
  │    Strip chars where category starts with "C"
  │
  ▼ 3. Normalize line endings
  │    \r\n → \n, \r → \n
  │
  ▼ 4. Collapse horizontal whitespace
  │    re.sub(r"[^\S\n]+", " ", text)
  │
  ▼ 5. Collapse blank lines (max 2 newlines)
  │    re.sub(r"\n{3,}", "\n\n", text)
  │
  ▼ 6. Strip each line
  │    line.strip() for each line
  │
  ▼ 7. Strip overall
     text.strip()
```

### DOCX Synthetic Page Splitting

DOCX files have no native page breaks. Content is split into synthetic pages:

| Parameter            | Value  | Constant             |
|----------------------|--------|----------------------|
| SYNTHETIC_PAGE_SIZE  | 4000   | Characters per page  |

**Break priority** (searched backwards within 500 chars of target):

| Priority | Separator | Description             |
|----------|-----------|-------------------------|
| 1        | `\n\n`    | Double newline (para)   |
| 2        | `\n`      | Single newline          |
| 3        | `". "`    | Sentence end            |
| 4        | `" "`     | Word boundary           |
| fallback | --        | Hard cut at target pos  |

### Concrete Example: PDF

```
Input: "IFRS_16_Leases.pdf" (150 physical pages)
  ▼ pymupdf4llm.to_markdown(page_chunks=True)
  ▼ 150 page dicts returned
  ▼ clean_text() applied to each
Output: ExtractedDocument.pages = [page1_text, page2_text, ... page150_text]
         ExtractedDocument.page_count = 150
```

### Concrete Example: DOCX

```
Input: "APG_Memo_Revenue.docx" (15,000 chars after HTML → text)
  ▼ mammoth.convert_to_html()
  ▼ _html_to_text() (strip tags, decode entities)
  ▼ clean_text()
  ▼ _split_into_synthetic_pages(text, SYNTHETIC_PAGE_SIZE=4000)
  ▼ 15000 / 4000 ≈ 4 synthetic pages
Output: ExtractedDocument.pages = [page1, page2, page3, page4]
         ExtractedDocument.page_count = 4
```

### NAS Mode

When `FILE_SOURCE_MODE=nas`:
1. File is downloaded from NAS via SMB to a temporary directory
2. Extraction runs on the local temp copy
3. Temp file is deleted after extraction

### Error Handling

- Per-file errors are caught; failed files go to `failed_documents[]`
- Pipeline continues processing remaining files
- Both the error and the FileInfo are preserved for reporting

---

## Stage 3: Process

**Module:** `doc_refresh/stages/stage_3_process.py`

This is the most complex stage. It transforms extracted pages into structured hierarchical data with embeddings.

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────────┐
│ INPUT                │          │ OUTPUT: ProcessingResult          │
│                      │          │                                   │
│ extracted_documents: │          │ processed_documents:              │
│   [ExtractedDocument]│────────▶ │   [ProcessedDocument]             │
│                      │          │ failed_documents:                 │
│                      │          │   [ProcessedDocument]             │
│                      │          │ total_sections / subsections /    │
│                      │          │   chunks / llm_calls / cost       │
└──────────────────────┘          └──────────────────────────────────┘
```

### Processing Constants

| Constant              | Value | Purpose                                        |
|-----------------------|-------|------------------------------------------------|
| CLASSIFICATION_PAGES  | 100   | Max pages sent to classification LLM           |
| BATCH_SIZE            | 50    | Pages per batch for section detection           |
| MAX_SECTION_PAGES     | 100   | Max pages before forced section split           |
| EMBEDDING_BATCH_SIZE  | 100   | Chunks per embedding API call                   |

### Per-Document Processing Pipeline

```
ExtractedDocument (pages[])
  │
  ▼ Step 1: Extract Document Metadata
  │
  ▼ Step 2: Detect Document Structure
  │           (classify → detect batches → consolidate)
  │
  ▼ Step 3: Build Primary Sections
  │
  ▼ Step 4: Analyze Subsections
  │
  ▼ Step 5: Generate Enhanced Summaries
  │
  ▼ Step 6: Build Document Summary (markdown assembly)
  │
  ▼ Step 7: Generate Document Description & Usage
  │
  ▼ Step 8: Generate Summary Embedding
  │
  ▼ Step 9: Generate Chunks
  │
  ▼ Step 10: Generate Chunk Embeddings
  │
  ▼ ProcessedDocument
```

---

### Step 1: Extract Document Metadata

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT: pages[:2] (first 2 pages)                             │
│                                                              │
│ ⚠ TRUNCATION: truncate_to_tokens(first_pages, 3750)         │
│   Pages joined with "\n\n---PAGE BREAK---\n\n"              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: extract_document_metadata                         ║
║                                                             ║
║ Prompt:  stage_3 / extract_document_metadata                ║
║ Model:   config.MODEL_SMALL (default: gpt-4.1-mini)        ║
║ Temp:    0.1                                                ║
║ Tool:    extract_metadata                                   ║
║ Returns: {title, authors[], publication_date,               ║
║           publication_venue, abstract}                      ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ OUTPUT: DocumentMetadata                                     │
│   title: str                                                 │
│   authors: List[str]                                         │
│   publication_date: str                                      │
│   publication_venue: str                                     │
│   abstract: str (⚠ truncated to 500 chars)                   │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 2: Detect Document Structure

Three phases:

#### Phase 1: Classification

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT: pages[:CLASSIFICATION_PAGES]  (first 100 pages)       │
│                                                              │
│ ⚠ TRUNCATION: Each page truncated to 2000 tokens            │
│   via format_pages_for_prompt()                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: classify_document                                  ║
║                                                             ║
║ Prompt:  stage_3 / classify_document                        ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.1                                                ║
║ Tool:    classify_document_structure                         ║
║ Returns: {structure_type, confidence, has_toc, toc_sections}║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ structure_type: one of:                                      │
│   "chapters" | "sections" | "topic_based" | "semantic"       │
│                                                              │
│ confidence: "high" | "medium" | "low"                        │
│ has_toc: bool                                                │
│ toc_sections: List[str]  (titles from table of contents)     │
│                                                              │
│ Invalid structure_type falls back to "semantic"               │
└──────────────────────────────────────────────────────────────┘
```

#### Phase 2: Section Break Detection (Batched)

```
For each batch of BATCH_SIZE (50) pages:
┌──────────────────────────────────────────────────────────────┐
│ Batch N: pages[start_idx : end_idx]                          │
│                                                              │
│ ⚠ TRUNCATION: Each page truncated to 2000 tokens            │
│   via format_pages_for_prompt()                              │
│                                                              │
│ Continuity: previous_context carries last section title      │
│   or "continuing section: '{title}'" between batches         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: detect_sections_batch                              ║
║                                                             ║
║ Prompt:  stage_3 / detect_sections_batch                    ║
║          + structure_guidance_{type} sub-prompt              ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.1                                                ║
║ Tool:    detect_section_breaks                               ║
║ Returns: {sections: [{page_number, title, level}],          ║
║           continued_section_title}                           ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ SectionBreak objects accumulated across all batches           │
│ previous_context updated for next batch continuity           │
└──────────────────────────────────────────────────────────────┘
```

**Batch calculation:** `num_batches = ceil(len(pages) / 50)`

Example: 150-page document → 3 batches (1-50, 51-100, 101-150)

#### Phase 3: Consolidation

```
┌──────────────────────────────────────────────────────────────┐
│ All raw sections from Phase 2                                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: consolidate_structure                              ║
║                                                             ║
║ Prompt:  stage_3 / consolidate_structure                    ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.1                                                ║
║ Tool:    consolidate_sections                                ║
║ Input:   All detected sections as text list                  ║
║          + ToC info (if available)                            ║
║          + structure_type, confidence, total_pages            ║
║ Returns: {sections: [{page_number, title, level}],          ║
║           corrections_made: [str]}                           ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
              ┌────────────┴────────────┐
              │ LLM returned sections?  │
              └────┬──────────┬─────────┘
                   │ YES      │ NO
                   ▼          ▼
           ┌──────────┐  ┌──────────────────────────────────┐
           │ Use LLM  │  │ FALLBACK: consolidate_sections_  │
           │ result   │  │   simple()                       │
           └──────────┘  │                                  │
                         │ - Deduplicate by (page, title)   │
                         │ - Enforce MAX_SECTION_PAGES (100)│
                         │   by inserting "(continued)"     │
                         │   breaks every 100 pages         │
                         └──────────────────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────┐
                  │ Ensure first section starts at page 1│
                  │ (insert "Document Start" if needed)  │
                  └──────────────────────────────────────┘
```

---

### Step 3: Build Primary Sections

No LLM call - pure computation.

```
┌──────────────────────────────────────────────────────────────┐
│ For each SectionBreak at index i:                            │
│                                                              │
│   page_start = break[i].page_number                          │
│   page_end   = break[i+1].page_number - 1   (if next exists)│
│             OR len(pages)                    (if last)       │
│   page_end   = max(page_end, page_start)     (safety)       │
│                                                              │
│ Creates Section(id=uuid4, sequence_number=i+1, ...)          │
└──────────────────────────────────────────────────────────────┘
```

Example with 150 pages and breaks at [1, 35, 72, 110]:

| Section | Title          | page_start | page_end | Pages |
|---------|----------------|------------|----------|-------|
| 1       | Document Start | 1          | 34       | 34    |
| 2       | Chapter 2      | 35         | 71       | 37    |
| 3       | Chapter 3      | 72         | 109      | 38    |
| 4       | Chapter 4      | 110        | 150      | 41    |

---

### Step 4: Analyze Subsections

```
For each primary section:
┌──────────────────────────────────────────────────────────────┐
│ ✗ SKIP if section.page_count <= 3                            │
│                                                              │
│ Section content: pages joined with                           │
│   "\n\n---PAGE BREAK---\n\n"                                 │
│ ⚠ TRUNCATION: truncate_to_tokens(content, 12000)            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: analyze_subsections                                ║
║                                                             ║
║ Prompt:  stage_3 / analyze_subsections                      ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.2                                                ║
║ Tool:    analyze_subsections                                 ║
║ Returns: {subsections: [{title, page_start, page_end}]}     ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ VALIDATION:                                                  │
│   subsection.page_start = max(sub.page_start, section.start) │
│   subsection.page_end   = min(sub.page_end, section.end)     │
│                                                              │
│ Creates Subsection objects with UUIDs, sequence_number 1..N  │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 5: Generate Enhanced Summaries

Called once per section AND once per subsection.

```
For each section or subsection:
┌──────────────────────────────────────────────────────────────┐
│ Content: pages of that section, joined with PAGE BREAK       │
│ ⚠ TRUNCATION: first 20 pages only (pages[:20])              │
│ ⚠ TRUNCATION: truncate_to_tokens(content, 10000)            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: generate_section_summary_json                      ║
║                                                             ║
║ Prompt:  stage_3 / generate_section_summary_json            ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.2                                                ║
║ Tool:    generate_section_summary                            ║
║ Returns: JSON dict (see schema below)                        ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Summary JSON Schema:                                         │
│ {                                                            │
│   "overview":       str,     // What the section covers      │
│   "key_topics":     [str],   // Main concepts/themes         │
│   "key_metrics":    {} or [], // Numbers, statistics          │
│   "key_findings":   [str],   // Conclusions/results          │
│   "notable_facts":  [str]    // Specific answerable facts    │
│ }                                                            │
│                                                              │
│ NOTE: key_metrics can be dict OR list - handled at rendering │
└──────────────────────────────────────────────────────────────┘
```

**LLM call count for Step 5:** `num_sections + num_subsections`

---

### Step 6: Build Document Summary

No LLM call - pure markdown assembly.

```
┌──────────────────────────────────────────────────────────────┐
│ ASSEMBLY ORDER:                                              │
│                                                              │
│ # Document Metadata                                          │
│ Title: {metadata.title}                                      │
│ Authors: {metadata.authors joined with ", "}                 │
│ Date: {metadata.publication_date}                            │
│ Venue: {metadata.publication_venue}                          │
│ Pages: {page_count}                                          │
│                                                              │
│ # Abstract                                                   │
│ {metadata.abstract}    (only if non-empty)                   │
│                                                              │
│ # Section Summaries                                          │
│                                                              │
│ ## 1. {section.title} (pages {start}-{end})                  │
│ **Overview:** {summary.overview}                             │
│ **Key Topics:** {topics joined with ", "}                    │
│ **Key Metrics:** {k: v joined with "; "} or list             │
│ - {finding1}                                                 │
│ - {finding2}                                                 │
│ **Notable Facts:**                                           │
│ - {fact1}                                                    │
│                                                              │
│ ### 1.1 {subsection.title} (pages {start}-{end})            │
│ **Overview:** ...                                            │
│ **Key Topics:** ...                                          │
│ **Key Metrics:** ...                                         │
│ - {findings}                                                 │
│                                                              │
│ (repeated for all sections and subsections)                   │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 7: Generate Document Description & Usage

```
┌──────────────────────────────────────────────────────────────┐
│ Context built from:                                          │
│ - metadata.title, authors, date, venue                       │
│ - section_titles[:20]                                        │
│ - unique_topics[:15] (deduplicated key_topics from all sections) │
│ - section_summaries[:10] (overview + top 3 findings per section) │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ LLM CALL: generate_catalog_fields                            ║
║                                                             ║
║ Prompt:  stage_3 / generate_catalog_fields                  ║
║ Model:   config.MODEL_SMALL                                 ║
║ Temp:    0.3                                                ║
║ Tool:    generate_catalog_fields                             ║
║ Returns: {description: str, usage: str}                      ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ document_description: Brief 2-3 sentence description of      │
│   what the document is (for catalog display)                 │
│                                                              │
│ document_usage: Comprehensive paragraph with all details     │
│   for LLM document selection (used by metadata_subagent)     │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 8: Generate Summary Embedding

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT: document_summary (full markdown from Step 6)          │
│                                                              │
│ ⚠ TRUNCATION: truncate_to_tokens(summary, 8000)             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ EMBEDDING CALL                                               ║
║                                                             ║
║ Model:  config.MODEL_EMBEDDING (text-embedding-3-large)     ║
║ Input:  [truncated_summary]                                 ║
║ Output: 3072-dimension float vector                          ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ summary_embedding: List[float]  (3072 dimensions)            │
│                                                              │
│ DOWNSTREAM USE:                                              │
│   Stored in iris_document_metadata.summary_embedding         │
│   Used by metadata_subagent for document-level similarity    │
│   search (cosine distance via HNSW index)                    │
└──────────────────────────────────────────────────────────────┘
```

---

### Step 9: Generate Chunks

No LLM call - pure computation.

```
┌──────────────────────────────────────────────────────────────┐
│ For each page (1-indexed) with non-empty content:            │
│                                                              │
│ 1. Look up page_number in page_section_map → Section         │
│ 2. Look up page_number in page_subsection_map → Subsection   │
│ 3. Build hierarchy_path:                                     │
│    - Section + Subsection: "Section Title > Subsection Title"│
│    - Section only:         "Section Title"                   │
│    - Neither:              ""                                │
│                                                              │
│ chunk_number = page_number - 1  (0-indexed)                  │
│ page_number  = page_number      (1-indexed)                  │
└──────────────────────────────────────────────────────────────┘
```

**Chunk Dataclass Fields:**

| Field                       | Type           | Source                            |
|-----------------------------|----------------|-----------------------------------|
| id                          | str (UUID)     | uuid4()                           |
| primary_section_id          | Optional[str]  | Section.id                        |
| subsection_id               | Optional[str]  | Subsection.id                     |
| chunk_number                | int            | page_number - 1 (0-indexed)       |
| page_number                 | int            | 1-indexed page position           |
| raw_content                 | str            | Full page text                    |
| hierarchy_path              | str            | "Section > Subsection"            |
| primary_section_number      | Optional[int]  | Section.sequence_number           |
| primary_section_name        | Optional[str]  | Section.title                     |
| subsection_number           | Optional[int]  | Subsection.sequence_number        |
| subsection_name             | Optional[str]  | Subsection.title                  |
| primary_section_page_count  | Optional[int]  | Section.page_count                |
| subsection_page_count       | Optional[int]  | Subsection.page_count             |
| embedding                   | Optional[List] | Set in Step 10                    |

Empty pages (whitespace-only) are skipped.

---

### Step 10: Generate Chunk Embeddings

```
┌──────────────────────────────────────────────────────────────┐
│ For batches of EMBEDDING_BATCH_SIZE (100) chunks:            │
│                                                              │
│ Per chunk: ⚠ TRUNCATION: truncate_to_tokens(content, 8000)  │
│                                                              │
│ Batch texts = [truncated_content for chunk in batch]         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════╗
║ EMBEDDING CALL (per batch)                                   ║
║                                                             ║
║ Model:  config.MODEL_EMBEDDING (text-embedding-3-large)     ║
║ Input:  [text1, text2, ... text100]                         ║
║ Output: [[3072 floats], [3072 floats], ...]                 ║
╚══════════════════════════╤══════════════════════════════════╝
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ VALIDATION:                                                  │
│   len(embeddings) MUST == len(batch)                         │
│   Mismatch → raises RuntimeError (fails the document)        │
│                                                              │
│ FAILURE HANDLING:                                            │
│   Any batch failure → raises RuntimeError                    │
│   This fails the ENTIRE document (goes to failed_documents)  │
│   Other documents in the pipeline are unaffected             │
└──────────────────────────────────────────────────────────────┘
```

### Concrete Example: 150-Page PDF

```
Step 1:  First 2 pages → 3750 tokens max → 1 LLM call
Step 2:  Phase 1: First 100 pages → 1 LLM call (classification)
         Phase 2: 3 batches of 50 pages → 3 LLM calls (section detection)
         Phase 3: 1 LLM call (consolidation)
         Result: 8 primary sections detected
Step 3:  8 sections built from breaks (no LLM)
Step 4:  8 sections, skip 2 with ≤3 pages → 6 LLM calls (subsection analysis)
         12 subsections found
Step 5:  8 section summaries + 12 subsection summaries → 20 LLM calls
Step 6:  Markdown assembly (no LLM)
Step 7:  1 LLM call (description + usage)
Step 8:  1 embedding call (summary)
Step 9:  ~148 chunks generated (2 empty pages skipped)
Step 10: ceil(148/100) = 2 embedding batches → 2 embedding calls

TOTAL LLM CALLS: 1 + 1 + 3 + 1 + 6 + 20 + 1 = 33 LLM calls
TOTAL EMBEDDING CALLS: 1 + 2 = 3 embedding calls
```

### Error Handling

- If any step fails within `process_document()`, the exception is caught
- `processing_error` is set on the ProcessedDocument
- The document goes to `failed_documents[]`
- Other documents continue processing

---

## Stage 4: Validate

**Module:** `doc_refresh/stages/stage_4_validate.py`

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────┐
│ INPUT                │          │ OUTPUT: ValidationResult      │
│                      │          │                               │
│ processed_documents: │          │ validated_documents:          │
│   [ProcessedDocument]│────────▶ │   [ValidatedDocument]         │
│                      │          │ failed_documents:             │
│ strict: bool         │          │   [ProcessedDocument]         │
│                      │          │ all_errors: [ValidationError] │
│                      │          │ total_warnings: int           │
└──────────────────────┘          └──────────────────────────────┘
```

### Strict Mode

| Mode           | Condition                          | Behavior                  |
|----------------|------------------------------------|---------------------------|
| strict=True    | Default (non-dry-run)              | Warnings → rejection      |
| strict=False   | During --dry-run                   | Warnings → pass with note |

### Validation Checks

```
For each ProcessedDocument:
┌──────────────────────────────────────────────────────────────┐
│ 1. validate_required_fields                                  │
│ 2. validate_page_ranges                                      │
│ 3. validate_sections                                         │
│ 4. validate_chunks                                           │
│ 5. validate_embeddings                                       │
└──────────────────────────────────────────────────────────────┘
```

#### All Validation Checks Detail

| Check                         | Severity | Condition                                               |
|-------------------------------|----------|---------------------------------------------------------|
| **Required Fields**           |          |                                                         |
| file_info missing             | error    | file_info is None                                       |
| file_path missing             | error    | file_info.file_path empty                               |
| file_hash missing             | error    | file_info.file_hash empty                               |
| page_count invalid            | error    | page_count <= 0                                         |
| **Page Ranges**               |          |                                                         |
| start > end                   | error    | section.page_start > section.page_end                   |
| starts before page 1          | error    | section.page_start < 1                                  |
| ends after last page          | warning  | section.page_end > doc.page_count                       |
| sections overlap              | warning  | current.page_end >= next.page_start                     |
| **Sections**                  |          |                                                         |
| no sections (has pages)       | warning  | sections empty but page_count > 0                       |
| duplicate section IDs         | error    | non-unique section.id values                            |
| missing section ID            | error    | section.id empty                                        |
| missing section title         | error    | section.title empty                                     |
| missing section summary       | warning  | section.summary empty                                   |
| **Chunks**                    |          |                                                         |
| no chunks (has pages)         | error    | chunks empty but page_count > 0                         |
| too few chunks                | warning  | actual_chunks < expected_chunks * 0.5                   |
| duplicate chunk IDs           | error    | non-unique chunk.id values                              |
| missing chunk ID              | error    | chunk.id empty                                          |
| empty chunk content           | warning  | chunk.raw_content empty                                 |
| **Embeddings**                |          |                                                         |
| no embeddings at all          | error    | all chunks missing embeddings                           |
| some missing embeddings       | warning  | partial chunks missing embeddings                       |
| empty embedding vector        | error    | chunk.embedding exists but len() == 0                   |

### Decision Tree

```
┌─────────────────────────┐
│ Run all 5 validators    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Any severity="error"?   │
└────┬──────────┬─────────┘
     │ YES      │ NO
     ▼          ▼
┌─────────┐  ┌──────────────────────────────┐
│ REJECT  │  │ strict mode AND has warnings? │
│ →failed │  └────┬──────────┬──────────────┘
└─────────┘       │ YES      │ NO
                  ▼          ▼
             ┌─────────┐  ┌─────────┐
             │ REJECT  │  │ PASS    │
             │ →failed │  │ →valid  │
             └─────────┘  │ (with   │
                          │ warnings│
                          └─────────┘
```

---

## Stage 5: Database

**Module:** `doc_refresh/stages/stage_5_database.py`

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────┐
│ INPUT                │          │ OUTPUT: DatabaseResult        │
│                      │          │                               │
│ files_to_remove:     │          │ documents_removed: int        │
│   [{db_source,       │────────▶ │ documents_inserted: int       │
│     file_path}]      │          │ sections_inserted: int        │
│                      │          │ chunks_inserted: int          │
│ validated_documents: │          │ errors: [str]                 │
│   [ValidatedDocument]│          │                               │
│                      │          │                               │
│ dry_run: bool        │          │                               │
└──────────────────────┘          └──────────────────────────────┘
```

### 2-Table Design

```
┌────────────────────────────────────┐     ┌─────────────────────────────────────┐
│ iris_document_metadata             │     │ iris_document_chunks                 │
│                                    │     │                                     │
│ id (UUID, PK)                 ◀────┼─────┤ document_id (UUID, FK)              │
│ db_source (VARCHAR, FK→registry)   │     │ id (UUID, PK)                       │
│ document_name (VARCHAR)            │     │ db_source (VARCHAR, FK→registry)     │
│ document_type (VARCHAR)            │     │ chunk_number (INTEGER)              │
│ document_summary (TEXT)            │     │ primary_section_number (INTEGER)    │
│ summary_embedding (HALFVEC 3072)   │     │ primary_section_name (VARCHAR)      │
│ page_count (INTEGER)               │     │ subsection_number (INTEGER)         │
│ primary_section_count (INTEGER)    │     │ subsection_name (VARCHAR)           │
│ subsection_count (INTEGER)         │     │ hierarchy_path (VARCHAR)            │
│ file_name (VARCHAR)                │     │ chunk_content (TEXT)                │
│ file_path (TEXT)                   │     │ chunk_embedding (HALFVEC 3072)      │
│ file_size (BIGINT)                 │     │ page_number (INTEGER)              │
│ file_hash (VARCHAR 64)             │     │ file_name (VARCHAR)                │
│ file_type (VARCHAR)                │     │ source_filename (VARCHAR)          │
│ document_description (TEXT)        │     │ created_at (TIMESTAMP)             │
│ document_usage (TEXT)              │     │ primary_section_page_count (INT)   │
│ created_at (TIMESTAMP)             │     │ subsection_page_count (INTEGER)    │
│ updated_at (TIMESTAMP)             │     │                                     │
└────────────────────────────────────┘     └─────────────────────────────────────┘
         ▲                                          ▲
         │ FK: db_source                            │ FK: db_source
         │                                          │ FK: document_id
┌────────────────────────────────────┐
│ iris_database_registry             │
│                                    │
│ db_source (VARCHAR, PK)            │
│ ... (config columns)               │
└────────────────────────────────────┘
```

### Remove-Then-Insert Flow

```
For UPDATED documents (action="update"):
┌──────────────────────────────────────────────────────────────┐
│ 1. REMOVE existing document:                                 │
│    a. SELECT id FROM iris_document_metadata                  │
│       WHERE db_source = :src AND file_path = :path           │
│    b. DELETE FROM iris_document_chunks                        │
│       WHERE document_id = :id                                │
│    c. DELETE FROM iris_document_metadata                      │
│       WHERE id = :id                                         │
│                                                              │
│ 2. INSERT new document (same flow as new documents)          │
└──────────────────────────────────────────────────────────────┘
```

### Insert Flow

```
┌───────────────────────────────────────────────────────────────┐
│ Within a single SQLAlchemy session (auto-commit on success):  │
│                                                               │
│ 1. INSERT INTO iris_document_metadata (...)                   │
│    VALUES (:db_source, :document_name, ...)                   │
│    RETURNING id                                               │
│    → document_id                                              │
│                                                               │
│ 2. For each chunk:                                            │
│    INSERT INTO iris_document_chunks (                          │
│      document_id, db_source, chunk_number, ...                │
│    ) VALUES (:document_id, ...)                               │
│                                                               │
│ 3. Session auto-commits on context exit                       │
│    → On error: session.rollback()                             │
└───────────────────────────────────────────────────────────────┘
```

### Embedding Serialization

Embeddings are serialized as PostgreSQL HALFVEC strings:

```python
# Python → PostgreSQL
embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
# Results in: "[0.0123,0.0456,-0.0789,...]"
# Cast in SQL: :embedding::halfvec
```

### Column Mapping: iris_document_metadata

| Column                  | Source                                          |
|-------------------------|-------------------------------------------------|
| db_source               | file_info.db_source                             |
| document_name           | file_info.file_name                             |
| document_type           | structure_type.value ("chapters"/"sections"/etc) |
| document_summary        | document_summary (markdown from Step 6)         |
| summary_embedding       | summary_embedding (from Step 8)                 |
| page_count              | page_count                                      |
| primary_section_count   | len(sections)                                   |
| subsection_count        | sum(len(s.subsections) for s in sections)       |
| file_name               | file_info.file_name                             |
| file_path               | file_info.relative_path                         |
| file_size               | file_info.file_size                             |
| file_hash               | file_info.file_hash (SHA-256)                   |
| file_type               | extension from filename (e.g., "pdf")           |
| document_description    | document_description (from Step 7)              |
| document_usage          | document_usage (from Step 7)                    |

### Column Mapping: iris_document_chunks

| Column                      | Source                                   |
|-----------------------------|------------------------------------------|
| document_id                 | From RETURNING id of metadata INSERT     |
| db_source                   | file_info.db_source                      |
| chunk_number                | chunk.chunk_number (0-indexed)           |
| primary_section_number      | chunk.primary_section_number             |
| primary_section_name        | chunk.primary_section_name               |
| subsection_number           | chunk.subsection_number                  |
| subsection_name             | chunk.subsection_name                    |
| hierarchy_path              | chunk.hierarchy_path                     |
| chunk_content               | chunk.raw_content                        |
| chunk_embedding             | chunk.embedding (3072-dim float vector)  |
| page_number                 | chunk.page_number (1-indexed)            |
| file_name                   | file_info.file_name                      |
| source_filename             | file_info.file_name                      |
| primary_section_page_count  | chunk.primary_section_page_count         |
| subsection_page_count       | chunk.subsection_page_count              |

### Transaction Boundaries

- Each document removal is its own session/transaction
- Each document insertion (metadata + all chunks) is one session/transaction
- For updates: removal and insertion are separate transactions

### Error Handling

- Per-document errors are caught and added to `errors[]`
- Pipeline continues with remaining documents
- DRY RUN mode simulates all operations, counts what would happen

---

## Stage 6: Report

**Module:** `doc_refresh/stages/stage_6_report.py`

### Input / Output

```
┌──────────────────────┐          ┌──────────────────────────────┐
│ INPUT                │          │ OUTPUT: ReportResult          │
│                      │          │                               │
│ All stage results    │          │ report_dict: Dict             │
│ (can be None)        │────────▶ │ report_path: Optional[str]    │
│                      │          │ success: bool                 │
│ output_path: str     │          │                               │
└──────────────────────┘          └──────────────────────────────┘
```

### Report Structure

The `report_dict` contains:

```json
{
  "timestamp": "2026-02-09T...",
  "run_uuid": "...",
  "configuration": {
    "file_source_mode": "local",
    "base_path": "/data/...",
    "database_names": ["internal_capm", ...],
    "dry_run": false,
    "force": false
  },
  "summary": {
    "total_duration_seconds": 142.5,
    "total_cost": 0.0834,
    "total_tokens": 125000
  },
  "stages": {
    "scan":     { "files_to_process": 3, "files_to_remove": 1, ... },
    "extract":  { "documents_extracted": 3, "total_pages": 350, ... },
    "process":  { "documents_processed": 3, "total_sections": 24, ... },
    "validate": { "documents_validated": 3, "total_warnings": 1, ... },
    "database": { "documents_inserted": 3, "chunks_inserted": 345, ... }
  },
  "errors": []
}
```

### Console Output

```
============================================================
DOCUMENT REFRESH PIPELINE SUMMARY
============================================================

Configuration:
  File Source: local
  Base Path: /data/iris_documents
  Databases: internal_capm, external_iasb

Duration: 142.5 seconds
Total Cost: $0.0834
Total Tokens: 125,000

------------------------------------------------------------
Stage Results:

  Scan:
    Files to process: 3
    Files to remove: 1
    Files unchanged: 12
    Databases: internal_capm, external_iasb

  Extract:
    Documents extracted: 3
    Documents failed: 0
    Total pages: 350

  Process:
    Documents processed: 3
    Documents failed: 0
    Sections created: 24
    Chunks created: 345

  ...

============================================================
```

### Process Monitor

The `ProcessMonitoringManager` singleton tracks:

| Metric            | Scope          | What it records                              |
|-------------------|----------------|----------------------------------------------|
| run_uuid          | Global         | UUID for this pipeline run                   |
| start/end time    | Global + stage | Wall clock timing                            |
| llm_calls_data    | Per stage      | model, prompt/completion tokens, cost, ms    |
| details           | Per stage      | Stage-specific metrics (counts, errors, etc) |

Data is logged to `process_monitor_logs` table (if enabled).

---

## Appendix: How Retrieval Agents Consume This Data

The doc_refresh pipeline writes data that is read by IRIS retrieval agents at query time.

### Architecture

```
┌──────────────────────────────────────────────────────┐
│ USER QUERY                                            │
│ "What are the disclosure requirements for leases?"    │
└─────────────────────────┬────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ Router → Clarifier → Planner (selects databases)      │
└─────────────────────────┬────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
┌──────────────────────┐     ┌──────────────────────────┐
│ STAGE 1:             │     │ STAGE 2:                  │
│ Metadata Subagent    │     │ File Research Subagent    │
│                      │     │                           │
│ Uses:                │     │ Uses:                     │
│ - summary_embedding  │     │ - chunk_embedding         │
│ - document_summary   │     │ - chunk_content           │
│ - document_name      │     │ - hierarchy_path          │
│ - page_count         │     │ - page_number             │
│                      │     │ - primary_section_*       │
│ Returns:             │     │ - subsection_*            │
│ - answered findings  │     │ - *_page_count            │
│ - needs_deep_research│     │                           │
│   doc IDs ──────────────▶  │ Returns:                  │
│                      │     │ - page-level findings     │
└──────────────────────┘     │ - citations               │
                             └──────────────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────────┐
                             │ Summarizer Agent          │
                             │ Synthesizes all findings  │
                             └──────────────────────────┘
```

### Metadata Subagent: Document Discovery

The metadata subagent uses `summary_embedding` for document-level similarity search:

```sql
-- Cosine similarity search on summary embeddings
SELECT id, document_name, document_summary, page_count, ...
FROM iris_document_metadata
WHERE db_source = :db_source
ORDER BY summary_embedding <=> :query_embedding::halfvec
LIMIT :batch_size
```

- Also fetches top N chunk excerpts per document for richer context
- LLM makes 3-way decision per document: `answered` | `irrelevant` | `needs_deep_research`
- Documents marked `needs_deep_research` are passed to File Research Subagent

### File Research Subagent: Chunk-Level Retrieval

Uses hierarchical expansion strategy based on `iris_database_registry` parameters:

```
For each document needing deep research:
┌──────────────────────────────────────────────────────────────┐
│ 1. Is document "small" (page_count <= max_pages_for_full)?   │
│    YES → Fetch ALL chunks in page order (document_full)      │
│    NO  → Continue to similarity search                       │
│                                                              │
│ 2. Similarity search on chunk_embedding:                     │
│    SELECT chunk_number, page_number, chunk_content,           │
│           hierarchy_path, primary_section_*, subsection_*     │
│    ORDER BY chunk_embedding <=> :query_embedding             │
│    LIMIT :max_chunks_per_file                                │
│                                                              │
│ 3. Expand seed chunks by hierarchy:                          │
│    - If primary_section_page_count <= threshold               │
│      → Fetch entire primary section (primary_section)        │
│    - If subsection_page_count <= threshold                    │
│      → Fetch entire subsection (subsection)                  │
│    - Otherwise → Fetch neighbor chunks (neighbor)            │
│                                                              │
│ 4. LLM extracts page-level findings from expanded content    │
└──────────────────────────────────────────────────────────────┘
```

### Key iris_database_registry Parameters

These parameters (set per-database) control how retrieval agents consume doc_refresh output:

| Parameter                          | Default | Controls                                           |
|------------------------------------|---------|----------------------------------------------------|
| batch_size                         | 10      | Documents per metadata batch sent to LLM           |
| max_selected_files                 | 8-15    | Max files selected for deep research               |
| top_chunks_in_catalog_selection    | 1-2     | Chunk excerpts shown per doc in catalog selection   |
| top_chunks_in_metadata_research    | 3       | Chunk excerpts shown per doc in metadata research   |
| max_pages_for_full_context         | 6       | If doc has <= this many pages, send full content    |
| max_primary_section_page_count     | 6       | If section <= this, expand to full section          |
| max_subsection_page_count          | 3       | If subsection <= this, expand to full subsection    |
| max_neighbour_chunks               | 2       | Chunks to add before/after each seed chunk          |
| max_gap_fill_pages                 | 2       | Pages to fill between nearby seed chunks            |
| max_chunks_per_file                | 20      | Max chunks retrieved per document                   |
| max_parallel_files                 | 5       | Concurrent file research tasks                      |
| metadata_context_fields            | [doc_summary] | Which fields shown to LLM in metadata phase   |

### Field Usage Summary

| doc_refresh Field               | Written To                         | Read By                    | Purpose                        |
|---------------------------------|------------------------------------|----------------------------|---------------------------------|
| summary_embedding               | iris_document_metadata             | metadata_subagent          | Document-level similarity       |
| document_summary                | iris_document_metadata             | metadata_subagent          | LLM context for 3-way decision |
| document_description            | iris_document_metadata             | metadata_subagent          | Catalog display                 |
| document_usage                  | iris_document_metadata             | metadata_subagent          | LLM document selection          |
| page_count                      | iris_document_metadata             | file_research_subagent     | Full-doc vs chunk decision      |
| chunk_embedding                 | iris_document_chunks               | file_research_subagent     | Chunk-level similarity          |
| chunk_content                   | iris_document_chunks               | file_research_subagent     | Content sent to LLM             |
| hierarchy_path                  | iris_document_chunks               | file_research_subagent     | Context prefix for chunks       |
| primary_section_name            | iris_document_chunks               | file_research_subagent     | Section grouping                |
| subsection_name                 | iris_document_chunks               | file_research_subagent     | Subsection grouping             |
| primary_section_page_count      | iris_document_chunks               | file_research_subagent     | Expansion decision              |
| subsection_page_count           | iris_document_chunks               | file_research_subagent     | Expansion decision              |
| page_number                     | iris_document_chunks               | file_research_subagent     | Citation, neighbor expansion    |
| primary_section_number          | iris_document_chunks               | file_research_subagent     | Section-level chunk fetch       |
| subsection_number               | iris_document_chunks               | file_research_subagent     | Subsection-level chunk fetch    |

---

## Appendix: All Truncation Points Summary

| Location                    | What is truncated             | Limit       | Unit   | Function             |
|-----------------------------|-------------------------------|-------------|--------|----------------------|
| Step 1: Metadata            | First 2 pages                 | 3,750       | tokens | truncate_to_tokens   |
| Step 1: Metadata            | abstract field                | 500         | chars  | str[:500]            |
| Step 2: Classification      | Each page in prompt           | 2,000       | tokens | format_pages_for_prompt |
| Step 2: Section Detection   | Each page in prompt           | 2,000       | tokens | format_pages_for_prompt |
| Step 4: Subsections         | Section content               | 12,000      | tokens | truncate_to_tokens   |
| Step 5: Summaries           | Section content (first 20pp)  | 10,000      | tokens | truncate_to_tokens   |
| Step 8: Summary Embedding   | Full document summary         | 8,000       | tokens | truncate_to_tokens   |
| Step 10: Chunk Embeddings   | Per-chunk content             | 8,000       | tokens | truncate_to_tokens   |
| DOCX Page Split             | Synthetic page                | 4,000       | chars  | SYNTHETIC_PAGE_SIZE  |

## Appendix: All LLM Calls Summary

| Step | Prompt Name                      | Tool Name                   | Model       | Temp | Calls per Document                     |
|------|----------------------------------|-----------------------------|-------------|------|-----------------------------------------|
| 1    | extract_document_metadata        | extract_metadata            | MODEL_SMALL | 0.1  | 1                                       |
| 2a   | classify_document                | classify_document_structure | MODEL_SMALL | 0.1  | 1                                       |
| 2b   | detect_sections_batch            | detect_section_breaks       | MODEL_SMALL | 0.1  | ceil(pages / 50)                        |
| 2c   | consolidate_structure            | consolidate_sections        | MODEL_SMALL | 0.1  | 1                                       |
| 4    | analyze_subsections              | analyze_subsections         | MODEL_SMALL | 0.2  | sections with > 3 pages                 |
| 5    | generate_section_summary_json    | generate_section_summary    | MODEL_SMALL | 0.2  | num_sections + num_subsections          |
| 7    | generate_catalog_fields          | generate_catalog_fields     | MODEL_SMALL | 0.3  | 1                                       |
| 8    | (embedding)                      | --                          | MODEL_EMBED | --   | 1                                       |
| 10   | (embedding)                      | --                          | MODEL_EMBED | --   | ceil(chunks / 100)                      |

All prompts are loaded from PostgreSQL `prompts` table with `model='doc_refresh'`, `layer='stage_3'`.
