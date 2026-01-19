-- =============================================================================
-- Table: iris_database_registry
-- =============================================================================
--
-- This file defines the schema for the iris_database_registry table.
-- Generated from PostgreSQL database: maven-finance
-- =============================================================================

CREATE TABLE IF NOT EXISTS iris_database_registry (
    db_source VARCHAR(100) NOT NULL,
    db_name VARCHAR(255) NOT NULL,
    db_summary TEXT NOT NULL,
    db_description TEXT NOT NULL,
    search_modes TEXT[] NOT NULL DEFAULT ARRAY['catalog'::text, 'semantic'::text],
    catalog_config JSONB,
    semantic_config JSONB,
    metadata_config JSONB,
    sample_questions JSONB,
    enabled BOOLEAN NOT NULL DEFAULT true,
    ad_groups TEXT[],
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    batch_size INTEGER NOT NULL,
    max_selected_files INTEGER NOT NULL,
    top_chunks_in_catalog_selection INTEGER NOT NULL,
    top_chunks_in_metadata_research INTEGER NOT NULL,
    page_threshold_for_full_content INTEGER NOT NULL,
    enable_db_wide_deep_research BOOLEAN NOT NULL,
    metadata_context_fields TEXT[] NOT NULL DEFAULT ARRAY['document_summary'::text],
    max_parallel_files INTEGER NOT NULL DEFAULT 5,
    max_chunks_per_file INTEGER NOT NULL DEFAULT 20,
    max_pages_for_full_context INTEGER NOT NULL DEFAULT 6,
    max_primary_section_page_count INTEGER NOT NULL DEFAULT 6,
    max_subsection_page_count INTEGER NOT NULL DEFAULT 3,
    max_neighbour_chunks INTEGER NOT NULL DEFAULT 2,
    max_gap_fill_pages INTEGER NOT NULL DEFAULT 2,
    CONSTRAINT iris_database_registry_pkey PRIMARY KEY (db_source)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_iris_db_registry_enabled ON iris_database_registry USING btree (enabled);
CREATE INDEX IF NOT EXISTS idx_iris_db_registry_ad_groups ON iris_database_registry USING gin (ad_groups);
CREATE INDEX IF NOT EXISTS idx_iris_db_registry_search_modes ON iris_database_registry USING gin (search_modes);

-- =============================================================================
-- Column Descriptions
-- =============================================================================
-- db_source: Unique identifier for the database source
-- db_name: Display name for the database
-- db_summary: Brief summary of database contents
-- db_description: Detailed description of database contents
-- search_modes: Array of enabled search modes ('catalog', 'semantic')
-- catalog_config: Configuration for catalog-based search
-- semantic_config: Configuration for semantic search
-- metadata_config: Configuration for metadata handling
-- sample_questions: Example questions for this database
-- enabled: Whether this database is active
-- ad_groups: Active Directory groups with access
-- batch_size: Number of documents to process in batch operations
-- max_selected_files: Maximum files to select for research
-- top_chunks_in_catalog_selection: Top chunks to consider in catalog selection
-- top_chunks_in_metadata_research: Top chunks for metadata research
-- page_threshold_for_full_content: Page count threshold for full content retrieval
-- enable_db_wide_deep_research: Enable deep research across entire database
-- metadata_context_fields: Fields to include in document context for LLM
-- max_parallel_files: Maximum files to process in parallel
-- max_chunks_per_file: Maximum chunks per file
-- max_pages_for_full_context: Maximum pages for full context retrieval
-- max_primary_section_page_count: Maximum pages per primary section
-- max_subsection_page_count: Maximum pages per subsection
-- max_neighbour_chunks: Maximum neighboring chunks to include
-- max_gap_fill_pages: Maximum pages to fill gaps between chunks
