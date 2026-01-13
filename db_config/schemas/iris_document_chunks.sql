-- =============================================================================
-- Table: iris_document_chunks
-- =============================================================================
--
-- This file defines the schema for the iris_document_chunks table.
-- Generated from PostgreSQL database: maven-finance
-- =============================================================================

CREATE TABLE IF NOT EXISTS iris_document_chunks (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    db_source VARCHAR(100) NOT NULL,
    chunk_number INTEGER NOT NULL,
    primary_section_number INTEGER,
    primary_section_name VARCHAR(500),
    subsection_number INTEGER,
    subsection_name VARCHAR(500),
    hierarchy_path VARCHAR(1000),
    chunk_content TEXT NOT NULL,
    chunk_embedding HALFVEC(3072),
    page_number INTEGER,
    file_name VARCHAR(500),
    source_filename VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    primary_section_page_count INTEGER,
    subsection_page_count INTEGER,
    CONSTRAINT iris_document_chunks_pkey PRIMARY KEY (id),
    CONSTRAINT fk_chunks_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE,
    CONSTRAINT fk_chunks_document_id FOREIGN KEY (document_id)
        REFERENCES iris_document_metadata(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON iris_document_chunks USING btree (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_db_source ON iris_document_chunks USING btree (db_source);
CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON iris_document_chunks USING btree (page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id_chunk_num ON iris_document_chunks USING btree (document_id, chunk_number);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON iris_document_chunks USING ivfflat (chunk_embedding halfvec_cosine_ops) WITH (lists='50');

-- =============================================================================
-- Column Descriptions
-- =============================================================================
-- id: Unique identifier for the chunk
-- document_id: Reference to iris_document_metadata.id
-- db_source: Reference to iris_database_registry.db_source
-- chunk_number: Sequential chunk number within the document
-- primary_section_number: Primary section number
-- primary_section_name: Name of the primary section
-- subsection_number: Subsection number
-- subsection_name: Name of the subsection
-- hierarchy_path: Full path in document hierarchy
-- chunk_content: Text content of the chunk
-- chunk_embedding: Vector embedding of the chunk content (3072 dimensions)
-- page_number: Page number in the source document
-- file_name: Name of the source file
-- source_filename: Original source filename
-- primary_section_page_count: Number of pages in the primary section
-- subsection_page_count: Number of pages in the subsection
