-- Create process_monitor_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS process_monitor_logs (
    -- Core Fields --
    log_id BIGSERIAL PRIMARY KEY,                         -- Auto-incrementing unique ID for each log entry
    run_uuid UUID NOT NULL,                               -- Unique ID generated for each complete model invocation/run
    model_name VARCHAR(100) NOT NULL,                     -- Identifier for the model (e.g., 'iris', 'model_b')
    stage_name VARCHAR(100) NOT NULL,                     -- Name of the specific process stage (e.g., 'SSL_Setup', 'Router_Processing')
    stage_start_time TIMESTAMPTZ NOT NULL,                 -- Timestamp when the stage began
    stage_end_time TIMESTAMPTZ,                            -- Timestamp when the stage ended
    duration_ms INT,                                       -- Duration of the stage in milliseconds (calculated: end_time - start_time)
    llm_calls JSONB,                                       -- JSON array storing details for LLM calls within this stage
    total_tokens INT,                                      -- Sum of total tokens from all llm_calls in this stage (calculated)
    total_cost DECIMAL(12, 6),                             -- Sum of costs from all llm_calls in this stage (calculated)
    status VARCHAR(255),                                   -- Outcome/Status of the stage (e.g., 'Success', 'Failure', 'Clarification')
    decision_details TEXT,                                -- Text field for specific outputs or decisions (e.g., Router's chosen agent)
    error_message TEXT,                                   -- Detailed error message if the stage failed
    log_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,   -- Timestamp when this specific log row was created

    -- Optional Extra Fields for Future Use --
    user_id VARCHAR(255),                                 -- Optional: Identifier for the user initiating the request (if applicable)
    environment VARCHAR(50),                              -- Optional: Environment identifier (e.g., 'production', 'staging', 'development')
    custom_metadata JSONB,                                -- Optional: Flexible JSONB field for any other structured metadata
    notes TEXT                                             -- Optional: Free-form text field for additional notes or context
);

-- Comments for clarity --
COMMENT ON COLUMN process_monitor_logs.llm_calls IS 'JSON array storing details for LLM calls: [{"model": str, "input_tokens": int, "output_tokens": int, "cost": float, "response_time_ms": int}]';
COMMENT ON COLUMN process_monitor_logs.custom_metadata IS 'Flexible JSONB field for any other structured metadata specific to the invocation or environment.';