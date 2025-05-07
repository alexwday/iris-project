# Excel Test Summary Tool

This tool processes Excel test files by:

1. Converting each test case row into individual markdown files
2. Using LLM to summarize each test case
3. Generating system-level summaries for each sheet
4. Creating a file-level summary for the entire Excel file
5. Outputting an HTML report with expandable sections for each level of detail

## Usage

```python
python -m excel_test_summary_tool.main input_excel_file.xlsx
```

## Structure

- `excel_processing/`: Functions for loading and parsing Excel files
- `markdown_generator/`: Functions for converting Excel rows to markdown
- `llm_summarization/`: Functions for summarizing test cases using LLM
- `html_output/`: Functions for generating HTML reports
- `results/`: Output directory for generated files
