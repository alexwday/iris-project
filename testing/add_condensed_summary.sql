-- =============================================================================
-- ADD CONDENSED_SUMMARY COLUMN TO IRIS_DOCUMENT_METADATA
-- =============================================================================
-- Migration for batching architecture support.
-- Condensed summaries (50 words max) are used for decision phase when
-- document count >= 100.
--
-- Usage:
--   psql -p 34532 -d maven-finance -f add_condensed_summary.sql
-- =============================================================================

-- Add the condensed_summary column
ALTER TABLE iris_document_metadata
ADD COLUMN IF NOT EXISTS condensed_summary TEXT;

COMMENT ON COLUMN iris_document_metadata.condensed_summary IS
    'Short 1-2 sentence summary (~50 words) for decision phase when document count is high (>=100). Used in batching architecture to reduce token usage during research mode decision.';

-- Update the view to include condensed_summary
-- Must drop and recreate because we're adding a column in the middle
DROP VIEW IF EXISTS v_document_with_chunks;
CREATE VIEW v_document_with_chunks AS
SELECT
    m.id,
    m.db_source,
    m.document_name,
    m.document_type,
    m.document_summary,
    m.condensed_summary,  -- NEW
    m.summary_embedding,
    m.page_count,
    m.file_name,
    m.document_description,
    m.document_usage,
    COUNT(c.id) as chunk_count,
    MIN(c.chunk_number) as first_chunk_num,
    MAX(c.chunk_number) as last_chunk_num
FROM iris_document_metadata m
LEFT JOIN iris_document_chunks c ON m.id = c.document_id
GROUP BY m.id;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'iris_document_metadata'
AND column_name = 'condensed_summary';

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'CONDENSED_SUMMARY COLUMN ADDED';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Column: iris_document_metadata.condensed_summary';
    RAISE NOTICE 'Purpose: Short summaries for decision phase';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Populate condensed summaries for existing docs';
    RAISE NOTICE '  2. Update document processing to generate condensed summaries';
    RAISE NOTICE '==============================================';
END $$;
