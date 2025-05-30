# Agent Summarizer (`iris/src/agents/agent_summarizer/`)

The Summarizer Agent generates the final research summary based on aggregated detailed research findings from various databases. It synthesizes information into a coherent, comprehensive response for the user.

## Overview

The Summarizer Agent serves as the final synthesis step in the IRIS research workflow. It processes aggregated research findings from multiple database subagents and generates either formatted metadata lists or comprehensive research summaries depending on the scope. The agent employs the CO-STAR framework for sophisticated synthesis, implements pattern recognition to identify consensus and contradictions across sources, and uses confidence signaling to convey the reliability of findings. It supports streaming response delivery for research summaries.

## Key Components

* **`summarizer.py`**: Implements the core summarization logic with the main function `generate_streaming_summary`. Processes aggregated research findings to generate streaming summaries for research scope or formatted lists for metadata scope. Yields content chunks progressively with final usage details.
* **`summarizer_settings.py`**: Defines sophisticated CO-STAR framework configuration with detailed synthesis guidelines. Uses 'large' model capability with low temperature (0.1) for precise synthesis. Provides pattern recognition instructions, confidence signaling, and citation integration examples.

## Core Functions/Classes

### `generate_streaming_summary(aggregated_detailed_research, scope, token, original_query_plan=None)`

#### Purpose
Generates the final response based on aggregated detailed research findings, either as a formatted metadata list or a comprehensive synthesized research summary with streaming delivery.

#### Parameters
* **`aggregated_detailed_research`** (Dict[str, str]): Dictionary keyed by database name containing detailed research strings from each database
* **`scope`** (str): The scope of the request ('metadata' or 'research')
* **`token`** (str): Authentication token for API access (OAuth token in RBC environment, API key in local environment)
* **`original_query_plan`** (Dict, optional): The original query plan for context (default: None)

#### Returns
* **Generator[Any, None, None]**: Yields multiple items:
  - For 'research' scope: Content chunks (str) of the synthesized summary as they're generated
  - For 'metadata' scope: Single formatted string with results and embedded JSON context
  - Final item: Usage details dictionary
    ```python
    {'usage_details': {
        'model': str,
        'prompt_tokens': int,
        'completion_tokens': int,
        'cost': float,
        'response_time_ms': int
    }}
    ```

#### Workflow
1. **Scope Determination**: Routes to appropriate handling based on scope parameter
2. **Research Scope Processing**:
   - Model configuration retrieval
   - System prompt preparation with CO-STAR framework
   - Research context formatting from aggregated findings
   - Streaming LLM call for synthesis
   - Progressive content chunk yielding
3. **Metadata Scope Processing**:
   - Direct formatting without LLM call
   - JSON context embedding for follow-up capability
   - Single yield of formatted results
4. **Usage Details Capture**: Detects and yields final usage information
5. **Error Handling**: Comprehensive error management with detailed logging

#### Error Handling
* **SummarizerError**: Raised for synthesis failures or invalid scope
* **Configuration errors**: Handles model configuration retrieval failures
* **Stream processing**: Manages streaming interruptions gracefully
* **Usage data fallback**: Provides error usage details if stream data missing
* **Exception logging**: Comprehensive error logging with stack traces via exc_info

### `SummarizerError` (Exception Class)

#### Purpose
Custom exception class for summarizer-specific errors, providing clear error context for synthesis and formatting failures.

## Configuration

Settings used from `summarizer_settings.py`:

* **`MODEL_CAPABILITY`**: "large" - Uses advanced model for sophisticated synthesis
* **`MAX_TOKENS`**: 4096 - Maximum tokens for comprehensive summaries
* **`TEMPERATURE`**: 0.1 - Low temperature for precise, consistent synthesis
* **`AVAILABLE_DATABASES`**: Database information for display names
* **`PATTERN_RECOGNITION_INSTRUCTIONS`**: Guidelines for identifying consensus, contradictions, and gaps
* **`CONFIDENCE_SIGNALING`**: Framework for conveying reliability of findings
* **`SUMMARIZER_SPECIFIC_GUARDRAILS`**: Strict adherence to provided research without speculation

## Usage Examples

### Basic Usage
```python
from iris.src.agents.agent_summarizer.summarizer import generate_streaming_summary

# Research scope with multiple database findings
aggregated_research = {
    "internal_capm": "## Key Findings\n- IFRS 15 requires...",
    "external_iasb": "## Core Principles\n- Revenue recognition when..."
}

# Stream the synthesized summary
for chunk in generate_streaming_summary(
    aggregated_research, 
    "research", 
    auth_token,
    original_query_plan
):
    if isinstance(chunk, dict) and 'usage_details' in chunk:
        # Final usage details
        usage = chunk['usage_details']
    else:
        # Content chunk
        print(chunk, end='', flush=True)
```

### Advanced Usage
```python
# Metadata scope with catalog results
aggregated_metadata = {
    "internal_wiki": "[{'id': 'wiki_123', 'name': 'Revenue Recognition Guide', ...}]",
    "internal_icfr": "[{'id': 'icfr_456', 'name': 'Control Procedures', ...}]"
}

# Get formatted metadata list
for result in generate_streaming_summary(
    aggregated_metadata,
    "metadata",
    auth_token,
    original_query_plan
):
    if isinstance(result, str):
        # Formatted list with embedded JSON context
        print(result)
```

## Integration Points

How the Summarizer Agent integrates with other IRIS components:

* **Database Subagents**: Receives aggregated research findings from all queried databases
* **Chat Model**: Final step in research pipeline, returns synthesized response to user
* **Planner Agent**: Uses original query plan for context in synthesis
* **Global Prompts**: Incorporates project, fiscal, and restrictions statements for context

## Dependencies

* **`logging`**: Comprehensive operation logging and error tracking
* **`json`**: JSON handling for metadata context embedding
* **`typing`**: Type hints for generator functions and complex types
* **Internal modules**: 
  - `env_config`: Model configuration and capability settings
  - `rbc_openai`: LLM connector for streaming synthesis calls
  - `global_prompts`: Project, fiscal, and restrictions statements (excludes database statement)
  - `summarizer_settings`: CO-STAR framework configuration and synthesis guidelines

## Error Handling

Comprehensive error handling approach:

* **Configuration failures**: Handles model configuration retrieval errors with fallback
* **Invalid scope**: Raises SummarizerError for unrecognized scope values
* **Stream processing errors**: Manages streaming interruptions for research scope
* **Empty research handling**: Gracefully handles cases with no research findings
* **Usage data extraction**: Provides error usage details when stream data unavailable
* **Exception propagation**: Re-raises as SummarizerError with context
* **Logging**: All errors logged with full stack traces using exc_info=True

## Security Considerations

* **Token handling**: Authentication tokens passed through without storage or logging
* **Data isolation**: Only processes provided research findings, no external data access
* **Anti-speculation**: Enforces synthesis based only on provided research
* **Citation preservation**: Maintains source attribution from research findings
* **No data persistence**: Stateless processing without storing research data

## Performance Notes

* **Streaming efficiency**: Progressive content delivery for research summaries
* **Model selection**: Large model provides nuanced synthesis capabilities
* **Temperature tuning**: 0.1 ensures consistent, precise synthesis across runs
* **Scope optimization**: Metadata formatting bypasses LLM for efficiency
* **Token optimization**: CO-STAR framework prompt cached via construct_system_prompt()
* **Generator pattern**: Memory-efficient streaming without buffering entire response

---

Refer to the [agents-overview.md](./agents-overview.md) for details on how the Summarizer Agent completes the IRIS system research pipeline.