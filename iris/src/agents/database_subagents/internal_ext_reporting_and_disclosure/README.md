# Internal External Reporting and Disclosure Subagent (`iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/`)

This subfolder contains the implementation of the Internal External Reporting and Disclosure subagent, responsible for querying and synthesizing research from internal RBC External Reporting and Disclosure documents.

## Files

*   `subagent.py`: Core logic for querying the internal External Reporting and Disclosure database asynchronously, including catalog retrieval, document selection, content retrieval, and response synthesis using LLM tool calls. Supports both 'metadata' and 'research' query scopes. Integrates with process monitoring.
*   `catalog_selection_prompt.py`: Defines prompt templates to guide the LLM in selecting relevant External Reporting and Disclosure documents from the catalog based on the user query.
*   `content_synthesis_prompt.py`: Defines advanced prompt templates for synthesizing content and status from retrieved External Reporting and Disclosure document sections. Uses the CO-STAR framework and includes global context (project, database, fiscal, restrictions). Enforces strict citation and compliance rules for the LLM synthesis output.
*   `__init__.py`: Marks the directory as a Python package.

## Workflow Overview

1.  **Catalog Retrieval**: Fetches the full External Reporting and Disclosure catalog from the database.
2.  **Document Selection**: Uses an LLM with a catalog selection prompt to select the most relevant External Reporting and Disclosure documents based on the user query.
3.  **Content Retrieval**: Fetches full content for the selected documents.
4.  **Response Synthesis**: Uses an LLM with a detailed prompt (from `content_synthesis_prompt.py`) to synthesize a structured research report with inline citations and a status summary flag.
5.  **Result Return**: Returns the synthesized research report and metadata, along with selected document IDs and integrates with process monitoring.

## Integration

This subagent is invoked synchronously by the database router when the internal External Reporting and Disclosure database is selected for querying. It adheres to the interface expected by the router, returning results suitable for further summarization or direct response.

The subagent strictly follows compliance and citation guidelines, ensuring all synthesized content is traceable to the source External Reporting and Disclosure documents.

---

This README serves as detailed process documentation for the Internal External Reporting and Disclosure subagent implementation.
