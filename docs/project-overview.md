# IRIS Project - Comprehensive Overview

IRIS (Intelligent Retrieval & Interaction System) is an advanced AI agent-based system designed to answer user queries by interacting with a diverse set of internal and external financial data sources. It employs a modular pipeline of specialized agents to route, clarify, plan, query, and synthesize responses efficiently and accurately.

## Overview

IRIS serves RBC Finance by implementing an intelligent research and response system for finance policy inquiries. The system combines comprehensive internal and external finance policy documentation with an autonomous agent-based RAG (Retrieval-Augmented Generation) process. Users can engage in natural conversations about finance policies, and the system independently researches and generates responses as needed. The architecture employs a modular pipeline of specialized agents that coordinate to handle complex queries across multiple data sources while maintaining security, compliance, and performance standards.

## Key Components

* **Agent Pipeline**: Structured flow including Router, Clarifier, Planner, Database Router, Summarizer, and Direct Response agents
* **Database Subagents**: Specialized subagents for querying specific internal and external data sources
* **Chat Model Orchestration**: Central coordination layer managing the complete agent pipeline
* **Initial Setup Systems**: Configuration, authentication, logging, and monitoring infrastructure  
* **Global Prompts**: Standardized context and instruction components used across all agents
* **LLM Connectors**: Unified interfaces for language model API interactions

## Core Functions/Classes

### Agent Pipeline System (`iris/src/agents/`)

#### Purpose
Modular pipeline of specialized AI agents that coordinate to process user queries through routing, clarification, planning, database querying, and response synthesis.

#### Key Agents
* **Router Agent**: Determines if query requires database research or direct response
* **Clarifier Agent**: Refines research goals and determines scope (metadata vs research)
* **Planner Agent**: Selects relevant databases and creates query plans
* **Database Subagents**: Specialized agents for querying specific internal and external data sources
* **Summarizer Agent**: Synthesizes research findings into coherent responses
* **Direct Response Agent**: Provides conversational responses when research is unnecessary

#### Integration
Central processing pipeline coordinating all query handling and response generation

### Chat Model Orchestration (`iris/src/chat_model/`)

#### Purpose
Central coordination layer managing the complete agent pipeline from user input to final response, including concurrent database operations and process monitoring.

#### Key Functions
* Pipeline orchestration and agent coordination
* Concurrent database query execution using ThreadPoolExecutor
* Process monitoring and usage tracking
* Both synchronous and asynchronous interfaces for different integration needs

### Database Subagents (`iris/src/agents/database_subagents/`)

#### Purpose
Specialized subagents for querying specific data sources with tailored approaches for different content types and access patterns.

#### Internal Sources
* CAPM, Cheatsheets, Compliance, ESG, External Reporting and Disclosure
* Global Finance Standards, ICFR, Management Reporting, Memos, PAR
* Process and Controls, Wiki, AIO

#### External Sources
* EY, IASB, KPMG, PwC professional guidance and standards

### Support Systems

#### Initial Setup (`iris/src/initial_setup/`)
* Database connections, logging configuration, process monitoring
* OAuth authentication, SSL setup, environment configuration

#### Global Prompts (`iris/src/global_prompts/`)
* Standardized context, database descriptions, fiscal calendar
* Compliance restrictions, quality guidelines, project statements

#### LLM Connectors (`iris/src/llm_connectors/`)
* OpenAI API integration with retry logic and usage tracking
* Support for streaming, non-streaming, tool calls, and embeddings

## Configuration

System configuration managed through environment variables and configuration modules:

* **Environment Detection**: Automatic local vs RBC environment configuration
* **Database Settings**: PostgreSQL connection parameters and credentials
* **Authentication**: OAuth tokens for RBC API access and OpenAI API keys
* **SSL Configuration**: Certificate setup for secure API communication
* **Model Settings**: LLM model configurations, costs, and capabilities
* **Monitoring Settings**: Process monitoring and usage tracking configuration

## Usage Examples

### Basic Query Processing
```python
from iris.src.chat_model.model import model

conversation = {
    "messages": [
        {"role": "user", "content": "What is the current policy for revenue recognition?"}
    ]
}

# Process through agent pipeline
for response_chunk in model(conversation):
    print(response_chunk, end='')
```

### Jupyter Notebook Testing
```bash
# Start Jupyter
jupyter notebook

# Open test notebook
# notebooks/test_notebook.ipynb
```

### FastAPI Integration
```python
from iris.src.chat_model.model import process_request_async

# Async processing for web applications
result = await process_request_async(conversation_messages, stream=False)
```

## Integration Points

The IRIS system integrates with multiple external and internal systems:

* **Database Sources**: PostgreSQL databases containing internal and external finance policy documentation
* **OpenAI API**: Language model services for agent processing and response generation
* **Web Interfaces**: FastAPI integration for web-based user interactions
* **Process Monitoring**: Database logging for execution tracking and performance analysis
* **Authentication Systems**: OAuth integration for secure API access in RBC environments
* **SSL/TLS Infrastructure**: Secure communication channels for all external API interactions

## Dependencies

### Core Dependencies
* **Python 3.9+**: Programming language and runtime environment
* **PostgreSQL**: Database system for data storage and retrieval
* **OpenAI Python SDK**: Official SDK for OpenAI API interactions
* **FastAPI**: Web framework for API endpoints and async processing
* **psycopg2**: PostgreSQL database adapter for Python

### Development Dependencies
* **Black**: Code formatting and style enforcement
* **MyPy**: Static type checking
* **Pytest**: Testing framework
* **Jupyter**: Interactive development and testing environment

## Error Handling

Comprehensive error handling throughout the system:

* **Agent Pipeline Failures**: Individual agent failures are isolated and logged without stopping the overall pipeline
* **Database Connection Issues**: Robust connection management with retry logic and fallback behavior
* **API Communication Errors**: Retry mechanisms for transient failures with detailed error logging
* **Authentication Failures**: Clear error reporting and retry logic for OAuth and API key issues
* **Process Monitoring Resilience**: Monitoring failures do not impact core system functionality

## Security Considerations

* **Authentication Token Security**: OAuth tokens and API keys are securely managed with masking in logs
* **Database Security**: Secure connection parameters and credential management for database access
* **SSL/TLS Encryption**: All external communications secured with proper certificate validation
* **Access Control**: User permissions and access limitations respected throughout the query process
* **Data Privacy**: Sensitive information filtering in logs and monitoring to prevent exposure

## Performance Notes

* **Concurrent Processing**: ThreadPoolExecutor enables parallel database queries for improved response times
* **Streaming Responses**: Real-time response delivery for better user experience
* **Connection Pooling**: Efficient database connection management to reduce overhead
* **Caching Strategy**: Strategic caching of configuration and frequently accessed data
* **Resource Management**: Proper cleanup and resource management to prevent memory leaks
* **Monitoring Optimization**: Performance monitoring designed to have minimal impact on system performance

---

The IRIS system provides a comprehensive, secure, and efficient platform for intelligent finance policy research and response generation, serving RBC Finance with advanced AI-powered capabilities.
