-- =============================================================================
-- CREATE PROMPTS TABLE FOR IRIS
-- =============================================================================
-- Stores all agent and subagent prompts for the IRIS system.
-- Prompts include system_prompt, user_prompt, tool definitions, and global refs.
--
-- Usage:
--   psql -p 34532 -d maven-finance -f create_prompts_table.sql
-- =============================================================================

-- Drop existing table if needed (uncomment for fresh install)
-- DROP TABLE IF EXISTS prompts CASCADE;

CREATE TABLE IF NOT EXISTS prompts (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Prompt identification
    model VARCHAR(50) NOT NULL DEFAULT 'iris',
    layer VARCHAR(50) NOT NULL,  -- 'agent', 'subagent', 'global'
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    description TEXT,

    -- Prompt content
    system_prompt TEXT,
    user_prompt TEXT,
    tool_definition JSONB,  -- Tool definition JSON for LLM tool calling

    -- Global prompt references
    uses_global TEXT[],  -- Array of global prompt names to inject

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    CONSTRAINT uq_prompts_model_layer_name_version
        UNIQUE (model, layer, name, version)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prompts_model ON prompts(model);
CREATE INDEX IF NOT EXISTS idx_prompts_layer ON prompts(layer);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);

COMMENT ON TABLE prompts IS
    'Agent and subagent prompts for IRIS system. Includes system prompts, user prompts, and tool definitions.';

COMMENT ON COLUMN prompts.layer IS
    'Prompt layer: agent (main agents), subagent (cascading retrieval), global (shared context)';

COMMENT ON COLUMN prompts.uses_global IS
    'Array of global prompt names to inject into system_prompt at {{CONTEXT_START}}';

-- =============================================================================
-- VERIFICATION
-- =============================================================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'prompts'
ORDER BY ordinal_position;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'PROMPTS TABLE CREATED';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Table: prompts';
    RAISE NOTICE '';
    RAISE NOTICE 'Columns:';
    RAISE NOTICE '  - model, layer, name, version (identification)';
    RAISE NOTICE '  - system_prompt, user_prompt (content)';
    RAISE NOTICE '  - tool_definition (JSON for LLM tools)';
    RAISE NOTICE '  - uses_global (global prompt references)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next step:';
    RAISE NOTICE '  Run populate_iris_prompts.py to insert prompts';
    RAISE NOTICE '==============================================';
END $$;
