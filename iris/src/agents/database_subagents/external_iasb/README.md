# External IASB Subagent (`iris/src/agents/database_subagents/external_iasb/`)

This subfolder contains the implementation of the External IASB Guidance subagent, responsible for querying and synthesizing research from the official IASB external IFRS guidance database, including IAS, IFRS, IFRIC, and SIC documents.

## Files

*   `subagent.py`: Core logic for querying the official IASB external IFRS guidance database. Implements vector search across multiple IASB document IDs, relevance filtering, reranking, section expansion, gap filling, and final response synthesis using LLM calls. Supports both 'metadata' and 'research' query scopes. Integrates with process monitoring for detailed logging.
*   `content_synthesis_prompt.py`: Defines advanced prompt templates for synthesizing content and status from retrieved IASB context cards. Uses the CO-STAR framework and includes global context (project, database, fiscal, restrictions). Enforces strict citation and compliance rules for the LLM synthesis output, with special attention to official IASB standards and interpretations.
*   `__init__.py`: Marks the directory as a Python package.

## Workflow Overview

1.  **Query Embedding Generation**: Converts the user query into an embedding vector using the configured embedding model.
2.  **Vector Search**: Performs vector similarity searches against multiple IASB external IFRS guidance document embeddings (IAS, IFRS, IFRIC, SIC), each with specific top-K limits.
3.  **Summary Relevance Filtering**: Uses an LLM to classify retrieved chunks as relevant or irrelevant based on their summaries.
4.  **Importance Reranking**: Adjusts chunk rankings by combining vector similarity scores with section importance scores.
5.  **Section Expansion**: Expands selected chunks to include all related chunks within the same section if below token thresholds.
6.  **Sequence Gap Filling**: Identifies and fills small gaps in sequence numbers between chunks to ensure continuity.
7.  **Formatting**: Formats the final set of chunks and groups into cards for LLM consumption.
8.  **Response Synthesis**: Uses an LLM with a detailed prompt (from `content_synthesis_prompt.py`) to synthesize a structured research report with inline citations and a status summary flag.
9.  **Result Return**: Returns the synthesized research report and metadata, along with chunk IDs and LLM usage details.

## Integration

This subagent is invoked synchronously by the database router when the official IASB external IFRS guidance database is selected for querying. It adheres to the interface expected by the router, returning results suitable for further summarization or direct response.

The subagent strictly follows compliance and citation guidelines, ensuring all synthesized content is traceable to the official IASB external IFRS guidance database.

---

This README serves as detailed process documentation for the External IASB subagent implementation.
