# Internal CAPM Subagent (`iris/src/agents/database_subagents/internal_capm/`)

This subfolder contains the implementation of the Internal CAPM (Central Accounting Policy Manual) subagent, responsible for querying and synthesizing research from internal RBC accounting policy manuals.

## Files

*   `subagent.py`: Core logic for querying the internal CAPM database. Implements a multi-step process including catalog retrieval, document selection, section selection, content retrieval, and final response synthesis using LLM calls. Supports both 'metadata' and 'research' query scopes. Integrates with process monitoring for detailed logging.
*   `catalog_selection_prompt.py`: Defines prompt templates to guide the LLM in selecting relevant CAPM documents from the catalog based on the user query.
*   `section_selection_prompt.py`: Defines prompt templates to guide the LLM in selecting relevant sections from CAPM documents based on section summaries.
*   `content_synthesis_prompt.py`: Defines advanced prompt templates for synthesizing content and status from retrieved CAPM document sections. Uses the CO-STAR framework and includes global context (project, database, fiscal, restrictions). Enforces strict citation and compliance rules for the LLM synthesis output.
*   `description_condensation_prompt.py`: (Not yet reviewed) Presumably contains prompts for condensing descriptions, likely used in catalog or section summarization.
*   `__init__.py`: Marks the directory as a Python package.

## Workflow Overview

1.  **Catalog Retrieval**: Fetches the full CAPM catalog from the database.
2.  **Document Selection**: Uses an LLM with a catalog selection prompt to select the most relevant CAPM documents based on the user query.
3.  **Section Retrieval**: Fetches sections and summaries for the selected documents.
4.  **Section Selection**: Uses an LLM with a section selection prompt to select the most relevant sections based on summaries.
5.  **Content Retrieval**: Fetches full content for the selected sections.
6.  **Response Synthesis**: Uses an LLM with a detailed prompt (from `content_synthesis_prompt.py`) to synthesize a structured research report with inline citations and a status summary flag.
7.  **Result Return**: Returns the synthesized research report and metadata, along with selected document IDs and integrates with process monitoring.

## Integration

This subagent is invoked synchronously by the database router when the internal CAPM database is selected for querying. It adheres to the interface expected by the router, returning results suitable for further summarization or direct response.

The subagent strictly follows compliance and citation guidelines, ensuring all synthesized content is traceable to the source CAPM documents.

---

This README serves as detailed process documentation for the Internal CAPM subagent implementation.
