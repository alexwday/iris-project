# Internal Global Finance Standards Subagent (`iris/src/agents/database_subagents/internal_global_finance_standards/`)

This subfolder contains the implementation of the Internal Global Finance Standards subagent, responsible for querying and synthesizing research from internal RBC Global Finance Standards documents.

## Files

*   `subagent.py`: Core logic for querying the internal Global Finance Standards database asynchronously, including catalog retrieval, document selection, content retrieval, and response synthesis using LLM tool calls. Supports both 'metadata' and 'research' query scopes. Integrates with process monitoring.
*   `catalog_selection_prompt.py`: Defines prompt templates to guide the LLM in selecting relevant Global Finance Standards documents from the catalog based on the user query.
*   `content_synthesis_prompt.py`: Defines advanced prompt templates for synthesizing content and status from retrieved Global Finance Standards document sections. Uses the CO-STAR framework and includes global context (project, database, fiscal, restrictions). Enforces strict citation and compliance rules for the LLM synthesis output.
*   `__init__.py`: Marks the directory as a Python package.

## Workflow Overview

1.  **Catalog Retrieval**: Fetches the full Global Finance Standards catalog from the database.
2.  **Document Selection**: Uses an LLM with a catalog selection prompt to select the most relevant Global Finance Standards documents based on the user query.
3.  **Content Retrieval**: Fetches full content for the selected documents.
4.  **Response Synthesis**: Uses an LLM with a detailed prompt (from `content_synthesis_prompt.py`) to synthesize a structured research report with inline citations and a status summary flag.
5.  **Result Return**: Returns the synthesized research report and metadata, along with selected document IDs and integrates with process monitoring.

## Integration

This subagent is invoked synchronously by the database router when the internal Global Finance Standards database is selected for querying. It adheres to the interface expected by the router, returning results suitable for further summarization or direct response.

The subagent strictly follows compliance and citation guidelines, ensuring all synthesized content is traceable to the source Global Finance Standards documents.

---

This README serves as detailed process documentation for the Internal Global Finance Standards subagent implementation.
