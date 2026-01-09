-- =============================================================================
-- IRIS Test Tables for DocBench Evaluation
--
-- These tables mirror the production tables but are completely separate.
-- Used for validating RAG retrieval and synthesis against DocBench benchmark.
--
-- To set up:   psql -f create_test_tables.sql
-- To tear down: psql -f drop_test_tables.sql
-- =============================================================================

-- Ensure pgvector extension exists
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Test Database Registry
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_test_database_registry (
    db_source            VARCHAR(100) PRIMARY KEY,
    db_name              VARCHAR(255) NOT NULL,
    db_summary           TEXT NOT NULL,
    db_description       TEXT NOT NULL,
    research_config      JSONB NOT NULL DEFAULT '{
        "batch_size": 50,
        "max_parallel_files": 5,
        "max_selected_files": 10,
        "max_chunks_per_file": 20,
        "top_chunks_in_metadata": 1,
        "page_threshold_for_full_content": 150
    }'::jsonb,
    search_modes         TEXT[] NOT NULL DEFAULT ARRAY['catalog', 'semantic'],
    catalog_config       JSONB,
    semantic_config      JSONB,
    metadata_config      JSONB,
    sample_questions     JSONB,
    enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    ad_groups            TEXT[],
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_test_db_registry_enabled ON iris_test_database_registry(enabled);

-- =============================================================================
-- Test Document Metadata
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_test_document_metadata (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_source            VARCHAR(100) NOT NULL REFERENCES iris_test_database_registry(db_source) ON DELETE CASCADE,
    document_name        VARCHAR(500) NOT NULL,
    document_type        VARCHAR(100),
    document_summary     TEXT NOT NULL,
    summary_embedding    HALFVEC(3072),
    page_count           INTEGER,
    chapter_count        INTEGER,
    section_count        INTEGER,
    file_name            VARCHAR(500),
    file_path            TEXT,
    file_size            BIGINT,
    file_type            VARCHAR(50),
    document_description TEXT,
    document_usage       TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    condensed_summary    TEXT,
    file_hash            VARCHAR(64),          -- SHA256 hash for change detection
    UNIQUE(db_source, document_name)
);

CREATE INDEX IF NOT EXISTS idx_test_doc_metadata_db_source ON iris_test_document_metadata(db_source);
CREATE INDEX IF NOT EXISTS idx_test_doc_metadata_doc_name ON iris_test_document_metadata(document_name);

-- =============================================================================
-- Test Document Chunks
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_test_document_chunks (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id               UUID NOT NULL REFERENCES iris_test_document_metadata(id) ON DELETE CASCADE,
    db_source                 VARCHAR(100) NOT NULL REFERENCES iris_test_database_registry(db_source) ON DELETE CASCADE,
    chunk_number              INTEGER NOT NULL,
    chapter_number            INTEGER,
    chapter_name              VARCHAR(500),
    section_number            INTEGER,
    section_name              VARCHAR(500),
    chapter_section_hierarchy VARCHAR(100),
    chunk_content             TEXT NOT NULL,
    chunk_summary             TEXT,
    chunk_embedding           HALFVEC(3072),
    page_number               INTEGER,
    page_reference            VARCHAR(50),
    page_start                INTEGER,
    page_end                  INTEGER,
    file_name                 VARCHAR(500),
    source_filename           VARCHAR(500),
    created_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_test_chunks_db_source ON iris_test_document_chunks(db_source);
CREATE INDEX IF NOT EXISTS idx_test_chunks_document_id ON iris_test_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_test_chunks_doc_id_chunk_num ON iris_test_document_chunks(document_id, chunk_number);

-- =============================================================================
-- Test QA Pairs (DocBench validated question-answer pairs)
-- This table stores the benchmark QA pairs for evaluation
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_test_qa_pairs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_source            VARCHAR(100) NOT NULL REFERENCES iris_test_database_registry(db_source) ON DELETE CASCADE,
    document_name        VARCHAR(500) NOT NULL,
    question_id          VARCHAR(100) NOT NULL,
    question             TEXT NOT NULL,
    question_type        VARCHAR(50),          -- text-only, multimodal, meta-data, unanswerable
    gold_answer          TEXT NOT NULL,
    evidence_text        TEXT,                 -- Source passage that contains the answer
    evidence_page        INTEGER,              -- Page number where evidence is found
    is_answerable        BOOLEAN DEFAULT TRUE,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(db_source, question_id)
);

CREATE INDEX IF NOT EXISTS idx_test_qa_pairs_db_source ON iris_test_qa_pairs(db_source);
CREATE INDEX IF NOT EXISTS idx_test_qa_pairs_document ON iris_test_qa_pairs(document_name);

-- =============================================================================
-- Add vector indexes after data is loaded (for better performance)
-- Run these AFTER populating the tables:
--
-- CREATE INDEX idx_test_doc_metadata_embedding
--     ON iris_test_document_metadata
--     USING ivfflat (summary_embedding halfvec_cosine_ops) WITH (lists = 10);
--
-- CREATE INDEX idx_test_chunks_embedding
--     ON iris_test_document_chunks
--     USING ivfflat (chunk_embedding halfvec_cosine_ops) WITH (lists = 50);
-- =============================================================================

-- Confirmation
SELECT 'Test tables created successfully' AS status;
