# Subagent YAML Template Structure

This document defines the standardized YAML template structure for all database subagents in the IRIS system.

## Template Structure

All subagent YAML files should follow this standardized structure:

```yaml
# [Subagent Name] Configuration
# Converted from [original_file].py to YAML format

# Model Configuration
model:
  capability: "small" | "large"  # Based on subagent complexity
  max_tokens: [number]           # Appropriate for subagent task
  temperature: [0.0-1.0]         # Usually low for consistency

# Global context statements to include and their insertion points
context:
  statements:
    - name: "project_statement"
      function: "get_project_statement"
    - name: "database_statement"      # Optional - exclude if not needed
      function: "get_database_statement"
    - name: "fiscal_statement"
      function: "get_fiscal_statement"
    - name: "restrictions_statement"
      function: "get_restrictions_statement"

# Tool definitions (if subagent uses tools)
tools:
  - type: "function"
    function:
      name: "[tool_name]"
      description: "[tool description]"
      parameters:
        type: "object"
        properties:
          # Tool parameters here
        required: ["param1", "param2"]

# Complete system prompt with CO-STAR framework and task definition
system_prompt: |
  {{CONTEXT_START}}

  <OBJECTIVE>
  [Clear statement of subagent's specific objective]
  Your objective is to:
  1. [Specific goal 1]
  2. [Specific goal 2]
  3. [etc.]
  </OBJECTIVE>

  <STYLE>
  [Writing and approach style]
  </STYLE>

  <TONE>
  [Communication tone]
  </TONE>

  <AUDIENCE>
  [Target audience - usually other system components]
  </AUDIENCE>

  You are [subagent role description].

  <TASK>
  [Detailed task description]

  <INPUT_FORMAT>
  You receive:
  - `parameter1`: Description of input parameter
  - `parameter2`: Description of input parameter
  </INPUT_FORMAT>

  <ANALYSIS_INSTRUCTIONS>
  [Detailed step-by-step instructions for the subagent]
  </ANALYSIS_INSTRUCTIONS>

  <INPUT_PARAMETER_1>
  {{parameter1}}
  </INPUT_PARAMETER_1>

  <INPUT_PARAMETER_2>
  {{parameter2}}
  </INPUT_PARAMETER_2>

  <OUTPUT_REQUIREMENTS>
  [Specific output format requirements]
  </OUTPUT_REQUIREMENTS>

  <WORKFLOW_CONTEXT>
  <YOUR_POSITION>
  [Description of subagent's position in the workflow]
  </YOUR_POSITION>

  <UPSTREAM_CONTEXT>
  [What happens before this subagent]
  </UPSTREAM_CONTEXT>

  <DOWNSTREAM_IMPACT>
  [What happens after this subagent and impact]
  </DOWNSTREAM_IMPACT>
  </WORKFLOW_CONTEXT>

  <ERROR_HANDLING>
  [Specific error handling scenarios for this subagent]
  </ERROR_HANDLING>
  </TASK>

  <RESPONSE_FORMAT>
  [Final response format specification]
  </RESPONSE_FORMAT>
```

## Model Configuration Guidelines

### Capability Selection
- **"large"**: Use for complex analysis, document selection, planning tasks
- **"small"**: Use for content synthesis, extraction, focused processing tasks

### Max Tokens Guidelines
- **2048**: Simple selection/routing tasks
- **8192-16384**: Content synthesis and research tasks
- **32768**: Complex multi-document synthesis (rarely needed for subagents)

### Temperature Settings
- **0.0**: Deterministic tasks (selection, routing)
- **0.1**: Slight creativity for synthesis while maintaining consistency
- **0.3-0.7**: Higher creativity (rarely used in subagents)

## Context Statements Guidelines

### Minimal Context (Most Subagents)
For focused tasks like document selection and content synthesis:
- `context: statements: []` (no global context needed)
- These subagents perform specific extraction/processing tasks

### Full Context (Strategic Tasks)
Only include global context for subagents that need broader system awareness:
- `project_statement`: Project purpose and scope  
- `database_statement`: Available databases information
- `fiscal_statement`: Current fiscal period context
- `restrictions_statement`: Compliance and quality guidelines

### Current Practice
- **Document Selection**: No global context (focused task)
- **Content Synthesis**: No global context (focused extraction)
- **Strategic Planning**: Would use full context (none currently exist)

## Tool Configuration

### Tools with Parameters
```yaml
tools:
  - type: "function"
    function:
      name: "tool_name"
      description: "Clear description of what the tool does"
      parameters:
        type: "object"
        properties:
          param_name:
            type: "string"
            description: "Parameter description"
        required: ["param_name"]
```

### No Tools
```yaml
tools: []
```

## CO-STAR Framework Implementation

All subagents must implement the CO-STAR framework:

1. **Context**: Via `{{CONTEXT_START}}` placeholder
2. **Objective**: Clear `<OBJECTIVE>` section
3. **Style**: Specific `<STYLE>` guidance
4. **Tone**: Appropriate `<TONE>` specification
5. **Audience**: Target `<AUDIENCE>` description
6. **Response**: Detailed `<RESPONSE_FORMAT>` requirements

## Template Placeholders

Use these placeholders for dynamic content injection:

- `{{CONTEXT_START}}`: Inserts global context statements
- `{{parameter_name}}`: Inserts dynamic input parameters
- `{{user_query}}`: User's original query
- `{{formatted_documents}}`: Formatted document content
- `{{formatted_catalog}}`: Formatted catalog entries
- `{{formatted_cards}}`: Formatted context cards

## Workflow Context Section

Include workflow context to help subagents understand their role:

- **YOUR_POSITION**: Where this subagent fits in the workflow
- **UPSTREAM_CONTEXT**: What happens before this subagent
- **DOWNSTREAM_IMPACT**: How this subagent's output affects subsequent steps

## Error Handling

Include specific error handling scenarios relevant to the subagent:

- Input format issues
- No relevant content found
- Conflicting information
- Technical processing errors

## Current Subagent Implementations

### 1. Catalog Selection Subagent
- **File**: `catalog_search/catalog_selection_prompt.yaml`
- **Purpose**: Select relevant documents from internal catalogs
- **Model**: Large, 2048 tokens, temperature 0.0
- **Context**: Minimal (no database_statement)
- **Tools**: None (direct JSON output)

### 2. Catalog Search Content Synthesis Subagent
- **File**: `catalog_search/content_synthesis_prompt.yaml`
- **Purpose**: Extract page-based research from internal documents
- **Model**: Small, 16384 tokens, temperature 0.1
- **Context**: Full global context
- **Tools**: `extract_page_based_research`

### 3. Semantic Search Content Synthesis Subagent
- **File**: `semantic_search/content_synthesis_prompt.yaml`
- **Purpose**: Synthesize research from IASB context cards
- **Model**: Small, 16384 tokens, temperature 0.1
- **Context**: Full global context
- **Tools**: `synthesize_research_findings`

## Best Practices

1. **Consistency**: Follow the template structure exactly
2. **Clarity**: Use clear, specific descriptions in all sections
3. **Modularity**: Design subagents for single, focused purposes
4. **Error Handling**: Include comprehensive error scenarios
5. **Documentation**: Comment any deviations from standard template
6. **Testing**: Ensure template placeholders work correctly
7. **Maintenance**: Keep templates updated with framework changes