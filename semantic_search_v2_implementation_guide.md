# Semantic Search V2 Implementation Guide
**Comparison Period**: August 7, 2025 (commit 696d80b) to August 20, 2025 (HEAD)

## New Files Added

### 1. `services/src/agents/database_subagents/semantic_search_v2/__init__.py` (5 lines)
**Purpose**: Package initialization file that exports the `query_database_sync` function for clean imports from the semantic_search_v2 subagent.

### 2. `services/src/agents/database_subagents/semantic_search_v2/subagent.py` (1,792 lines)
**Purpose**: New implementation of semantic search subagent that queries the iris_semantic_search table. Key features include:
- Top-k semantic search with pgvector embedding similarity
- Multi-stage retrieval: semantic search → section expansion (for sections ≤6 pages) → gap filling (for missing sections between results)
- Dual page reference system (PageNumber for PDF navigation, PageReference for display)
- REF tag integration with reference index tracking
- Support for both single document (document_id) and multi-document queries
- Fixes NULL vector score issues by filtering invalid embeddings

### 3. `services/src/agents/database_subagents/semantic_search_v2/content_synthesis_prompt.yaml` (216 lines)
**Purpose**: YAML configuration for the content synthesis LLM prompt. Defines instructions for:
- Extracting page-based research findings from technical documentation
- Handling multiple page reference locations (XML metadata, HTML markers, content markers)
- Creating proper citations with PageNumber (for navigation) and PageReference (for display)
- Analytical, objective tone for research extraction
- Target audience is the internal Summarizer Agent

---

## Changes to Existing Files

### File: `services/src/agents/database_subagents/database_router.py`

#### Change 1: Import Statement Update
**Location**: Line 169

**BEFORE**:
```python
# Use the unified semantic_search subagent for external databases
from .semantic_search.subagent import query_database_sync
```

**AFTER**:
```python
# Use the new semantic_search_v2 subagent for external databases
from .semantic_search_v2.subagent import query_database_sync
```

**Reasoning**: Routes all external database queries to the new v2 implementation that fixes the NULL vector score issue and provides enhanced reference extraction capabilities.

---

### File: `services/src/chat_model/model.py`

#### Change 1: Enhanced Reference Processing in _process_final_references
**Location**: Lines 341-380

**BEFORE**:
```python
                highlight_text = ref_data.get("highlight_text", "")
                doc_name = ref_data.get("doc_name", "Unknown Document")

                # Create S3 URL using S3_BASE_PATH + file_name
                s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                # Create href link with 3-parameter format: filename, page, highlight_text
                page_key = (doc_name, page)
                if page_key not in page_links:
                    link_text = f"📄 {doc_name} Page {page}"
                    href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                    page_links[page_key] = href
```

**AFTER**:
```python
                highlight_text = ref_data.get("highlight_text", "")
                doc_name = ref_data.get("doc_name", "Unknown Document")

                # Extract additional fields for semantic search
                page_reference = ref_data.get(
                    "page_reference", str(page)
                )  # Display reference
                chapter_number = ref_data.get("chapter_number", "")  # Chapter number
                source_filename = ref_data.get(
                    "source_filename", doc_name
                )  # Original document name
                
                # Debug logging to verify page numbers
                logger.debug(
                    f"REF:{ref_id} - page={page}, page_reference={page_reference}, "
                    f"chapter={chapter_number}, source={source_filename}"
                )

                # Create S3 URL using S3_BASE_PATH + file_name
                s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                # Create href link with 3-parameter format: filename, page, highlight_text
                page_key = (doc_name, page)
                if page_key not in page_links:
                    # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                    # Always show page_reference when available (it's the display text)
                    if chapter_number:
                        if page_reference and page_reference != "0":
                            # Show full format with page reference
                            link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                        else:
                            # No page_reference, fallback to page number
                            link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page}"
                    else:
                        # Fallback for catalog search or when chapter not available
                        if page_reference and page_reference != "0":
                            link_text = f"📄 {source_filename}, Pg. {page_reference}"
                        else:
                            # No page_reference, fallback to page number
                            link_text = f"📄 {source_filename}, Pg. {page}"
                    
                    # Use 'page' (which contains page_number) for PDF navigation
                    # page_reference is only for display text
                    href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                    page_links[page_key] = href
```

**Reasoning**: Added support for semantic_search_v2's enhanced metadata (page_reference, chapter_number, source_filename) to provide more informative and accurate reference links. Separates display page reference from actual PDF navigation page number.

#### Change 2: _process_reference_buffer Enhanced Formatting
**Location**: Lines 532-566

**BEFORE**:
```python
                # Create href link with 3-parameter format: filename, page, highlight_text
                link_text = f"📄 {doc_name} Page {page}"
                href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'

                replacement = f" {href} "
```

**AFTER**:
```python
                # Extract additional fields for semantic search
                page_reference = ref_data.get(
                    "page_reference", str(page)
                )  # Display reference
                chapter_number = ref_data.get("chapter_number", "")  # Chapter number
                source_filename = ref_data.get(
                    "source_filename", doc_name
                )  # Original document name

                # Create S3 URL using S3_BASE_PATH + file_name
                s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                # Create href link with 3-parameter format: filename, page, highlight_text
                # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                # Handle missing page_reference gracefully
                if chapter_number:
                    if (
                        page_reference
                        and page_reference != str(page)
                        and page_reference != "0"
                    ):
                        link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                    else:
                        # No valid page_reference, just show source and chapter
                        link_text = f"📄 {source_filename}, Ch. {chapter_number}"
                else:
                    # Fallback for catalog search or when chapter not available
                    if (
                        page_reference
                        and page_reference != str(page)
                        and page_reference != "0"
                    ):
                        link_text = f"📄 {source_filename}, Pg. {page_reference}"
                    else:
                        # No valid page_reference, just show source
                        link_text = f"📄 {source_filename}"
                href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'

                replacement = f" {href} "
```

**Reasoning**: Consistent enhanced formatting for reference buffer processing with chapter and page reference support.

#### Change 3: Additional Reference Buffer Page Links Enhancement
**Location**: Lines 616-658

**BEFORE**:
```python
                    if page_key not in page_links:
                        link_text = f"📄 {doc_name} Page {page}"
                        href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                        page_links[page_key] = href
```

**AFTER**:
```python
                    # Extract additional fields for semantic search
                    page_reference = ref_data.get(
                        "page_reference", str(page)
                    )  # Display reference
                    chapter_number = ref_data.get(
                        "chapter_number", ""
                    )  # Chapter number
                    source_filename = ref_data.get(
                        "source_filename", doc_name
                    )  # Original document name

                    # Create S3 URL using S3_BASE_PATH + file_name
                    s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                    # Create href link with 3-parameter format: filename, page, highlight_text
                    page_key = (doc_name, page)
                    if page_key not in page_links:
                        # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                        # Handle missing page_reference gracefully
                        if chapter_number:
                            if (
                                page_reference
                                and page_reference != str(page)
                                and page_reference != "0"
                            ):
                                link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                            else:
                                # No valid page_reference, just show source and chapter
                                link_text = (
                                    f"📄 {source_filename}, Ch. {chapter_number}"
                                )
                        else:
                            # Fallback for catalog search or when chapter not available
                            if (
                                page_reference
                                and page_reference != str(page)
                                and page_reference != "0"
                            ):
                                link_text = (
                                    f"📄 {source_filename}, Pg. {page_reference}"
                                )
                            else:
                                # No valid page_reference, just show source
                                link_text = f"📄 {source_filename}"
                        href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                        page_links[page_key] = href
```

**Reasoning**: Complete implementation of enhanced reference formatting across all reference processing paths.

#### Change 4: Support for semantic_search_v2 Response Format
**Location**: Lines 1394-1437

**BEFORE**:
```python
                                        if (
                                            isinstance(page_data, dict)
                                            and "research_content" in page_data
                                        ):
                                            page_number = page_data.get(
                                                "page_number", 0
                                            )
                                            research_content = page_data.get(
                                                "research_content", ""
                                            )
                                            file_link = page_data.get("file_link", "")
                                            file_name = page_data.get("file_name", "")

                                            # Assign REF number
                                            ref_id = str(ref_counter)
                                            
                                            ...
                                            
                                            reference_index[ref_id] = {
                                                "doc_name": doc_name,
                                                "file_link": file_link,
                                                "file_name": file_name,
                                                "page": page_number,
                                                "highlight_text": "",  # Empty as requested
                                                "source_db": db_name,
                                            }
```

**AFTER**:
```python
                                        if (
                                            isinstance(page_data, dict)
                                            and "research_content" in page_data
                                        ):
                                            # semantic_search_v2 stores it as "page" not "page_number"
                                            page_number = page_data.get(
                                                "page", page_data.get("page_number", 0)
                                            )
                                            research_content = page_data.get(
                                                "research_content", ""
                                            )
                                            file_link = page_data.get("file_link", "")
                                            file_name = page_data.get("file_name", "")
                                            
                                            # Get additional fields from semantic_search_v2
                                            page_reference = page_data.get("page_reference", str(page_number))
                                            chapter_number = page_data.get("chapter_number", "")
                                            source_filename = page_data.get("source_filename", doc_name)

                                            # Assign REF number
                                            ref_id = str(ref_counter)
                                            
                                            ...
                                            
                                            reference_index[ref_id] = {
                                                "doc_name": doc_name,
                                                "file_link": file_link,
                                                "file_name": file_name,
                                                "page": page_number,  # For PDF navigation
                                                "page_reference": page_reference,  # For display text
                                                "chapter_number": chapter_number,
                                                "source_filename": source_filename,
                                                "highlight_text": "",  # Empty as requested
                                                "source_db": db_name,
                                            }
```

**Reasoning**: Handles semantic_search_v2's response format which uses "page" instead of "page_number", and extracts additional metadata fields for enhanced reference display.

#### Change 5: Document Display Name Support
**Location**: Lines 1481-1490

**BEFORE**:
```python
                                for doc_name, doc_data in db_research.items():
                                    combined_research += f"## {doc_name}\n\n"

                                    for page_key, page_data in doc_data.items():
                                        page_number = page_data.get("page_number", 0)
```

**AFTER**:
```python
                                for doc_name, doc_data in db_research.items():
                                    # Use display name if available, otherwise use doc_name
                                    display_name = doc_data.get(
                                        "_display_name", doc_name
                                    )
                                    combined_research += f"## {display_name}\n\n"

                                    for page_key, page_data in doc_data.items():
                                        # Skip the _display_name metadata field
                                        if page_key == "_display_name":
                                            continue
                                        page_number = page_data.get("page_number", 0)
```

**Reasoning**: Supports semantic_search_v2's `_display_name` metadata field for better document titles while properly skipping it during iteration.

---

## Summary of Changes

### New Implementation
- Complete semantic_search_v2 subagent (2,013 lines total across 3 files)
- Fixes critical NULL vector score bug
- Implements multi-stage retrieval pipeline
- Dual page reference system for accurate citations

### Modified Files
1. **database_router.py**: Routes to v2 implementation
2. **model.py**: 
   - Enhanced reference formatting with chapter/page metadata
   - Support for v2 response format
   - Document display name support