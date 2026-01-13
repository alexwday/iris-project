-- Migration: Convert research_config JSONB to individual columns
-- This migration:
-- 1. Adds new individual columns for research configuration
-- 2. Migrates existing data from research_config JSONB
-- 3. Drops the research_config column

-- Step 1: Add new columns (nullable first for migration)
ALTER TABLE iris_database_registry
ADD COLUMN IF NOT EXISTS batch_size INTEGER,
ADD COLUMN IF NOT EXISTS max_selected_files INTEGER,
ADD COLUMN IF NOT EXISTS top_chunks_in_catalog_selection INTEGER,
ADD COLUMN IF NOT EXISTS top_chunks_in_metadata_research INTEGER,
ADD COLUMN IF NOT EXISTS page_threshold_for_full_content INTEGER,
ADD COLUMN IF NOT EXISTS enable_db_wide_deep_research BOOLEAN,
ADD COLUMN IF NOT EXISTS metadata_context_fields TEXT[] DEFAULT ARRAY['document_summary'];

-- Step 2: Migrate data from research_config JSONB to individual columns
UPDATE iris_database_registry
SET 
    batch_size = COALESCE((research_config->>'batch_size')::INTEGER, 10),
    max_selected_files = COALESCE((research_config->>'max_selected_files')::INTEGER, 10),
    top_chunks_in_catalog_selection = COALESCE((research_config->>'top_chunks_in_catalog_selection')::INTEGER, 1),
    top_chunks_in_metadata_research = COALESCE((research_config->>'top_chunks_in_metadata_research')::INTEGER, 3),
    page_threshold_for_full_content = COALESCE((research_config->>'page_threshold_for_full_content')::INTEGER, 150),
    enable_db_wide_deep_research = COALESCE((research_config->>'enable_db_wide_deep_research')::BOOLEAN, true),
    metadata_context_fields = ARRAY['document_summary']
WHERE research_config IS NOT NULL;

-- Step 3: Set defaults for any NULL values
UPDATE iris_database_registry
SET 
    batch_size = COALESCE(batch_size, 10),
    max_selected_files = COALESCE(max_selected_files, 10),
    top_chunks_in_catalog_selection = COALESCE(top_chunks_in_catalog_selection, 1),
    top_chunks_in_metadata_research = COALESCE(top_chunks_in_metadata_research, 3),
    page_threshold_for_full_content = COALESCE(page_threshold_for_full_content, 150),
    enable_db_wide_deep_research = COALESCE(enable_db_wide_deep_research, true),
    metadata_context_fields = COALESCE(metadata_context_fields, ARRAY['document_summary']);

-- Step 4: Add NOT NULL constraints
ALTER TABLE iris_database_registry
ALTER COLUMN batch_size SET NOT NULL,
ALTER COLUMN max_selected_files SET NOT NULL,
ALTER COLUMN top_chunks_in_catalog_selection SET NOT NULL,
ALTER COLUMN top_chunks_in_metadata_research SET NOT NULL,
ALTER COLUMN page_threshold_for_full_content SET NOT NULL,
ALTER COLUMN enable_db_wide_deep_research SET NOT NULL,
ALTER COLUMN metadata_context_fields SET NOT NULL;

-- Step 5: Drop the old research_config column
ALTER TABLE iris_database_registry
DROP COLUMN IF EXISTS research_config;
