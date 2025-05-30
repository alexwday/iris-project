# External Database Subagents (`iris/src/agents/database_subagents/external_*/`)

Standardized implementation for external database subagents (EY, PwC, KPMG) that query and synthesize research from external IFRS guidance databases using advanced vector search and content synthesis.

## Overview

The external database subagents (external_ey, external_pwc, external_kpmg) share identical implementation logic for handling queries to external accounting guidance content stored in the vector database. Each performs sophisticated multi-stage processing including vector search, relevance filtering, importance reranking, section expansion, gap filling, and LLM-based synthesis. All subagents support both 'metadata' scope (for document discovery) and 'research' scope (for detailed content synthesis) queries, ensuring synthesized content includes proper inline citations traceable to source documents.

The only differences between implementations are:
- **Database name**: external_ey, external_pwc, or external_kpmg
- **Document ID**: Specific to each provider's content

## Key Components

* **`subagent.py`**: Core query processing logic implementing the multi-stage retrieval and synthesis pipeline
* **`content_synthesis_prompt.py`**: Advanced prompt templates using CO-STAR framework for content synthesis with strict citation requirements
* **`__init__.py`**: Python package initialization

## Core Functions/Classes

### `query_database_sync(query, scope, token, process_monitor, query_stage_name)`

#### Purpose
Main entry point for synchronously querying the external database, handling both metadata and research scopes.

#### Parameters
* **`query`** (str): The search query to execute
* **`scope`** (str): Query scope - either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token for API access
* **`process_monitor`** (optional): Process monitor for tracking token usage
* **`query_stage_name`** (str, optional): Specific stage name for this query instance

#### Returns
* **SubagentResult**: Tuple containing:
  - DatabaseResponse: Query results (MetadataResponse list or ResearchResponse dict)
  - Optional[List[str]]: List of initial chunk IDs used in the search

#### Workflow
1. **Initialize**: Set up logging and process monitoring stage
2. **Execute Logic**: Call `_query_database_logic` to perform the actual query
3. **Process Usage**: Track LLM usage details through process monitor
4. **Handle Results**: Return results with appropriate chunk IDs

#### Error Handling
* **Database Errors**: Logged and returned with appropriate error status
* **Connection Errors**: Handled with fallback to error response
* **Unexpected Errors**: Caught and logged with stack trace

### `_query_database_logic(query, scope, token)`

#### Purpose
Internal logic implementing the complete query processing pipeline for both metadata and research scopes.

#### Parameters
* **`query`** (str): The search query
* **`scope`** (str): Either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token

#### Returns
* **LogicResult**: Tuple containing:
  - DatabaseResponse: Query results
  - Optional[List[str]]: Initial chunk IDs
  - Optional[List[str]]: Final chunk IDs (after expansion/filtering)
  - List[LlmUsageDetails]: Collected LLM usage details

#### Workflow
##### Metadata Scope:
1. **Generate Embedding**: Create query embedding vector
2. **Vector Search**: Search with document ID filter
3. **Extract Sections**: Get unique sections from results
4. **Format Response**: Return section metadata list

##### Research Scope:
1. **Generate Embedding**: Create query embedding vector
2. **Initial Search**: Perform vector similarity search (top K=20)
3. **Relevance Filter**: Use LLM to filter by summary relevance
4. **Rerank**: Adjust rankings using importance scores
5. **Expand Sections**: Include full sections for token thresholds
6. **Fill Gaps**: Add missing chunks between sequences
7. **Format Cards**: Prepare context cards for synthesis
8. **Generate Response**: Use LLM for final synthesis

### `_generate_query_embedding(query, token)`

#### Purpose
Generates embedding vector for the query using the configured embedding model.

#### Parameters
* **`query`** (str): Query text to embed
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[Optional[List[float]], LlmUsageDetails]**: Embedding vector and usage details

### `_perform_vector_search(cursor, query_embedding, initial_k, doc_id)`

#### Purpose
Performs vector similarity search against document embeddings with optional document ID filtering.

#### Parameters
* **`cursor`**: Database cursor
* **`query_embedding`** (List[float]): Query embedding vector
* **`initial_k`** (int): Number of results to retrieve
* **`doc_id`** (str, optional): Document ID filter

#### Returns
* **List[Dict[str, Any]]**: Search results with vector scores and ranks

### `_filter_by_summary_relevance(query, results, token)`

#### Purpose
Uses LLM to classify chunk summaries as relevant or irrelevant to the query.

#### Parameters
* **`query`** (str): Original user query
* **`results`** (List[dict]): Search results to filter
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[List[dict], dict, LlmUsageDetails]**: Filtered results, relevance map, and usage details

### `_rerank_by_importance(results, importance_factor)`

#### Purpose
Reranks results by combining vector similarity scores with section importance scores.

#### Parameters
* **`results`** (List[dict]): Results to rerank
* **`importance_factor`** (float): Weight factor for importance scores (0.2)

#### Returns
* **List[dict]**: Reranked results with updated scores and ranks

### `_expand_sections_by_token_count(cursor, results, top_k_rank, top_k_tokens, general_tokens)`

#### Purpose
Expands chunks to include full sections when section token count is below thresholds.

#### Parameters
* **`cursor`**: Database cursor
* **`results`** (List[dict]): Results to potentially expand
* **`top_k_rank`** (int): Rank threshold for stricter token limit (5)
* **`top_k_tokens`** (int): Token threshold for top K results (8000)
* **`general_tokens`** (int): Token threshold for other results (4000)

#### Returns
* **Tuple[List[Union[dict, List[dict]]], set]**: Processed results with groups and added chunk IDs

### `_fill_sequence_gaps(cursor, results, max_seq_gap)`

#### Purpose
Identifies and fills small sequence number gaps between consecutive chunks for continuity.

#### Parameters
* **`cursor`**: Database cursor
* **`results`** (List[Union[dict, List[dict]]]): Results to process
* **`max_seq_gap`** (int): Maximum sequence gap to fill (8)

#### Returns
* **Tuple[List[Union[dict, List[dict]]], set]**: Results with gaps filled and added chunk IDs

### `_format_chunks_as_cards(results)`

#### Purpose
Formats final results into context cards for LLM consumption.

#### Parameters
* **`results`** (List[Union[dict, List[dict]]]): Processed results to format

#### Returns
* **str**: Formatted context cards string

### `_generate_response_from_chunks(query, formatted_chunks, token)`

#### Purpose
Generates final synthesized response using LLM tool call with formatted chunks.

#### Parameters
* **`query`** (str): Original user query
* **`formatted_chunks`** (str): Formatted context cards
* **`token`** (str, optional): Authentication token

#### Returns
* **Tuple[ResearchResponse, LlmUsageDetails]**: Synthesized response and usage details

### `get_content_synthesis_prompt(query, formatted_cards)` (from content_synthesis_prompt.py)

#### Purpose
Generates the complete synthesis prompt using CO-STAR framework with global context.

#### Parameters
* **`query`** (str): User's original query
* **`formatted_cards`** (str): Formatted context cards

#### Returns
* **str**: Complete prompt for synthesis LLM call

## Configuration

Settings used from environment configuration:

* **`DATABASE_NAME`**: Provider-specific identifier:
  - "external_ey" for EY subagent
  - "external_pwc" for PwC subagent
  - "external_kpmg" for KPMG subagent
* **`TARGET_TABLE`**: "iris_textbook_database" - Vector search table (same for all)
* **`DOCUMENT_ID`**: Provider-specific document identifier:
  - "ey_international_gaap_2024" for EY
  - "pwc_ca_ifrs_manual" for PwC
  - "kpmg_insights_into_ifrs_20th_edition" for KPMG
* **`EMBEDDING_DIMENSIONS`**: 2000 - Embedding vector dimensions
* **`INITIAL_K`**: 20 - Initial vector search results
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
from iris.src.agents.database_subagents.external_ey.subagent import query_database_sync
# Or: from iris.src.agents.database_subagents.external_pwc.subagent import query_database_sync
# Or: from iris.src.agents.database_subagents.external_kpmg.subagent import query_database_sync

# Query for document sections related to leases
result, chunk_ids = query_database_sync(
    query="lease accounting under IFRS 16",
    scope="metadata",
    token=oauth_token
)

# Result contains list of section metadata
for section in result:
    print(f"Section: {section['document_name']}")
    print(f"Description: {section['document_description']}")
```

### Advanced Usage - Research Query with Process Monitoring
```python
from iris.src.agents.database_subagents.external_pwc.subagent import query_database_sync
from iris.src.initial_setup.process_monitor_setup import ProcessMonitor

# Initialize process monitor
monitor = ProcessMonitor(conversation_id="12345")
monitor.start_stage("pwc_research_query")

# Perform research query
result, chunk_ids = query_database_sync(
    query="What are the disclosure requirements for lessees under IFRS 16?",
    scope="research",
    token=oauth_token,
    process_monitor=monitor,
    query_stage_name="pwc_research_query"
)

# Access synthesized research
print(result["status_summary"])  # e.g., "✅ Found information directly addressing the query"
print(result["detailed_research"])  # Markdown-formatted research with inline citations
```

## Integration Points

* **Database Router**: Called by `database_router.py` when the respective external database is selected
* **Process Monitor**: Integrates with process monitoring for tracking LLM usage and performance
* **LLM Connectors**: Uses `rbc_openai.py` for all LLM calls (embeddings, relevance, synthesis)
* **Database Config**: Uses `db_config.py` for PostgreSQL connections with pgvector support
* **Global Prompts**: Incorporates project, database, fiscal, and restrictions statements in synthesis

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

* **Embedding Generation Failures**: Returns appropriate error response based on scope
* **Database Connection Errors**: Caught and logged with rollback support
* **Vector Search Failures**: Returns empty results with error logging
* **LLM API Errors**: Handles JSON parsing errors and missing responses gracefully
* **Synthesis Errors**: Falls back to error status with descriptive messages
* **Process Monitor Errors**: Isolated to prevent disruption of main query flow

## Security Considerations

* OAuth token passed through for API authentication
* Database queries use parameterized statements to prevent SQL injection
* Sensitive information truncated in logs
* Strict data sourcing rules enforced in synthesis prompts
* No external knowledge introduction beyond provided context cards

## Performance Notes

* Vector search optimized with pgvector indexing
* Relevance filtering reduces downstream processing
* Section expansion and gap filling minimize LLM calls
* Process monitoring tracks token usage for cost optimization
* Configurable token limits prevent excessive LLM usage
* Results sorted by sequence for efficient card formatting