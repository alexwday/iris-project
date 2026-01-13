-- =============================================================================
-- Migration: 003_add_file_hash_column
-- =============================================================================
-- Adds file_hash column to iris_document_metadata for change detection.
-- This allows the doc_refresh pipeline to detect file changes by comparing
-- SHA-256 hashes instead of just relying on file existence.
-- =============================================================================

-- Add file_hash column if it doesn't exist
ALTER TABLE iris_document_metadata
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

-- Optional: Add index if you frequently query by hash
-- CREATE INDEX IF NOT EXISTS idx_doc_metadata_file_hash
--     ON iris_document_metadata (file_hash);
