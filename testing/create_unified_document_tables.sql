-- =============================================================================
-- UNIFIED DOCUMENT TABLES FOR CASCADING RETRIEVAL ARCHITECTURE
-- =============================================================================
-- Part of IRIS Enhancement: Universal Cascading Retrieval Architecture
--
-- These tables consolidate document metadata and chunks from:
--   - apg_catalog (internal document metadata)
--   - apg_content (internal document sections)
--   - iris_semantic_search (external textbook chunks)
--
-- New Architecture:
--   Stage 1 (Metadata Subagent): Query iris_document_metadata + top chunks
--   Stage 2 (File Research): Deep dive into iris_document_chunks
--
-- Usage:
--   psql -p 34532 -d maven-finance -f create_unified_document_tables.sql
--
-- Prerequisites:
--   - pgvector extension installed
--   - iris_database_registry table exists (Stage 1)
-- =============================================================================

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 1. IRIS_DOCUMENT_METADATA - Document-level metadata with summary embeddings
-- =============================================================================
-- Each row represents one document/file in the system.
-- Contains document summary and embedding for Stage 1 metadata search.

DROP TABLE IF EXISTS iris_document_chunks CASCADE;
DROP TABLE IF EXISTS iris_document_metadata CASCADE;

CREATE TABLE iris_document_metadata (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Database association
    db_source VARCHAR(100) NOT NULL,

    -- Document identification
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),  -- e.g., 'policy', 'standard', 'memo', 'textbook'

    -- Document summary for Stage 1 metadata search
    document_summary TEXT NOT NULL,
    condensed_summary TEXT,  -- Short summary (~50 words) for decision phase
    summary_embedding HALFVEC(3072),

    -- Document metadata
    page_count INTEGER,
    chapter_count INTEGER,
    section_count INTEGER,

    -- File information
    file_name VARCHAR(500),
    file_path TEXT,
    file_size BIGINT,
    file_type VARCHAR(50),

    -- Usage/description (from apg_catalog)
    document_description TEXT,
    document_usage TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint (optional, requires iris_database_registry)
    CONSTRAINT fk_doc_metadata_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE,

    -- Unique constraint on db_source + document_name
    CONSTRAINT uq_doc_metadata_source_name UNIQUE (db_source, document_name)
);

-- Indexes for common query patterns
CREATE INDEX idx_doc_metadata_db_source ON iris_document_metadata(db_source);
CREATE INDEX idx_doc_metadata_doc_name ON iris_document_metadata(document_name);

-- Vector index for summary embedding similarity search
-- Using IVFFlat for approximate nearest neighbor search
-- Note: For production with >10k documents, consider HNSW index
CREATE INDEX idx_doc_metadata_summary_embedding ON iris_document_metadata
    USING ivfflat (summary_embedding halfvec_cosine_ops)
    WITH (lists = 10);

COMMENT ON TABLE iris_document_metadata IS
    'Document-level metadata for Stage 1 cascading retrieval. Each row = one document.';

COMMENT ON COLUMN iris_document_metadata.summary_embedding IS
    'Embedding of document_summary for semantic similarity search in Stage 1.';

-- =============================================================================
-- 2. IRIS_DOCUMENT_CHUNKS - Chunk-level content with embeddings
-- =============================================================================
-- Each row represents one chunk (section/paragraph) within a document.
-- Used for Stage 2 file research and for fetching top chunk per file in Stage 1.

CREATE TABLE iris_document_chunks (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Document association
    document_id UUID NOT NULL,
    db_source VARCHAR(100) NOT NULL,

    -- Chunk identification and ordering
    chunk_number INTEGER NOT NULL,

    -- Hierarchical position (chapter > section > chunk)
    chapter_number INTEGER,
    chapter_name VARCHAR(500),
    section_number INTEGER,
    section_name VARCHAR(500),

    -- Simplified hierarchy string (e.g., "Ch3.S2" or "3.2.1")
    chapter_section_hierarchy VARCHAR(100),

    -- Content
    chunk_content TEXT NOT NULL,
    chunk_summary TEXT,  -- Optional summary of this chunk
    chunk_embedding HALFVEC(3072),

    -- Page references (for PDF citations)
    page_number INTEGER,            -- PDF page number (for navigation)
    page_reference VARCHAR(50),     -- Publisher page reference (for display)
    page_start INTEGER,             -- Start page if chunk spans pages
    page_end INTEGER,               -- End page if chunk spans pages

    -- File information (denormalized for query performance)
    file_name VARCHAR(500),
    source_filename VARCHAR(500),   -- Original document name before processing

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_chunks_document_id FOREIGN KEY (document_id)
        REFERENCES iris_document_metadata(id) ON DELETE CASCADE,
    CONSTRAINT fk_chunks_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE
);

-- Indexes for common query patterns
CREATE INDEX idx_chunks_document_id ON iris_document_chunks(document_id);
CREATE INDEX idx_chunks_db_source ON iris_document_chunks(db_source);
CREATE INDEX idx_chunks_page_number ON iris_document_chunks(page_number);
CREATE INDEX idx_chunks_chunk_number ON iris_document_chunks(document_id, chunk_number);

-- Vector index for chunk embedding similarity search
CREATE INDEX idx_chunks_embedding ON iris_document_chunks
    USING ivfflat (chunk_embedding halfvec_cosine_ops)
    WITH (lists = 50);

-- Composite index for filtering + sorting in Stage 2
CREATE INDEX idx_chunks_doc_id_chunk_num ON iris_document_chunks(document_id, chunk_number);

COMMENT ON TABLE iris_document_chunks IS
    'Chunk-level content for Stage 2 file research. Each row = one section/paragraph.';

COMMENT ON COLUMN iris_document_chunks.chunk_embedding IS
    'Embedding of chunk_content for semantic similarity search within documents.';

COMMENT ON COLUMN iris_document_chunks.page_reference IS
    'Publisher page reference (displayed in citations), distinct from PDF page_number.';

-- =============================================================================
-- 3. HELPER VIEW - Document with chunk count
-- =============================================================================
-- Convenient view for Stage 1 queries that need document + chunk counts

CREATE OR REPLACE VIEW v_document_with_chunks AS
SELECT
    m.id,
    m.db_source,
    m.document_name,
    m.document_type,
    m.document_summary,
    m.condensed_summary,
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

COMMENT ON VIEW v_document_with_chunks IS
    'Document metadata with aggregated chunk statistics for Stage 1 queries.';

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- Show created tables
SELECT
    table_name,
    (SELECT count(*) FROM information_schema.columns c WHERE c.table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('iris_document_metadata', 'iris_document_chunks')
ORDER BY table_name;

-- Show indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('iris_document_metadata', 'iris_document_chunks')
ORDER BY tablename, indexname;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'UNIFIED DOCUMENT TABLES CREATED';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - iris_document_metadata (document-level, Stage 1)';
    RAISE NOTICE '  - iris_document_chunks (chunk-level, Stage 2)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - v_document_with_chunks (documents + chunk stats)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next step:';
    RAISE NOTICE '  Run populate_unified_tables.py to migrate data';
    RAISE NOTICE '==============================================';
END $$;
