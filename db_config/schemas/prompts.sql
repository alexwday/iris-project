-- =============================================================================
-- Table: prompts
-- =============================================================================
--
-- Agent and subagent prompts for IRIS system. Includes system prompts,
-- user prompts, and tool definitions.
--
-- This file defines the schema for the prompts table.
-- Generated from PostgreSQL database: maven-finance
-- =============================================================================

-- Create sequence for id
CREATE SEQUENCE IF NOT EXISTS prompts_id_seq;

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER NOT NULL DEFAULT nextval('prompts_id_seq'::regclass),
    model VARCHAR(50) NOT NULL DEFAULT 'iris'::character varying,
    layer VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0'::character varying,
    description TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    tool_definition JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT prompts_pkey PRIMARY KEY (id)
);

-- Set sequence ownership
ALTER SEQUENCE prompts_id_seq OWNED BY prompts.id;

-- Unique Constraints
ALTER TABLE prompts
    ADD CONSTRAINT uq_prompts_model_layer_name_version UNIQUE (model, layer, name, version);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prompts_model ON prompts USING btree (model);
CREATE INDEX IF NOT EXISTS idx_prompts_layer ON prompts USING btree (layer);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts USING btree (name);

-- =============================================================================
-- Column Descriptions
-- =============================================================================
-- id: Auto-incrementing unique identifier
-- model: Model identifier (default: 'iris')
-- layer: Prompt layer: agent (main agents), subagent (cascading retrieval)
-- name: Name of the prompt
-- version: Version string (default: '1.0.0')
-- description: Description of the prompt's purpose
-- system_prompt: System prompt content
-- user_prompt: User prompt template
-- tool_definition: Tool definitions as JSON
