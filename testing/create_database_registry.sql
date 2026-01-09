-- Create iris_database_registry table
-- This table stores metadata and configuration for all research databases
--
-- Part of IRIS Enhancement: Universal Cascading Retrieval Architecture
-- See notes/STAGED_IMPLEMENTATION_PLAN.md for context

CREATE TABLE IF NOT EXISTS iris_database_registry (
    -- Core identification
    db_source VARCHAR(100) PRIMARY KEY,
    db_name VARCHAR(255) NOT NULL,
    db_summary TEXT NOT NULL,
    db_description TEXT NOT NULL,

    -- Research configuration for cascading retrieval
    -- Metadata path: fetch docs → batch (batch_size) → synthesize → combine
    -- Deep research path: fetch docs → batch → select files (max_selected_files) → file research → combine
    research_config JSONB NOT NULL DEFAULT '{
        "batch_size": 10,
        "max_selected_files": 20,
        "top_chunks_in_metadata": 3,
        "max_parallel_batches": 5,
        "max_parallel_files": 5,
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
CREATE INDEX IF NOT EXISTS idx_iris_db_registry_enabled
    ON iris_database_registry(enabled);

CREATE INDEX IF NOT EXISTS idx_iris_db_registry_ad_groups
    ON iris_database_registry USING GIN(ad_groups);

CREATE INDEX IF NOT EXISTS idx_iris_db_registry_search_modes
    ON iris_database_registry USING GIN(search_modes);

-- Add comment to table
COMMENT ON TABLE iris_database_registry IS 'Central registry for all research databases with their descriptions, search configurations, and access controls. Part of the universal cascading retrieval architecture.';

-- Add comments to key columns
COMMENT ON COLUMN iris_database_registry.db_source IS 'Unique database identifier (e.g., internal_capm, external_ey)';
COMMENT ON COLUMN iris_database_registry.db_summary IS 'Brief description for context/awareness - used by agents for general database knowledge';
COMMENT ON COLUMN iris_database_registry.db_description IS 'Detailed guidance for planning/selection with tier, strategy, and query tips';
COMMENT ON COLUMN iris_database_registry.research_config IS 'JSONB config for cascading retrieval. Keys: batch_size (docs per batch), max_selected_files (cap for deep research), top_chunks_in_metadata (chunks per doc in index), max_parallel_files, page_threshold_for_full_content, max_chunks_per_file';
COMMENT ON COLUMN iris_database_registry.catalog_config IS 'Legacy: JSONB config for catalog search (max_files, max_file_size_mb, max_depth_pages, allow_full_file)';
COMMENT ON COLUMN iris_database_registry.semantic_config IS 'Legacy: JSONB config for semantic search (top_k, max_chunks, min_similarity, expand_sections)';
COMMENT ON COLUMN iris_database_registry.metadata_config IS 'Legacy: JSONB config for metadata summary search (top_k, max_files, max_tokens)';
COMMENT ON COLUMN iris_database_registry.ad_groups IS 'Array of Active Directory groups that can access this database';
