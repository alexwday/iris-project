-- =============================================================================
-- LOCAL IRIS DATABASE SETUP
-- =============================================================================
-- Run this script to set up local PostgreSQL for IRIS testing.
--
-- Usage:
--   psql -p 34532 -d maven-finance -f setup_local_db.sql
--
-- Prerequisites:
--   - PostgreSQL running on port 34532
--   - Database 'maven-finance' exists
--   - pgvector extension installed (brew install pgvector)
-- =============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is loaded
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- =============================================================================
-- 1. APG_CATALOG TABLE (Document Metadata)
-- =============================================================================
-- Drop and recreate to ensure clean schema
DROP TABLE IF EXISTS apg_catalog CASCADE;

CREATE TABLE apg_catalog (
    -- SYSTEM fields
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- DOCUMENT identification fields
    document_source VARCHAR(100) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    document_name VARCHAR(255) NOT NULL,

    -- SCOPE fields
    document_description TEXT,
    document_usage TEXT,

    -- EMBEDDING fields
    document_usage_embedding vector(2000),
    document_description_embedding vector(2000),

    -- REFRESH metadata fields
    date_created TIMESTAMP WITH TIME ZONE,
    date_last_modified TIMESTAMP WITH TIME ZONE,
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    file_size BIGINT,
    file_path VARCHAR(1000),
    file_link VARCHAR(1000)
);

-- Create indexes for common queries
CREATE INDEX idx_apg_catalog_source ON apg_catalog(document_source);
CREATE INDEX idx_apg_catalog_name ON apg_catalog(document_name);

-- =============================================================================
-- 2. APG_CONTENT TABLE (Document Content/Sections)
-- =============================================================================
DROP TABLE IF EXISTS apg_content CASCADE;

CREATE TABLE apg_content (
    -- SYSTEM fields
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- DOCUMENT reference fields
    document_source VARCHAR(100) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    document_name VARCHAR(255) NOT NULL,

    -- CONTENT fields
    section_id INTEGER NOT NULL,
    section_name VARCHAR(500),
    section_summary TEXT,
    section_content TEXT NOT NULL,
    page_number INTEGER
);

-- Create indexes for common queries
CREATE INDEX idx_apg_content_source ON apg_content(document_source);
CREATE INDEX idx_apg_content_docname ON apg_content(document_name);
CREATE INDEX idx_apg_content_source_name ON apg_content(document_source, document_name);

-- =============================================================================
-- 3. IRIS_SEMANTIC_SEARCH TABLE (External Textbook Content)
-- =============================================================================
DROP TABLE IF EXISTS iris_semantic_search CASCADE;

CREATE TABLE iris_semantic_search (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Document Fields
    document_id VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath TEXT,
    source_filename VARCHAR(255),

    -- Chapter Fields
    chapter_number INTEGER,
    chapter_name VARCHAR(500),
    chapter_summary TEXT,
    chapter_page_count INTEGER,

    -- Section Fields
    section_number INTEGER,
    section_summary TEXT,
    section_start_page INTEGER,
    section_end_page INTEGER,
    section_page_count INTEGER,
    section_start_reference VARCHAR(50),
    section_end_reference VARCHAR(50),

    -- Chunk Fields
    chunk_number INTEGER NOT NULL,
    chunk_content TEXT NOT NULL,
    chunk_start_page INTEGER,
    chunk_end_page INTEGER,
    chunk_start_reference VARCHAR(50),
    chunk_end_reference VARCHAR(50),

    -- Embedding Field
    embedding VECTOR(2000),

    -- Extra Fields
    extra1 TEXT,
    extra2 TEXT,
    extra3 TEXT,

    -- System Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for semantic search
CREATE INDEX idx_semantic_search_doc_id ON iris_semantic_search(document_id);
CREATE INDEX idx_semantic_search_chapter ON iris_semantic_search(chapter_number);

-- =============================================================================
-- 4. IRIS_DATABASE_REGISTRY TABLE (Database Configuration)
-- =============================================================================
-- Central registry for all research databases with configurations
-- Part of IRIS Enhancement: Universal Cascading Retrieval Architecture

DROP TABLE IF EXISTS iris_database_registry CASCADE;

CREATE TABLE iris_database_registry (
    -- Core identification
    db_source VARCHAR(100) PRIMARY KEY,
    db_name VARCHAR(255) NOT NULL,
    db_summary TEXT NOT NULL,
    db_description TEXT NOT NULL,

    -- Research configuration (unified JSONB for new cascading architecture)
    -- Contains: batch_size, max_selected_files, max_parallel_files,
    --           top_chunks_in_metadata, page_threshold_for_full_content, max_chunks_per_file
    research_config JSONB NOT NULL DEFAULT '{
        "batch_size": 10,
        "max_selected_files": 10,
        "max_parallel_batches": 5,
        "max_parallel_files": 5,
        "top_chunks_in_metadata": 1,
        "page_threshold_for_full_content": 150,
        "max_chunks_per_file": 20
    }'::jsonb,

    -- Legacy search configuration (kept for backward compatibility during migration)
    search_modes TEXT[] NOT NULL DEFAULT ARRAY['catalog', 'semantic'],
    catalog_config JSONB,
    semantic_config JSONB,
    metadata_config JSONB,

    -- Access control and metadata
    sample_questions JSONB,
    enabled BOOLEAN NOT NULL DEFAULT true,
    ad_groups TEXT[],

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX idx_iris_db_registry_enabled ON iris_database_registry(enabled);
CREATE INDEX idx_iris_db_registry_ad_groups ON iris_database_registry USING GIN(ad_groups);
CREATE INDEX idx_iris_db_registry_search_modes ON iris_database_registry USING GIN(search_modes);

-- =============================================================================
-- 5. IRIS_DOCUMENT_METADATA TABLE (Unified Document Metadata)
-- =============================================================================
-- Part of IRIS Enhancement: Universal Cascading Retrieval Architecture
-- Each row represents one document for Stage 1 metadata search

DROP TABLE IF EXISTS iris_document_chunks CASCADE;
DROP TABLE IF EXISTS iris_document_metadata CASCADE;

CREATE TABLE iris_document_metadata (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Database association
    db_source VARCHAR(100) NOT NULL,

    -- Document identification
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),

    -- Document summary for Stage 1 metadata search
    document_summary TEXT NOT NULL,
    summary_embedding VECTOR(2000),

    -- Document metadata
    page_count INTEGER,
    chapter_count INTEGER,
    section_count INTEGER,

    -- File information
    file_name VARCHAR(500),
    file_path TEXT,
    file_size BIGINT,
    file_type VARCHAR(50),

    -- Usage/description
    document_description TEXT,
    document_usage TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT fk_doc_metadata_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE,
    CONSTRAINT uq_doc_metadata_source_name UNIQUE (db_source, document_name)
);

CREATE INDEX idx_doc_metadata_db_source ON iris_document_metadata(db_source);
CREATE INDEX idx_doc_metadata_doc_name ON iris_document_metadata(document_name);
CREATE INDEX idx_doc_metadata_summary_embedding ON iris_document_metadata
    USING ivfflat (summary_embedding vector_cosine_ops) WITH (lists = 10);

-- =============================================================================
-- 6. IRIS_DOCUMENT_CHUNKS TABLE (Unified Chunk Content)
-- =============================================================================
-- Each row represents one chunk/section for Stage 2 file research

CREATE TABLE iris_document_chunks (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Document association
    document_id UUID NOT NULL,
    db_source VARCHAR(100) NOT NULL,

    -- Chunk identification
    chunk_number INTEGER NOT NULL,

    -- Hierarchical position
    chapter_number INTEGER,
    chapter_name VARCHAR(500),
    section_number INTEGER,
    section_name VARCHAR(500),
    chapter_section_hierarchy VARCHAR(100),

    -- Content
    chunk_content TEXT NOT NULL,
    chunk_summary TEXT,
    chunk_embedding VECTOR(2000),

    -- Page references
    page_number INTEGER,
    page_reference VARCHAR(50),
    page_start INTEGER,
    page_end INTEGER,

    -- File information (denormalized)
    file_name VARCHAR(500),
    source_filename VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT fk_chunks_document_id FOREIGN KEY (document_id)
        REFERENCES iris_document_metadata(id) ON DELETE CASCADE,
    CONSTRAINT fk_chunks_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE
);

CREATE INDEX idx_chunks_document_id ON iris_document_chunks(document_id);
CREATE INDEX idx_chunks_db_source ON iris_document_chunks(db_source);
CREATE INDEX idx_chunks_page_number ON iris_document_chunks(page_number);
CREATE INDEX idx_chunks_doc_id_chunk_num ON iris_document_chunks(document_id, chunk_number);
CREATE INDEX idx_chunks_embedding ON iris_document_chunks
    USING ivfflat (chunk_embedding vector_cosine_ops) WITH (lists = 50);

-- =============================================================================
-- 7. HELPER VIEW - Document with chunk count
-- =============================================================================
CREATE OR REPLACE VIEW v_document_with_chunks AS
SELECT
    m.id,
    m.db_source,
    m.document_name,
    m.document_type,
    m.document_summary,
    m.summary_embedding,
    m.page_count,
    m.file_name,
    m.document_description,
    m.document_usage,
    COUNT(c.id) as chunk_count
FROM iris_document_metadata m
LEFT JOIN iris_document_chunks c ON m.id = c.document_id
GROUP BY m.id;

-- =============================================================================
-- 8. PROCESS_MONITOR_LOGS TABLE (for finance-dev database)
-- =============================================================================
-- Note: Run this part against 'finance-dev' database if needed
-- CREATE TABLE IF NOT EXISTS process_monitor_logs ( ... );

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- Show created tables
SELECT table_name,
       (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('apg_catalog', 'apg_content', 'iris_semantic_search', 'iris_database_registry',
                   'iris_document_metadata', 'iris_document_chunks')
ORDER BY table_name;

-- Show vector extension status
SELECT 'pgvector extension' as component,
       CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
            THEN 'INSTALLED' ELSE 'MISSING' END as status;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'LOCAL DATABASE SETUP COMPLETE';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Legacy Tables (current architecture):';
    RAISE NOTICE '  - apg_catalog (document metadata)';
    RAISE NOTICE '  - apg_content (document sections)';
    RAISE NOTICE '  - iris_semantic_search (external textbooks)';
    RAISE NOTICE '';
    RAISE NOTICE 'New Tables (cascading retrieval architecture):';
    RAISE NOTICE '  - iris_database_registry (database configuration)';
    RAISE NOTICE '  - iris_document_metadata (unified document metadata)';
    RAISE NOTICE '  - iris_document_chunks (unified chunk content)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views:';
    RAISE NOTICE '  - v_document_with_chunks (documents + chunk stats)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run populate_local_db.py to add sample document data';
    RAISE NOTICE '  2. Run populate_database_registry.py to seed database configs';
    RAISE NOTICE '  3. Run populate_unified_tables.py to migrate to new tables';
    RAISE NOTICE '==============================================';
END $$;
