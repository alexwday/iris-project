-- =============================================================================
-- Table: iris_document_metadata
-- =============================================================================
--
-- This file defines the schema for the iris_document_metadata table.
-- Generated from PostgreSQL database: maven-finance
-- =============================================================================

CREATE TABLE IF NOT EXISTS iris_document_metadata (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    db_source VARCHAR(100) NOT NULL,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),
    document_summary TEXT NOT NULL,
    summary_embedding HALFVEC(3072),
    page_count INTEGER,
    primary_section_count INTEGER,
    subsection_count INTEGER,
    file_name VARCHAR(500),
    file_path TEXT,
    file_size BIGINT,
    file_type VARCHAR(50),
    document_description TEXT,
    document_usage TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    file_hash VARCHAR(64),
    CONSTRAINT iris_document_metadata_pkey PRIMARY KEY (id),
    CONSTRAINT fk_doc_metadata_db_source FOREIGN KEY (db_source)
        REFERENCES iris_database_registry(db_source) ON DELETE CASCADE
);

-- Unique Constraints
ALTER TABLE iris_document_metadata
    ADD CONSTRAINT uq_doc_metadata_source_name UNIQUE (db_source, document_name);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_doc_metadata_db_source ON iris_document_metadata USING btree (db_source);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_doc_name ON iris_document_metadata USING btree (document_name);
CREATE INDEX IF NOT EXISTS idx_doc_metadata_summary_embedding ON iris_document_metadata USING ivfflat (summary_embedding halfvec_cosine_ops) WITH (lists='10');

-- =============================================================================
-- Column Descriptions
-- =============================================================================
-- id: Unique identifier for the document
-- db_source: Reference to iris_database_registry.db_source
-- document_name: Name of the document
-- document_type: Type/category of the document
-- document_summary: Summary of document contents
-- summary_embedding: Vector embedding of the document summary (3072 dimensions)
-- page_count: Number of pages in the document
-- primary_section_count: Number of primary sections
-- subsection_count: Number of subsections
-- file_name: Original filename
-- file_path: Path to the file
-- file_size: Size of the file in bytes
-- file_type: File extension/type
-- document_description: Detailed description
-- document_usage: Usage instructions or notes
-- file_hash: MD5 hash for change detection
