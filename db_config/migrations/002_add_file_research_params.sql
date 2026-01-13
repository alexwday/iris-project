-- Migration: Add max_parallel_files and max_chunks_per_file to registry

-- Step 1: Add new columns
ALTER TABLE iris_database_registry
ADD COLUMN IF NOT EXISTS max_parallel_files INTEGER NOT NULL DEFAULT 5,
ADD COLUMN IF NOT EXISTS max_chunks_per_file INTEGER NOT NULL DEFAULT 20;

-- Verify
SELECT db_source, max_parallel_files, max_chunks_per_file 
FROM iris_database_registry 
ORDER BY db_source LIMIT 5;
