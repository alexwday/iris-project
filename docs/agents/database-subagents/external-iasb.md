# External IASB Subagent (`iris/src/agents/database_subagents/external_iasb/`)

Specialized subagent for querying and synthesizing research from the official IASB (International Accounting Standards Board) guidance database, implementing multi-document search across IAS, IFRS, IFRIC, and SIC standards.

## Overview

The External IASB subagent handles queries to official IASB accounting standards and interpretations stored in the vector database. Unlike other external subagents that query single documents, this subagent searches across multiple IASB document types with different priority levels. It performs sophisticated multi-stage processing including vector search across multiple documents, relevance filtering, importance reranking, section expansion, gap filling, and LLM-based synthesis.

## Key Components

* **`subagent.py`**: Core query processing logic implementing multi-document retrieval and synthesis pipeline
* **`content_synthesis_prompt.py`**: Advanced prompt templates using CO-STAR framework for synthesizing official IASB content
* **`__init__.py`**: Python package initialization

## Core Functions/Classes

### `query_database_sync(query, scope, token, process_monitor, query_stage_name)`

#### Purpose
Main entry point for synchronously querying the IASB database across multiple document types.

#### Parameters
* **`query`** (str): The search query to execute
* **`scope`** (str): Query scope - either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token for API access
* **`process_monitor`** (optional): Process monitor for tracking token usage
* **`query_stage_name`** (str, optional): Specific stage name for this query instance

#### Returns
* **SubagentResult**: Tuple containing:
  - DatabaseResponse: Query results (MetadataResponse list or ResearchResponse dict)
  - Optional[List[str]]: List of chunk IDs from all processed documents

#### Workflow
1. **Initialize**: Set up logging and process monitoring
2. **Execute Logic**: Call `_query_database_logic` for multi-document processing
3. **Process Usage**: Track LLM usage details through process monitor
4. **Handle Results**: Return combined results from all documents

### `_query_database_logic(query, scope, token)`

#### Purpose
Internal logic implementing the complete multi-document query processing pipeline.

#### Parameters
* **`query`** (str): The search query
* **`scope`** (str): Either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token

#### Returns
* **LogicResult**: Tuple containing:
  - DatabaseResponse: Combined query results
  - Optional[List[str]]: Initial chunk IDs from all documents
  - Optional[List[str]]: Final chunk IDs (after processing)
  - List[LlmUsageDetails]: Collected LLM usage details

#### Workflow
##### Metadata Scope:
1. **Generate Embedding**: Create query embedding vector
2. **Multi-Document Search**: Search across all IASB document types
3. **Extract Sections**: Get unique sections from all results
4. **Format Response**: Return combined section metadata list

##### Research Scope:
1. **Generate Embedding**: Create query embedding vector
2. **Process Each Document**: Use `_process_single_document_id` for each IASB document type
3. **Combine Results**: Merge processed results from all documents
4. **Format Cards**: Prepare context cards for synthesis (with Source Document ID)
5. **Generate Response**: Use LLM for final synthesis of combined content

### `_process_single_document_id(cursor, query_embedding, doc_id, initial_k, query, token)`

#### Purpose
Processes a single IASB document type through the complete retrieval and refinement pipeline.

#### Parameters
* **`cursor`**: Database cursor
* **`query_embedding`** (List[float]): Query embedding vector
* **`doc_id`** (str): Specific IASB document ID to process
* **`initial_k`** (int): Number of initial results to retrieve for this document
* **`query`** (str): Original query for relevance filtering
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple**: Processed results and collected usage details for this document

#### Workflow
1. **Vector Search**: Search with specific document ID filter
2. **Relevance Filter**: Use LLM to filter by summary relevance
3. **Rerank**: Adjust rankings using importance scores
4. **Expand Sections**: Include full sections for token thresholds
5. **Fill Gaps**: Add missing chunks between sequences

### `_format_chunks_as_cards(results)`

#### Purpose
Formats final results into context cards for LLM consumption, including source document ID.

#### Parameters
* **`results`** (List[Union[dict, List[dict]]]): Processed results to format

#### Returns
* **str**: Formatted context cards string with IASB-specific fields

## Configuration

Settings used from environment configuration:

* **`DATABASE_NAME`**: "external_iasb" - Database identifier
* **`TARGET_TABLE`**: "iris_textbook_database" - Vector search table
* **`IASB_DOC_CONFIG`**: Multi-document configuration with different K values:
  - "iasb_ias": 20 (International Accounting Standards)
  - "iasb_ifrs": 20 (International Financial Reporting Standards)
  - "iasb_ifrics": 10 (IFRS Interpretations Committee)
  - "iasb_sic": 10 (Standards Interpretations Committee)
* **`EMBEDDING_DIMENSIONS`**: 2000 - Embedding vector dimensions
* **`IMPORTANCE_FACTOR`**: 0.2 - Weight for importance reranking
* **`SECTION_EXPANSION_TOP_K_RANK`**: 5 - Top K threshold for expansion
* **`SECTION_EXPANSION_TOP_K_TOKENS`**: 8000 - Token limit for top K
* **`SECTION_EXPANSION_GENERAL_TOKENS`**: 4000 - General token limit
* **`GAP_FILL_MAX_SEQUENCE_GAP`**: 8 - Maximum sequence gap to fill
* **`MAX_RESPONSE_TOKENS`**: 4000 - Max tokens for synthesis
* **`RESPONSE_TEMPERATURE`**: 0.7 - Temperature for synthesis

## Usage Examples

### Basic Usage - Metadata Query
```python
from iris.src.agents.database_subagents.external_iasb.subagent import query_database_sync

# Query for IASB standards related to leases
result, chunk_ids = query_database_sync(
    query="lease accounting requirements",
    scope="metadata",
    token=oauth_token
)

# Result contains sections from multiple IASB documents
for section in result:
    print(f"Standard: {section['document_name']}")
    print(f"Source: {section['source_document_id']}")
    print(f"Description: {section['document_description']}")
```

### Advanced Usage - Research Query
```python
from iris.src.agents.database_subagents.external_iasb.subagent import query_database_sync
from iris.src.initial_setup.process_monitor_setup import ProcessMonitor

# Initialize process monitor
monitor = ProcessMonitor(conversation_id="12345")
monitor.start_stage("iasb_research_query")

# Perform research query across all IASB document types
result, chunk_ids = query_database_sync(
    query="What are the recognition criteria for financial assets under IFRS 9?",
    scope="research",
    token=oauth_token,
    process_monitor=monitor,
    query_stage_name="iasb_research_query"
)

# Access synthesized research from multiple IASB sources
print(result["status_summary"])  # e.g., "✅ Found information across multiple IASB standards"
print(result["detailed_research"])  # Markdown-formatted research with source document citations
```

## Integration Points

* **Database Router**: Called by `database_router.py` when IASB database is selected
* **Process Monitor**: Integrates with process monitoring for multi-document usage tracking
* **LLM Connectors**: Uses `rbc_openai.py` for all LLM calls across multiple documents
* **Database Config**: Uses `db_config.py` for PostgreSQL connections with pgvector support
* **Global Prompts**: Incorporates project, database, fiscal, and restrictions statements

## Dependencies

* **`psycopg2`**: PostgreSQL database connectivity
* **`pgvector`**: Vector similarity search support
* **`tabulate`**: Optional dependency for formatted log tables
* **Internal modules**: 
  - `initial_setup.env_config`: Environment configuration
  - `initial_setup.db_config`: Database connection management
  - `llm_connectors.rbc_openai`: LLM API calls
  - `global_prompts.*`: Global context statements

## Error Handling

Comprehensive error handling approach:

* **Multi-Document Failures**: Continues processing other documents if one fails
* **Embedding Generation Failures**: Returns appropriate error response based on scope
* **Database Connection Errors**: Caught and logged with rollback support
* **Vector Search Failures**: Returns partial results if some documents succeed
* **LLM API Errors**: Handles JSON parsing errors and missing responses gracefully
* **Synthesis Errors**: Falls back to error status with descriptive messages

## Security Considerations

* OAuth token passed through for API authentication
* Database queries use parameterized statements to prevent SQL injection
* Sensitive information truncated in logs
* Strict data sourcing rules enforced for official IASB standards
* Source document tracking for compliance and traceability

## Performance Notes

* Multi-document search optimized with different K values per document type
* Document-specific processing reduces overall token usage
* Relevance filtering applied per document before combining
* Process monitoring tracks usage across all IASB document types
* Combined synthesis minimizes final LLM calls
* Results include source document ID for efficient citation tracking

## Unique Features

This IASB subagent differs from other external subagents in several key ways:

* **Multi-Document Architecture**: Searches across 4 different IASB document types
* **Document-Specific K Values**: Different retrieval limits for different standard types
* **Source Document Tracking**: Includes source document ID in formatted cards
* **Combined Processing**: Merges results from multiple documents before synthesis
* **IASB-Specific Prompting**: Tailored for official accounting standards and interpretations
