# IRIS Agents Overview (`iris/src/agents/`)

The IRIS agents directory contains the core AI agents that form the intelligent processing pipeline for user queries within the IRIS system, including specialized subagents for database interactions.

## Overview

The IRIS agent system implements a sophisticated multi-agent architecture designed to process accounting and finance queries through intelligent routing, clarification, planning, research, and synthesis. Each agent has a specific role in the pipeline, using advanced prompt engineering techniques (CO-STAR framework) and LLM tool calling for deterministic, reliable processing. The system supports both direct conversation-based responses and comprehensive database research workflows, with all agents working together to deliver accurate, well-sourced information to users.

## Key Components

* **Core Agents**: Six primary agents that orchestrate the query processing flow
* **Database Subagents**: Seventeen specialized subagents for querying specific data sources
* **Common Structure**: Each agent directory contains main logic files and settings configurations
* **Shared Infrastructure**: All agents use common LLM connectors, global prompts, and error handling

## Core Functions/Classes

### Agent Pipeline Flow

#### Purpose
Orchestrates the complete flow of user queries through the IRIS system, from initial routing to final response delivery.

#### Parameters
* **User Query**: Initial question or request from the user
* **Conversation History**: Previous messages for context
* **Authentication Token**: OAuth token or API key for system access

#### Returns
* **Final Response**: Either direct response or synthesized research findings
* **Usage Metrics**: Token usage and performance data from each agent

#### Workflow
1. **Router Agent**: Analyzes query to determine if research is needed
2. **Path A - Direct Response**: Routes to Direct Response Agent for conversation-based answers
3. **Path B - Research Flow**:
   - **Clarifier Agent**: Assesses context sufficiency and creates research statement
   - **Planner Agent**: Selects 1-5 relevant databases for querying
   - **Database Subagents**: Execute concurrent queries on selected databases
   - **Summarizer Agent**: Synthesizes findings into coherent response
4. **Response Delivery**: Streaming or structured response to user

#### Error Handling
* **Agent-specific exceptions**: Each agent defines custom exception classes
* **Fallback mechanisms**: Graceful degradation when agents encounter errors
* **Comprehensive logging**: Detailed error tracking across the pipeline
* **Usage tracking**: Performance metrics even in error scenarios

### Database Subagent System

#### Purpose
Manages concurrent execution of specialized database queries across 17 different internal and external data sources.

#### Key Subagents
**Internal Sources (13)**:
- Corporate Accounting Policy Manuals (CAPM)
- APG Wiki Entries
- APG Cheatsheets
- Internal Accounting Memos
- Project Approval Request (PAR)
- Auditor Independence Office (AIO)
- Internal Control over Financial Reporting (ICFR)
- ESG Guidance
- Compliance Policies
- External Reporting and Disclosure
- Global Finance Standards
- Management Reporting
- Process and Controls

**External Sources (4)**:
- EY IFRS Guidance
- IASB Standards and Interpretations
- KPMG IFRS Guidance
- PwC IFRS Guidance

## Configuration

Common configuration patterns across agents:

* **Model Capabilities**: Small (router, planner) vs Large (clarifier, direct response, summarizer)
* **Temperature Settings**: 0.0 for deterministic decisions, 0.1-0.7 for natural language generation
* **Token Limits**: 4096 tokens standard across all agents
* **CO-STAR Framework**: Context, Objective, Style, Tone, Audience, Response structure
* **Tool Definitions**: Structured tool calling for predictable outputs

## Usage Examples

### Basic Research Flow
```python
# User query requiring research
"What does IFRS 15 say about revenue recognition for software contracts?"

# Flow:
1. Router → research_from_database
2. Clarifier → Creates research statement with "Accounting Query:" flag
3. Planner → Selects ["internal_capm", "external_iasb"]
4. Database queries execute in parallel
5. Summarizer → Synthesizes findings with citations
```

### Direct Response Flow
```python
# User query with sufficient context
"Based on our previous discussion, summarize the key points about lease accounting"

# Flow:
1. Router → response_from_conversation
2. Direct Response → Generates summary from conversation history
```

## Integration Points

How the agent system integrates with other IRIS components:

* **Chat Model (`model.py`)**: Orchestrates agent execution and manages conversation flow
* **LLM Connectors**: All agents use `rbc_openai.py` for model interactions
* **Global Prompts**: Shared context across all agents (project, fiscal, database, restrictions)
* **Environment Configuration**: Dynamic model selection based on deployment environment
* **Database Infrastructure**: Vector stores and retrieval systems for each data source

## Dependencies

Common dependencies across all agents:

* **`logging`**: Structured logging for debugging and monitoring
* **`typing`**: Type hints for maintainability
* **`json`**: Tool call argument parsing
* **Internal modules**:
  - `env_config`: Environment-specific configurations
  - `rbc_openai`: OpenAI API wrapper with streaming support
  - `global_prompts`: Shared system context
  - Agent-specific settings modules

## Error Handling

System-wide error handling approach:

* **Custom Exception Classes**: Each agent defines specific error types
* **Error Propagation**: Errors bubble up through the pipeline with context
* **Graceful Degradation**: System attempts to provide partial responses when possible
* **Comprehensive Logging**: All errors logged with stack traces using exc_info=True
* **User-Friendly Messages**: Technical errors translated to helpful user messages

## Security Considerations

* **Token Security**: Authentication tokens never logged or persisted
* **Data Isolation**: Each agent processes only its designated data
* **Input Validation**: All user inputs validated before processing
* **Anti-Hallucination**: Strict controls against generating unsourced information
* **Access Control**: Database access restricted based on user permissions

## Performance Notes

* **Concurrent Execution**: Database subagents run in parallel for efficiency
* **Streaming Responses**: Direct Response and Summarizer use streaming for better UX
* **Model Optimization**: Small models for routing/planning, large for content generation
* **Caching**: System prompts cached to reduce token usage
* **Scalability**: Designed to handle multiple concurrent user sessions

---

For detailed information about individual agents, refer to their specific documentation:
- [Router Agent](./agent-router.md)
- [Clarifier Agent](./agent-clarifier.md)
- [Planner Agent](./agent-planner.md)
- [Direct Response Agent](./agent-direct-response.md)
- [Summarizer Agent](./agent-summarizer.md)
- [Database Subagents Overview](./database-subagents/database-subagents-overview.md)