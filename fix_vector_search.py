#!/usr/bin/env python3
"""
Fix for vector search returning NULL scores.
This script provides SQL solutions to handle invalid vectors in the query.
"""

# Solution 1: Modify the search query to filter out invalid vectors
FIXED_VECTOR_SEARCH_SQL = """
SELECT
    id,
    document_id,
    filename,
    filepath,
    source_filename,
    chapter_number,
    chapter_name,
    chapter_summary,
    chapter_page_count,
    section_number,
    section_summary,
    section_start_page,
    section_end_page,
    section_page_count,
    section_start_reference,
    section_end_reference,
    chunk_number,
    chunk_content,
    chunk_start_page,
    chunk_end_page,
    chunk_start_reference,
    chunk_end_reference,
    1 - (embedding::vector <=> %s::vector) AS vector_score
FROM iris_semantic_search
WHERE 
    embedding IS NOT NULL
    -- Filter out vectors with NaN or Infinity values
    AND NOT embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
    -- Ensure the vector has the correct dimensions
    AND array_length(embedding::real[], 1) = 2000
    {doc_filter}
ORDER BY vector_score DESC
LIMIT %s;
"""

# Solution 2: Create a function to validate vectors
CREATE_VALIDATION_FUNCTION = """
CREATE OR REPLACE FUNCTION is_valid_vector(v vector)
RETURNS boolean AS $$
DECLARE
    v_text text;
BEGIN
    IF v IS NULL THEN
        RETURN false;
    END IF;
    
    v_text := v::text;
    
    -- Check for NaN or Infinity
    IF v_text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' THEN
        RETURN false;
    END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# Solution 3: Clean existing data by removing invalid vectors
IDENTIFY_INVALID_VECTORS = """
-- Find rows with invalid vectors
SELECT 
    id,
    document_id,
    chunk_number,
    embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' as has_invalid_values
FROM iris_semantic_search
WHERE 
    embedding IS NOT NULL
    AND embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf';
"""

# Solution 4: Set invalid vectors to NULL so they're excluded from search
NULLIFY_INVALID_VECTORS = """
-- Set invalid vectors to NULL
UPDATE iris_semantic_search
SET embedding = NULL
WHERE 
    embedding IS NOT NULL
    AND embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf';
"""

# Solution 5: Alternative using CASE to handle NULLs gracefully
SAFE_VECTOR_SEARCH_SQL = """
SELECT
    id,
    document_id,
    filename,
    filepath,
    source_filename,
    chapter_number,
    chapter_name,
    chapter_summary,
    chapter_page_count,
    section_number,
    section_summary,
    section_start_page,
    section_end_page,
    section_page_count,
    section_start_reference,
    section_end_reference,
    chunk_number,
    chunk_content,
    chunk_start_page,
    chunk_end_page,
    chunk_start_reference,
    chunk_end_reference,
    CASE 
        WHEN embedding IS NULL THEN NULL
        WHEN embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' THEN NULL
        ELSE 1 - (embedding::vector <=> %s::vector)
    END AS vector_score
FROM iris_semantic_search
WHERE 
    embedding IS NOT NULL
    AND NOT embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
    {doc_filter}
ORDER BY vector_score DESC NULLS LAST
LIMIT %s;
"""

print("Vector Search Fix Options:")
print("=" * 60)
print("\n1. IMMEDIATE FIX - Update the subagent.py query:")
print("-" * 40)
print(FIXED_VECTOR_SEARCH_SQL)
print("\n2. DATABASE FUNCTION - Create a validation function:")
print("-" * 40)
print(CREATE_VALIDATION_FUNCTION)
print("\n3. IDENTIFY PROBLEMS - Find invalid vectors:")
print("-" * 40)
print(IDENTIFY_INVALID_VECTORS)
print("\n4. CLEAN DATA - Remove invalid vectors:")
print("-" * 40)
print(NULLIFY_INVALID_VECTORS)
print("\n5. SAFE SEARCH - Handle NULLs gracefully:")
print("-" * 40)
print(SAFE_VECTOR_SEARCH_SQL)