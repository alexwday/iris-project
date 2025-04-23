# IRIS Agent Framework

## A Template for Agentic Applications

## Core Framework Components

### 1. Agent Workflow Architecture

- **Central Router**: Decision orchestration for direct responses or research paths
- **Specialized Agents**: Clarifier, Planner, Summarizer - each with distinct responsibilities
- **Clear Flow Definition**: Well-defined interfaces between components
- **Model Selection per Task**: Each agent can use different model capabilities optimized for its task

### 2. LLM Connector System

- **Unified Interface**: Single connector to multiple LLM providers
- **Model Switching**: Configure different models via settings files
- **Authentication Flexibility**: Support for both OAuth and API key methods
- **Call Types**: Handles streaming, non-streaming, and tool calls
- **Token Tracking**: Comprehensive usage and cost monitoring

### 3. Database Integration Framework

- **Subagent Architecture**: Each database has a specialized subagent
- **Standardized Query Flow**:
  - Vector/semantic search to find relevant documents
  - Selection of relevant sections
  - Content retrieval from database
  - LLM-based synthesis of findings
- **Consistent Response Format**: Tool-based structure with standardized output
- **Easy Expansion**: Add new databases by implementing the subagent pattern

### 4. Prompting Framework

- **COSTAR + XML Structure**: Context, Objective, Style, Tone, Audience, Response
- **Structured Tool Calling**: JSON schema for consistent responses
- **Global Prompting System**: Centralized context shared across agents
  - Database inventory and descriptions
  - Project context and objectives
  - Compliance restrictions and guidelines
  - Fiscal information

### 5. Advanced Features

- **End-to-End Streaming**: Integrated throughout the system
- **Process Monitoring**: Stage-by-stage tracking with detailed metrics
  - Execution time per stage
  - Token usage and costs
  - Error tracking
- **Conversation Management**: Input standardization and history management
- **Enterprise Security**: SSL configuration and OAuth setup built-in

## Why It's The Ideal Template

1. **Modular Architecture**: Easily extend or replace components
2. **Flexible Database Connections**: Connect to any database type with minimal changes
3. **Model Provider Agnostic**: Switch between model providers with configuration changes
4. **Enterprise-Ready**: Security, monitoring, and error handling built-in
5. **Well-Documented**: Clear code patterns and comprehensive logging

## Next Steps

- **Metrics Dashboard**: Real-time monitoring of agent performance
- **Additional Connectors**: Expand LLM provider options
- **Automated Testing**: Expand test coverage for all components
- **Performance Optimization**: Further reduce latency and token usage