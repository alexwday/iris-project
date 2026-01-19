-- =============================================================================
-- Document Refresh Pipeline - Database Tables
--
-- These tables store documents processed by the doc_refresh pipeline.
-- Designed for multi-stage retrieval with section-level and chunk-level search.
--
-- Usage:
--   psql -d maven-finance -f doc_refresh/sql/create_tables.sql
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
-- UUID generation for iris tables
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- Documents Table
-- Stores document metadata and processing information
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    document_id          SERIAL PRIMARY KEY,
    db_source            VARCHAR(100) NOT NULL,
    file_path            TEXT NOT NULL,
    file_name            VARCHAR(500) NOT NULL,
    file_hash            VARCHAR(64) NOT NULL,      -- MD5 for change detection
    file_size            BIGINT,
    page_count           INTEGER NOT NULL,
    structure_type       VARCHAR(50),               -- chapters, sections, topic_based, semantic
    structure_confidence VARCHAR(20),               -- high, medium, low
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(db_source, file_path)
);

CREATE INDEX IF NOT EXISTS idx_docs_db_source ON documents(db_source);
CREATE INDEX IF NOT EXISTS idx_docs_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_docs_file_path ON documents(db_source, file_path);

-- =============================================================================
-- Sections Table
-- Stores hierarchical sections with summaries
-- =============================================================================
CREATE TABLE IF NOT EXISTS sections (
    section_id           SERIAL PRIMARY KEY,
    document_id          INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    parent_section_id    INTEGER REFERENCES sections(section_id) ON DELETE CASCADE,

    -- Hierarchy
    level                INTEGER NOT NULL,          -- 1=chapter/section, 2=subsection, 3=sub-subsection
    sequence_number      INTEGER NOT NULL,          -- Order within document

    -- Identification
    title                VARCHAR(500) NOT NULL,
    section_path         TEXT NOT NULL,             -- "Chapter 3 > Section Title"

    -- Content
    summary              TEXT NOT NULL,             -- Used for LLM chapter selection

    -- Boundaries
    page_start           INTEGER NOT NULL,
    page_end             INTEGER NOT NULL,

    -- Metadata
    inferred             BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sections_doc ON sections(document_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_section_id);
CREATE INDEX IF NOT EXISTS idx_sections_level ON sections(document_id, level);
CREATE INDEX IF NOT EXISTS idx_sections_pages ON sections(document_id, page_start, page_end);

-- =============================================================================
-- Chunks Table
-- Stores page-level chunks with embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id             SERIAL PRIMARY KEY,
    document_id          INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    section_id           INTEGER REFERENCES sections(section_id) ON DELETE SET NULL,

    -- Position
    chunk_number         INTEGER NOT NULL,
    page_number          INTEGER NOT NULL,

    -- Content
    raw_content          TEXT NOT NULL,
    context_prefix       TEXT,                      -- "[Section Path | Page N]" for display

    -- Embedding (of raw_content only)
    chunk_embedding      VECTOR(3072),              -- text-embedding-3-large

    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks(section_id);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(document_id, page_number);

-- =============================================================================
-- Iris Document Metadata (2-table design)
-- Stores document-level metadata and summary embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    db_source VARCHAR(100) NOT NULL,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),
    document_summary TEXT NOT NULL,
    summary_embedding HALFVEC,
    page_count INTEGER,
    primary_section_count INTEGER,
    subsection_count INTEGER,
    file_name VARCHAR(500),
    file_path TEXT,
    file_size BIGINT,
    file_hash VARCHAR(64),
    file_type VARCHAR(50),
    document_description TEXT,
    document_usage TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_metadata_source_name
    ON iris_document_metadata(db_source, document_name);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_db_source
    ON iris_document_metadata(db_source);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_doc_name
    ON iris_document_metadata(document_name);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_summary_embedding
    ON iris_document_metadata
    USING ivfflat (summary_embedding halfvec_cosine_ops) WITH (lists = 10);

-- Add file_hash column if not exists (for existing deployments)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'iris_document_metadata' AND column_name = 'file_hash'
    ) THEN
        ALTER TABLE iris_document_metadata ADD COLUMN file_hash VARCHAR(64);
    END IF;
END $$;

-- =============================================================================
-- Iris Document Chunks (2-table design)
-- Stores chunk-level content with embeddings
-- =============================================================================
CREATE TABLE IF NOT EXISTS iris_document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    db_source VARCHAR(100) NOT NULL,
    chunk_number INTEGER NOT NULL,
    primary_section_number INTEGER,
    primary_section_name VARCHAR(500),
    subsection_number INTEGER,
    subsection_name VARCHAR(500),
    hierarchy_path VARCHAR(1000),
    chunk_content TEXT NOT NULL,
    chunk_embedding HALFVEC,
    page_number INTEGER,
    file_name VARCHAR(500),
    source_filename VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    primary_section_page_count INTEGER,
    subsection_page_count INTEGER
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON iris_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_db_source
    ON iris_document_chunks(db_source);
CREATE INDEX IF NOT EXISTS idx_chunks_page_number
    ON iris_document_chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id_chunk_num
    ON iris_document_chunks(document_id, chunk_number);
CREATE INDEX IF NOT EXISTS idx_iris_chunks_embedding
    ON iris_document_chunks
    USING ivfflat (chunk_embedding halfvec_cosine_ops) WITH (lists = 50);

-- =============================================================================
-- Vector Index
-- Create AFTER loading data for better performance
-- =============================================================================

-- Helper function to create vector indexes (run after data load)
CREATE OR REPLACE FUNCTION create_doc_refresh_vector_indexes()
RETURNS void AS $$
BEGIN
    -- Drop existing indexes if any
    DROP INDEX IF EXISTS idx_chunks_embedding;

    -- Create chunk embedding index
    -- lists = sqrt(num_rows) is a good starting point, adjust based on data size
    EXECUTE 'CREATE INDEX idx_chunks_embedding ON chunks
        USING ivfflat (chunk_embedding vector_cosine_ops) WITH (lists = 100)';

    RAISE NOTICE 'Chunk embedding vector index created successfully';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Trigger for updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_documents_modtime ON documents;
CREATE TRIGGER update_documents_modtime
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- =============================================================================
-- Useful Views
-- =============================================================================

-- View: Document summary with counts
CREATE OR REPLACE VIEW document_summary AS
SELECT
    d.document_id,
    d.db_source,
    d.file_name,
    d.page_count,
    d.structure_type,
    COUNT(DISTINCT s.section_id) AS section_count,
    COUNT(DISTINCT c.chunk_id) AS chunk_count,
    d.created_at,
    d.updated_at
FROM documents d
LEFT JOIN sections s ON d.document_id = s.document_id
LEFT JOIN chunks c ON d.document_id = c.document_id
GROUP BY d.document_id;

-- View: Database source statistics
CREATE OR REPLACE VIEW db_source_stats AS
SELECT
    db_source,
    COUNT(*) AS document_count,
    SUM(page_count) AS total_pages,
    COUNT(DISTINCT structure_type) AS structure_types,
    MIN(created_at) AS first_processed,
    MAX(updated_at) AS last_updated
FROM documents
GROUP BY db_source;

-- Confirmation
SELECT 'Document refresh tables created successfully' AS status;
