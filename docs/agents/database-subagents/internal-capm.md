# Internal CAPM Subagent (`iris/src/agents/database_subagents/internal_capm/`)

Specialized subagent for querying and synthesizing research from internal RBC CAPM (Central Accounting Policy Manual) documents, implementing unique multi-step section-level selection for handling large, complex accounting policy documents.

## Overview

The Internal CAPM subagent implements a unique 3-step process that differs significantly from standard internal subagents. Unlike other internal subagents that use simple catalog selection followed by content synthesis, CAPM handles large accounting policy documents by adding an intermediate section selection step. This granular approach optimizes token usage while maintaining high relevance for complex accounting queries that often target specific policy areas within extensive documents.

## Key Components

* **`subagent.py`**: Core query processing logic implementing the unique 3-step selection and synthesis pipeline
* **`catalog_selection_prompt.py`**: Prompt template for initial document selection from catalog (more inclusive than standard)
* **`section_selection_prompt.py`**: Unique prompt template for selecting specific sections based on summaries
* **`content_synthesis_prompt.py`**: Advanced prompt template for synthesizing content from selected sections
* **`description_condensation_prompt.py`**: Utility prompt for condensing detailed descriptions to plain text summaries
* **`__init__.py`**: Python package initialization

## Core Functions/Classes

### `query_database_sync(query, scope, token, process_monitor, query_stage_name)`

#### Purpose
Main entry point for synchronously querying the CAPM database using the unique 3-step process.

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
2. **Execute Logic**: Call `_query_database_logic` for 3-step processing
3. **Process Usage**: Track LLM usage details through process monitor
4. **Handle Results**: Return results with document IDs

### `_query_database_logic(query, scope, token)`

#### Purpose
Internal logic implementing the unique 3-step query processing pipeline.

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

##### Research Scope (Unique 3-Step Process):
1. **Load Catalog**: Retrieve available documents
2. **Select Documents**: Use LLM to select relevant documents (up to 5)
3. **Fetch Section Summaries**: Retrieve section metadata and summaries for selected documents
4. **Select Sections**: Use LLM to select specific sections based on summaries
5. **Fetch Section Content**: Retrieve full content only for selected sections
6. **Generate Response**: Use LLM to synthesize research from selected section content

### `fetch_document_sections_and_summaries(cursor, selected_doc_ids, database_name)`

#### Purpose
Retrieves section metadata and summaries for selected documents to enable section-level selection.

#### Parameters
* **`cursor`**: Database cursor
* **`selected_doc_ids`** (List[str]): Document IDs to fetch sections for
* **`database_name`** (str): Database identifier

#### Returns
* **Dict[str, List[Dict]]**: Document names mapped to their section summaries

### `select_relevant_sections(query, documents_with_summaries, database_name, token)`

#### Purpose
Uses LLM to select specific sections based on summaries, providing granular content filtering.

#### Parameters
* **`query`** (str): User's search query
* **`documents_with_summaries`** (Dict): Documents with section summaries
* **`database_name`** (str): Database identifier
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[Dict[str, List[str]], LlmUsageDetails]**: Selected sections per document and usage details

#### Workflow
1. **Format Summaries**: Prepare section summaries for LLM analysis
2. **Generate Prompt**: Create section selection prompt with context awareness
3. **LLM Selection**: Use small model to select relevant sections
4. **Parse Response**: Extract section IDs per document
5. **Validate IDs**: Ensure section IDs are valid integers

### `fetch_section_content(cursor, section_selections, database_name)`

#### Purpose
Retrieves full content only for the sections selected in the previous step.

#### Parameters
* **`cursor`**: Database cursor
* **`section_selections`** (Dict[str, List[str]]): Selected sections per document
* **`database_name`** (str): Database identifier

#### Returns
* **List[Dict[str, Any]]**: Documents with content for selected sections only

## Configuration

Settings used from environment configuration:

* **`DATABASE_NAME`**: "internal_capm" - Database identifier
* **`CATALOG_TABLE`**: Database-specific catalog table name
* **`CONTENT_TABLE`**: Database-specific content table name
* **`CATALOG_MODEL_CAPABILITY`**: "small" - Model for catalog and section selection
* **`RESPONSE_MODEL_CAPABILITY`**: "large" - Model for synthesis
* **`MAX_RESPONSE_TOKENS`**: 4000 - Maximum tokens for synthesis
* **`RESPONSE_TEMPERATURE`**: 0.7 - Temperature for synthesis
* **`MAX_DOCUMENTS`**: 5 - Maximum documents to select in catalog phase

## Usage Examples

### Basic Usage - Metadata Query
```python
from iris.src.agents.database_subagents.internal_capm.subagent import query_database_sync

# Query for available CAPM documents
result, doc_ids = query_database_sync(
    query="lease accounting policy",
    scope="metadata",
    token=oauth_token
)

# Result contains list of document metadata
for doc in result:
    print(f"Document: {doc['document_name']}")
    print(f"Description: {doc['document_description']}")
```

### Advanced Usage - Research Query with Section Selection
```python
from iris.src.agents.database_subagents.internal_capm.subagent import query_database_sync
from iris.src.initial_setup.process_monitor_setup import ProcessMonitor

# Initialize process monitor
monitor = ProcessMonitor(conversation_id="12345")
monitor.start_stage("capm_research_query")

# Perform research query with 3-step process
result, doc_ids = query_database_sync(
    query="What are the recognition criteria for right-of-use assets under IFRS 16?",
    scope="research",
    token=oauth_token,
    process_monitor=monitor,
    query_stage_name="capm_research_query"
)

# Access synthesized research from selected sections
print(result["status_summary"])  # e.g., "✅ Found specific policy guidance"
print(result["detailed_research"])  # Markdown-formatted research from selected sections
```

## Integration Points

* **Database Router**: Called by `database_router.py` when CAPM database is selected
* **Process Monitor**: Integrates with process monitoring for multi-step LLM usage tracking
* **LLM Connectors**: Uses `rbc_openai.py` for catalog selection, section selection, and synthesis
* **Database Config**: Uses `db_config.py` for PostgreSQL connections
* **Global Prompts**: Incorporates project, database, fiscal, and restrictions statements

## Dependencies

* **`psycopg2`**: PostgreSQL database connectivity
* **`json`**: JSON parsing for section selections and document formatting
* **Internal modules**: 
  - `initial_setup.env_config`: Environment configuration
  - `initial_setup.db_config`: Database connection management
  - `llm_connectors.rbc_openai`: LLM API calls
  - `global_prompts.*`: Global context statements

## Error Handling

Comprehensive error handling approach:

* **Section ID Validation**: Converts string section IDs to integers with error handling
* **Empty Selection Handling**: Filters out documents with no selected sections
* **Database Connection Errors**: Caught and logged with appropriate fallback
* **LLM Selection Errors**: Handles JSON parsing errors and invalid selections
* **Content Retrieval Errors**: Manages missing sections gracefully
* **Multi-Step Failures**: Each step can fail independently with appropriate error responses

## Security Considerations

* OAuth token passed through for API authentication
* Database queries use parameterized statements to prevent SQL injection
* Section ID validation prevents unauthorized data access
* Multi-step selection process includes validation at each stage
* Strict adherence to data sourcing rules in all prompts

## Performance Notes

* **Token Optimization**: Section selection reduces synthesis token usage by 60-80%
* **Database Efficiency**: Separate queries for summaries vs. content reduce data transfer
* **Selective Content Retrieval**: Only fetches content for relevant sections
* **Multi-Step LLM Usage**: Uses small model for selection, large model for synthesis
* **Process Monitoring**: Tracks usage across all three steps for cost optimization
* **Section-Level Granularity**: Enables precise targeting of large document content

## Unique Features

This CAPM subagent differs from all other internal subagents in several key ways:

* **3-Step Process**: Unique catalog → section → synthesis workflow
* **Section-Level Selection**: Granular content filtering based on summaries
* **Summary-Based Pre-filtering**: Uses section summaries for intelligent selection
* **Context-Aware Selection**: Accounting standard and context identification
* **Token Optimization**: Designed specifically for large document handling
* **Description Condensation**: Utility for converting detailed descriptions to summaries
* **Enhanced Validation**: Multi-level filtering and section ID validation
* **Document Size Optimization**: Handles extensive accounting policy manuals efficiently
