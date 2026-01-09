-- =============================================================================
-- Drop all IRIS Test Tables
--
-- WARNING: This will delete all test data!
-- Run this to clean up DocBench test data before production deployment.
-- =============================================================================

DROP TABLE IF EXISTS iris_test_qa_pairs CASCADE;
DROP TABLE IF EXISTS iris_test_document_chunks CASCADE;
DROP TABLE IF EXISTS iris_test_document_metadata CASCADE;
DROP TABLE IF EXISTS iris_test_database_registry CASCADE;

SELECT 'Test tables dropped successfully' AS status;
