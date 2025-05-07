# 7. Model Implementation

**Model Name:** IRIS (Intelligent Research and Information System)
**Model ID:** IRIS-001

## 7.1 Software / Coding

IRIS employs a modular architecture organized around specialized agents and knowledge sources. The system implementation consists of the following main components:

### 7.1.1 System Architecture

The IRIS system operates through a multi-tier architecture. This includes the **Maven UI**, which is the user-facing application providing the interface for interacting with IRIS; the **IRIS API**, which encompasses the core model functionality deployed as an API service; **Database Services**, consisting of a PostgreSQL database with the pgvector extension for document and vector storage; and an **LLM Gateway** for integration with RBC's Lumina portal to access large language models.

The system functions through a coordinated process. Users interact with the **Maven Interface**, which manages user authentication and access control via Active Directory groups, authorizes specific database access based on user roles, handles conversation history and session management, and is responsible for user interface presentation and the streaming of responses. The **IRIS Model API** receives conversation context and authorized database access from Maven, processes queries through its agent framework, returns streaming responses back to Maven, and logs process monitoring data for performance tracking. **Database Management** involves separate PostgreSQL tables for knowledge retrieval and process monitoring, with database refreshes occurring on a set schedule (quarterly or yearly, depending on the database). **LLM Integration** is achieved by IRIS connecting to language models through RBC's Lumina portal.

Currently, the IRIS code has been implemented and deployed in Dataiku as a Dash web application demo. This same code is being integrated into the Maven UI for the production implementation. Both implementations interact with the same PostgreSQL database, with no changes being made during the transition from Dataiku to Maven.

### 7.1.2 Agent Framework

The agent system is implemented as a collection of Python modules, each responsible for specific aspects of query processing as described in Section 6.1. The **Router Agent**, implemented in `/iris/src/agents/agent_router/router.py`, determines the optimal processing path for each query by analyzing query intent and required knowledge sources. The **Clarifier Agent**, found in `/iris/src/agents/agent_clarifier/clarifier.py`, ensures queries contain sufficient context before research begins by identifying and requesting missing information. The **Planner Agent**, located in `/iris/src/agents/agent_planner/planner.py`, creates research plans by selecting appropriate knowledge sources and setting search parameters. **Database Subagents**, implemented in `/iris/src/agents/database_subagents/`, are specialized modules for retrieving information from specific internal sources (CAPM, Cheatsheets, Compliance, etc.) and external sources (EY, IASB, KPMG, PwC). The **Summarizer Agent**, implemented in `/iris/src/agents/agent_summarizer/summarizer.py`, synthesizes findings into coherent, properly cited responses. Finally, the **Direct Response Agent**, found in `/iris/src/agents/agent_direct_response/response_from_conversation.py`, generates responses based solely on conversation history without database access.

Data flows between agents through structured JSON messages containing the query context, research parameters, retrieved information, and synthesized responses. Each agent maintains its own state during processing and passes relevant information to downstream agents.

### 7.1.3 Knowledge Store Implementation

The IRIS knowledge store is implemented as a PostgreSQL database.

#### Core Database Tables

The database includes several core tables. The **apg_catalog** table serves as a document metadata repository, containing document identification details (source, type, name), document description and usage information, and file metadata (creation date, modification date, size, path). The **apg_content** table is for document content storage, holding references to documents in `apg_catalog`, section-based content organization, and both section summaries and full content text. The **iris_textbook_database** is a vector-enabled document chunk storage table, featuring document and section structural positioning (as detailed in Section 5), chapter-level metadata with tags and summaries, section-level pagination and importance scoring, content text, 2000-dimension vector embeddings, and a full-text search vector for text-based queries. Lastly, the **process_monitor_logs** table acts as a performance tracking system, logging detailed information for each model invocation, including timing and token usage metrics for each processing stage, and LLM call details stored as structured JSON.

#### Database Connectivity

The system connects to the database through a standardized configuration layer in `/iris/src/initial_setup/db_config.py`. This layer provides connection parameters for both local development and RBC environments, handles connection management and error recovery, and verifies the existence of required tables.

#### Database Processing Methods

The IRIS system employs five distinct approaches for knowledge retrieval, as detailed in Section 6.2. **Catalog Search - Small** is used for standard documents with simple structure (e.g., `internal_par`, `internal_process_and_controls`), involving a two-stage selection with catalog prioritization, LLM evaluation of metadata for document selection, and full section retrieval for selected documents. **Catalog Search - Large** is applied to large documents with hierarchical structure (e.g., `internal_capm`, `internal_global_finance_standards`), utilizing a three-stage hierarchical selection with LLM judgment and section summary evaluation for targeted content retrieval. **Catalog Search - Excel** is designed for tabular data sources (e.g., `internal_wiki`, `internal_management_reporting`), featuring table preprocessing with row-level document conversion and preservation of table format in Markdown. **Catalog Search - Vision** handles infographics and visual content (e.g., `internal_cheatsheets`), using an image-to-text conversion via a multi-pass vision transformer with multi-pass extraction of text, tables, and diagrams. Finally, **Semantic Search - Large** is for extensive reference materials (e.g., external sources like `external_ey`, `external_iasb`, `external_kpmg`, `external_pwc`), employing vector-based similarity search with token-aware chunking, sophisticated reranking based on importance scores and vector similarity, along with section expansion and sequence gap filling.

The database subagents implement these different approaches based on the specific requirements of each knowledge source, with a central database router (`database_router.py`) directing queries to the appropriate subagent.

### 7.1.4 Model Integration

IRIS integrates with large language models through the RBC Lumina portal. An **LLM Connector**, implemented in `/iris/src/llm_connectors/rbc_openai.py`, provides a consistent interface for agent-LLM communication, with configuration parameters defined in `/iris/src/llm_connectors/rbc_openai_settings.py`.

The system employs several models: **GPT-4o** for complex reasoning tasks like research synthesis, clarification, and content generation; **GPT-4o-mini** for decision tasks such as routing, database selection, and document filtering; **text-embedding-3-large** for generating vector embeddings used in semantic search; and **Qwen2** for vision processing of infographics and other image content.

Each model is accessed with customized prompt engineering to ensure consistent outputs across the agent architecture.

### 7.1.5 Process Monitoring

The IRIS system includes comprehensive process monitoring capabilities. This involves **Performance Tracking**, where every model call is logged with detailed performance metrics. All **Process Stages** in the pipeline are tracked with timing and token usage information. **Error Logging** provides structured logging of any issues or exceptions encountered. Additionally, **Usage Analytics** offer aggregated statistics on system usage patterns.

The monitoring framework is implemented in `/iris/src/initial_setup/process_monitor.py` and records detailed information about each model invocation in the `process_monitor_logs` table. This enables real-time performance monitoring by actively tracking system responsiveness, cost optimization through analysis of token usage patterns, early error detection for potential issues in the processing pipeline, and usage pattern analysis to understand common query types and knowledge source utilization.

The monitoring system outputs can be analyzed using the Jupyter notebooks in the `/notebooks/` directory, particularly `process_monitor_analysis.ipynb`, which provides visualization and statistical analysis of system performance metrics.

### 7.1.6 Process Flow Diagram

The IRIS system follows a processing flow that implements the theoretical approach described in Sections 4 through 6. The data flow through the system can be conceptualized as follows:

```
User Query (Maven UI)
      │
      ▼
 Conversation History
      │
      ▼
  Agent Router ───────────► Direct Response Path ──► Agent Direct Response
      │                                                      │
      │                                                      │
      ▼                                                      ▼
Research Path                                          User Response
      │
      ▼
Agent Clarifier
      │
      ▼
 Agent Planner
      │
      ▼
Database Subagents (Multiple in Parallel)
      │
      ▼
Agent Summarizer
      │
      ▼
 User Response
```

This implementation directly aligns with the agent architecture described in Section 4.1 and the model decision processes detailed in Section 6.3.

### 7.1.7 Development and Deployment

The IRIS code is currently running as a Python library in two environments: in **Dataiku**, it is implemented as a Dash web application for demonstration and business user feedback, which has been incorporated into ongoing development; and in **Local Development** environments for ongoing development and testing.

The code is being provided to the Maven team for integration into their UI, with plans to have the functional demonstration available in the Maven development environment by June 2025. The integration will maintain the same core functionality with no changes to the underlying model code, focusing primarily on adapting the API interface to work within the Maven ecosystem. The requirements and setup are all packaged within the model code to facilitate deployment.

### 7.1.8 Code Quality Assurance

The IRIS development team employs several approaches to ensure code quality. **Code Formatting** is enforced using Black with an 88 character line limit. **Linting** is performed with Pylint to identify potential code issues and ensure adherence to coding standards. **Testing** occurs in Dataiku, where the code runs as a Python library, and locally during development. Finally, **Deployment Validation** will involve retesting the code once hosted in OpenShift to confirm consistent working behavior.

These practices help identify and resolve potential issues, ensuring that the production system remains stable and performant.

### 7.1.9 Implementation Alignment with Model Design

The implementation of IRIS directly realizes the model design and approach described in the previous sections. Key points of alignment include the agent-based architecture, which follows the modular agent framework with specialized agents for different processing tasks. The system implements the hybrid RAG approach, using different processing pipelines based on document types. The five distinct retrieval methods are directly implemented in the database subagents with specific optimizations. Model parameter configurations align with the documented approach, including temperature settings. The system also implements the token-aware chunking algorithm for optimal information density and the monitoring framework for comprehensive performance tracking.

This direct alignment between design and implementation ensures that the theoretical approach is properly realized in the system.

## 7.2 Implementation Testing

The implementation of IRIS has undergone initial testing in the Dataiku environment. The system will receive comprehensive testing once integrated into the Maven UI.

The Dataiku version has been made available to business users to provide feedback on functionality and response quality. This feedback has been incorporated into ongoing development efforts.

Final implementation testing will be performed once the system is live in the Maven development environment, currently planned for June. This testing will validate that the system behaves as expected in the production environment and meets all business requirements.
