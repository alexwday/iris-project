-- SQL script to add new columns to the existing apg_catalog table

-- 1. Add document_usage column for LLM selection/usage
ALTER TABLE apg_catalog ADD COLUMN document_usage TEXT;

-- 2. Add file_link column for URLs or NAS paths
ALTER TABLE apg_catalog ADD COLUMN file_link VARCHAR(1000);

-- Note: After applying these changes, application code that interacts with these tables
-- will need to be updated, particularly in the database subagents.
