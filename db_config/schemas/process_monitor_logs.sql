-- =============================================================================
-- Table: process_monitor_logs
-- =============================================================================
--
-- This file defines the schema for the process_monitor_logs table.
-- Generated from PostgreSQL database: maven-finance
-- =============================================================================

-- Create sequence for log_id
CREATE SEQUENCE IF NOT EXISTS process_monitor_logs_log_id_seq;

CREATE TABLE IF NOT EXISTS process_monitor_logs (
    log_id BIGINT NOT NULL DEFAULT nextval('process_monitor_logs_log_id_seq'::regclass),
    run_uuid UUID NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    stage_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    stage_end_time TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    llm_calls JSONB,
    total_tokens INTEGER,
    total_cost NUMERIC(12,6),
    status VARCHAR(255),
    decision_details TEXT,
    error_message TEXT,
    log_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    environment VARCHAR(50),
    custom_metadata JSONB,
    notes TEXT,
    CONSTRAINT process_monitor_logs_pkey PRIMARY KEY (log_id)
);

-- Set sequence ownership
ALTER SEQUENCE process_monitor_logs_log_id_seq OWNED BY process_monitor_logs.log_id;

-- =============================================================================
-- Column Descriptions
-- =============================================================================
-- log_id: Auto-incrementing unique identifier
-- run_uuid: UUID identifying the processing run
-- model_name: Name of the model being monitored
-- stage_name: Name of the processing stage
-- stage_start_time: When the stage started
-- stage_end_time: When the stage ended
-- duration_ms: Duration in milliseconds
-- llm_calls: JSON details of LLM API calls
-- total_tokens: Total tokens used
-- total_cost: Total cost of the operation
-- status: Current status of the stage
-- decision_details: Details about decisions made
-- error_message: Error message if any
-- log_timestamp: When this log entry was created
-- user_id: User who initiated the process
-- environment: Environment (dev, prod, etc.)
-- custom_metadata: Additional metadata as JSON
-- notes: Free-form notes
