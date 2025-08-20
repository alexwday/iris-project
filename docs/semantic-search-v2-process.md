# Semantic Search V2 Process Documentation

## Overview
The semantic search v2 subagent processes queries through a 6-step pipeline to provide comprehensive, well-structured research with proper citations.

## Process Steps

### 1. Similarity Search (`_perform_vector_search`)
- Performs vector similarity search using query embedding
- Searches against `iris_semantic_search` table
- Returns top-k results based on cosine similarity
- Can filter by document_id for targeted searches

### 2. Relevance Filtering (`_filter_by_relevance`)
- Uses LLM to evaluate chapter and section summaries
- Removes completely irrelevant chunks (conservative approach)
- Keeps anything with potential relevance to the query
- Returns filtered list of relevant chunks

### 3. Section Expansion (`_expand_to_full_sections`)
- For sections with ≤6 pages (`SECTION_EXPANSION_MAX_PAGES`)
- Retrieves ALL chunks from the same chapter+section
- Orders chunks by chunk_number
- Ensures complete context for small sections

### 4. Gap Filling (`_fill_section_gaps`)
- Identifies gaps of 1-2 sections between results
- Fills gaps by retrieving missing sections
- Helps maintain narrative continuity
- Prevents missing important connecting information

### 5. Context Formatting (`_format_context_with_blocks`)
- Structures content hierarchically in XML format:
  ```xml
  <DOCUMENT id="doc_id">
    <CHAPTER number="X">
      <metadata>
        <filename>chapter.pdf</filename>
        <source_filename>original_doc.pdf</source_filename>
        <chapter_name>Chapter Title</chapter_name>
      </metadata>
      <sections>
        <SECTION number="Y" type="full|partial">
          <section_metadata>
            <start_page>1</start_page>
            <end_page>5</end_page>
            <start_reference>3-1</start_reference>
            <end_reference>3-5</end_reference>
          </section_metadata>
          <content_blocks>
            <!-- Actual content here -->
          </content_blocks>
        </SECTION>
      </sections>
    </CHAPTER>
  </DOCUMENT>
  ```

### 6. Research Extraction (`_generate_synthesis_response`)
- LLM extracts page-based research findings
- Each finding includes:
  - `filename`: Chapter PDF filename
  - `page_number`: Actual page in PDF (for navigation)
  - `page_reference`: Original document reference (for display)
  - `chapter_number`: Chapter number
  - `source_filename`: Original document name
  - `research_content`: Extracted findings
- Returns structured output compatible with REF system

## Key Configuration Constants
- `INITIAL_K = 20`: Initial retrieval count
- `SECTION_EXPANSION_MAX_PAGES = 6`: Max pages for full section expansion
- `GAP_FILL_MAX_SECTIONS = 2`: Max gap size to fill
- `MAX_RESPONSE_TOKENS = 32768`: Max tokens for LLM response

## Output Format
The final output is a structured dictionary:
```python
{
    "document_name_ChX": {
        "_display_name": "Document Name - Chapter X",
        "page_Y": {
            "research_content": "...",
            "file_link": "s3://...",
            "file_name": "chapter.pdf",
            "page": Y,  # For PDF navigation
            "page_reference": "3-15",  # For display
            "chapter_number": X,
            "source_filename": "original.pdf",
            "doc_name": "document_name_ChX"
        }
    }
}
```

## REF Link Generation
The model.py processes references to create hyperlinks:
- Format: `📄 source_filename, Ch. X, Pg. Y-Z`
- Gracefully handles missing page_reference
- Falls back to showing just source and chapter if no page reference

## Known Issues and Solutions

### Issue: Multiple chapters overwriting each other
**Solution**: Use unique doc_name key including chapter number (e.g., `document_ChX`)

### Issue: Page references showing as 0
**Solution**: 
1. Updated prompt to correctly reference XML structure
2. Added graceful handling for missing page_reference
3. Falls back to showing just source and chapter

### Issue: Research truncation
**Solution**: Ensure all chapters are processed and stored with unique keys