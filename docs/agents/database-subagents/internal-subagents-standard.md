# Internal Database Subagents (`iris/src/agents/database_subagents/internal_*/`)

Standardized implementation for internal database subagents (excluding internal_capm) that query and synthesize research from internal RBC accounting guidance databases using catalog selection and content synthesis.

## Overview

The internal database subagents share identical implementation logic for handling queries to internal RBC content stored in the database. This documentation covers all internal subagents EXCEPT internal_capm, which has unique functionality. The standard internal subagents include:
- internal_aio
- internal_cheatsheets
- internal_compliance
- internal_esg
- internal_ext_reporting_and_disclosure
- internal_global_finance_standards
- internal_icfr
- internal_management_reporting
- internal_memos
- internal_par
- internal_process_and_controls
- internal_wiki

Each performs catalog document selection followed by content synthesis. All subagents support both 'metadata' scope (for document discovery) and 'research' scope (for detailed content synthesis) queries.

## Key Components

* **`subagent.py`**: Core query processing logic implementing catalog selection and synthesis
* **`catalog_selection_prompt.py`**: Prompt template for LLM-based catalog document selection
* **`content_synthesis_prompt.py`**: Prompt template for synthesizing selected document content
* **`__init__.py`**: Python package initialization

## Core Functions/Classes

### `query_database_sync(query, scope, token, process_monitor, query_stage_name)`

#### Purpose
Main entry point for synchronously querying the internal database, handling both metadata and research scopes.

#### Parameters
* **`query`** (str): The search query to execute
* **`scope`** (str): Query scope - either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token for API access
* **`process_monitor`** (optional): Process monitor for tracking token usage
* **`query_stage_name`** (str, optional): Specific stage name for this query instance

#### Returns
* **SubagentResult**: Tuple containing:
  - DatabaseResponse: Query results (MetadataResponse list or ResearchResponse dict)
  - Optional[List[str]]: List of document IDs used in the search

#### Workflow
1. **Initialize**: Set up logging and process monitoring
2. **Execute Logic**: Call `_query_database_logic` to perform the actual query
3. **Process Usage**: Track LLM usage details through process monitor
4. **Handle Results**: Return results with appropriate document IDs

#### Error Handling
* **Database Errors**: Logged and returned with appropriate error status
* **Connection Errors**: Handled with fallback to error response
* **LLM Errors**: Gracefully handled with error messages

### `_query_database_logic(query, scope, token)`

#### Purpose
Internal logic implementing the query processing pipeline for both metadata and research scopes.

#### Parameters
* **`query`** (str): The search query
* **`scope`** (str): Either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token

#### Returns
* **LogicResult**: Tuple containing:
  - DatabaseResponse: Query results
  - Optional[List[str]]: Document IDs used
  - List[LlmUsageDetails]: Collected LLM usage details

#### Workflow
##### Metadata Scope:
1. **Load Catalog**: Retrieve all documents from catalog table
2. **Format Response**: Return document metadata list

##### Research Scope:
1. **Load Catalog**: Retrieve available documents
2. **Select Documents**: Use LLM to select relevant documents based on query
3. **Retrieve Content**: Fetch full content for selected documents
4. **Generate Response**: Use LLM to synthesize research from content

### `_load_catalog(cursor, database_name)`

#### Purpose
Loads the complete document catalog from the database.

#### Parameters
* **`cursor`**: Database cursor
* **`database_name`** (str): Name of the specific internal database

#### Returns
* **List[Dict[str, Any]]**: List of catalog entries with metadata

### `_select_documents_from_catalog(query, catalog_entries, database_name, token)`

#### Purpose
Uses LLM to intelligently select relevant documents from the catalog based on the query.

#### Parameters
* **`query`** (str): User's search query
* **`catalog_entries`** (List[Dict]): Available catalog entries
* **`database_name`** (str): Database identifier
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[List[str], LlmUsageDetails]**: Selected document IDs and usage details

### `_retrieve_documents_content(cursor, doc_ids, database_name)`

#### Purpose
Retrieves full content for selected documents from the database.

#### Parameters
* **`cursor`**: Database cursor
* **`doc_ids`** (List[str]): Document IDs to retrieve
* **`database_name`** (str): Database identifier

#### Returns
* **List[Dict[str, Any]]**: Documents with full content

### `_generate_response_from_documents(query, documents, database_name, token)`

#### Purpose
Generates synthesized response using LLM based on retrieved documents.

#### Parameters
* **`query`** (str): Original user query
* **`documents`** (List[Dict]): Retrieved documents with content
* **`database_name`** (str): Database identifier
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[ResearchResponse, LlmUsageDetails]**: Synthesized response and usage details

### `get_catalog_selection_prompt(query, catalog_json, database_name)` (from catalog_selection_prompt.py)

#### Purpose
Generates the prompt for LLM-based catalog document selection.

#### Parameters
* **`query`** (str): User's search query
* **`catalog_json`** (str): JSON-formatted catalog entries
* **`database_name`** (str): Database identifier

#### Returns
* **str**: Complete prompt for catalog selection

### `get_content_synthesis_prompt(query, formatted_documents, database_name)` (from content_synthesis_prompt.py)

#### Purpose
Generates the prompt for content synthesis from selected documents.

#### Parameters
* **`query`** (str): User's original query
* **`formatted_documents`** (str): Formatted document content
* **`database_name`** (str): Database identifier

#### Returns
* **str**: Complete prompt for synthesis

## Configuration

Settings used from environment configuration:

* **`DATABASE_NAME`**: Specific to each subagent:
  - "internal_aio"
  - "internal_cheatsheets"
  - "internal_compliance"
  - "internal_esg"
  - "internal_ext_reporting_and_disclosure"
  - "internal_global_finance_standards"
  - "internal_icfr"
  - "internal_management_reporting"
  - "internal_memos"
  - "internal_par"
  - "internal_process_and_controls"
  - "internal_wiki"
* **`CATALOG_TABLE`**: Database-specific catalog table name
* **`CONTENT_TABLE`**: Database-specific content table name
* **`CATALOG_MODEL_CAPABILITY`**: "small" - Model for catalog selection
* **`RESPONSE_MODEL_CAPABILITY`**: "large" - Model for synthesis
* **`MAX_RESPONSE_TOKENS`**: 4000 - Maximum tokens for synthesis
* **`RESPONSE_TEMPERATURE`**: 0.7 - Temperature for synthesis

## Usage Examples

### Basic Usage - Metadata Query
```python
from iris.src.agents.database_subagents.internal_wiki.subagent import query_database_sync

# Query for available documents
result, doc_ids = query_database_sync(
    query="expense reporting",
    scope="metadata",
    token=oauth_token
)

# Result contains list of document metadata
for doc in result:
    print(f"Document: {doc['document_name']}")
    print(f"Description: {doc['document_description']}")
```

### Advanced Usage - Research Query with Process Monitoring
```python
from iris.src.agents.database_subagents.internal_compliance.subagent import query_database_sync
from iris.src.initial_setup.process_monitor_setup import ProcessMonitor

# Initialize process monitor
monitor = ProcessMonitor(conversation_id="12345")
monitor.start_stage("compliance_research")

# Perform research query
result, doc_ids = query_database_sync(
    query="What are the SOX compliance requirements for expense reporting?",
    scope="research",
    token=oauth_token,
    process_monitor=monitor,
    query_stage_name="compliance_research"
)

# Access synthesized research
print(result["status_summary"])  # e.g., "✅ Found relevant information"
print(result["detailed_research"])  # Markdown-formatted research
```

## Integration Points

* **Database Router**: Called by `database_router.py` when the respective internal database is selected
* **Process Monitor**: Integrates with process monitoring for tracking LLM usage
* **LLM Connectors**: Uses `rbc_openai.py` for catalog selection and synthesis
* **Database Config**: Uses `db_config.py` for PostgreSQL connections
* **Global Prompts**: Incorporates project, database, fiscal, and restrictions statements

## Dependencies

* **`psycopg2`**: PostgreSQL database connectivity
* **`json`**: JSON parsing for catalog and document formatting
* **Internal modules**: 
  - `initial_setup.env_config`: Environment configuration
  - `initial_setup.db_config`: Database connection management
  - `llm_connectors.rbc_openai`: LLM API calls
  - `global_prompts.*`: Global context statements

## Error Handling

Comprehensive error handling approach:

* **Database Connection Errors**: Caught and logged with appropriate fallback
* **Empty Catalog**: Returns empty results with informative message
* **LLM Selection Errors**: Falls back to empty selection with error status
* **Document Retrieval Errors**: Handles missing documents gracefully
* **Synthesis Errors**: Returns error status with descriptive message
* **JSON Parsing Errors**: Logged with fallback to error response

## Security Considerations

* OAuth token passed through for API authentication
* Database queries use parameterized statements to prevent SQL injection
* Catalog entries sanitized before LLM processing
* No external data sources accessed beyond configured database
* Strict adherence to data sourcing rules in prompts

## Performance Notes

* Catalog loaded once per query for efficiency
* Document selection reduces content retrieval overhead
* Batch document retrieval minimizes database calls
* Process monitoring tracks token usage across all LLM calls
* Configurable token limits prevent excessive usage
* Two-stage approach (selection then synthesis) optimizes LLM usage