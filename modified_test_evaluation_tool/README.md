# Test Case Analysis Tool

A standalone tool for analyzing and summarizing test cases from Excel files using LLMs. This tool extracts test cases from Excel sheets, processes them to generate structured summaries, and creates comprehensive reports organized by sheets and test cases.

## Features

- Extract test cases from Excel files (each row typically represents a test case)
- Automatically identify test case numbers and names from column headers
- Generate detailed summaries of each test case using LLM (GPT-4 by default)
- Create structured analysis of test purposes, inputs, and expected results
- Aggregate test cases by sheet and generate executive summaries
- Generate HTML reports with collapsible sections for easy navigation
- Support for both local and RBC environments
- SSL and OAuth configuration from the IRIS project

## Installation

```bash
# Clone the repository
cd /path/to/iris-project/modified_test_evaluation_tool

# Install the package in development mode
pip install -e .
```

## Usage

### Command-line Interface

```bash
# Process Excel files in a directory
evaluate-tests --excel_dir /path/to/excel/files --output_dir ./results

# Additional options
evaluate-tests --excel_dir /path/to/excel/files --model gpt-4 --recursive --sheet "Sheet1"
```

### Python API

```python
from modified_test_evaluation_tool.excel_processing import extract_test_cases
from modified_test_evaluation_tool.summarizer import summarize_test_case, aggregate_summaries
from modified_test_evaluation_tool.oauth import setup_oauth

# Setup authentication
oauth_token = setup_oauth()

# Extract test cases from Excel
test_cases = extract_test_cases("test_cases.xlsx")

# Summarize a test case
summary = summarize_test_case(test_cases[0], oauth_token)

# Aggregate multiple summaries
analysis = aggregate_summaries([summary1, summary2], oauth_token)
```

## Command-line Options

| Option | Description |
|--------|-------------|
| `--excel_dir` | Directory containing Excel test case files (required) |
| `--output_dir` | Directory to save results (default: ./results) |
| `--model` | LLM model to use (default: gpt-4) |
| `--log_file` | Path to log file |
| `--log_level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `--recursive` | Search subdirectories for Excel files |
| `--sheet` | Specific sheet name to process |
| `--rbc_env` | Use RBC environment settings |
| `--use_ssl` | Use SSL for API calls |
| `--use_oauth` | Use OAuth for API authentication |
| `--no_html` | Skip HTML report generation |
| `--html_only` | Convert existing JSON to HTML without running summarization |

## Environment Variables

- `IS_RBC_ENV`: Set to "true" to use RBC environment
- `USE_SSL`: Set to "true" to enable SSL
- `USE_OAUTH`: Set to "true" to use OAuth authentication
- `OPENAI_API_KEY`: Your OpenAI API key (local environment only)

## Excel File Format

The tool expects Excel files with test cases structured as follows:
- Each sheet can contain multiple test cases
- Each row typically represents a separate test case
- The first row is assumed to be a header row with column names
- The tool will look for columns that might contain test case numbers or names
- Common column name patterns recognized:
  - For test case numbers: "Case #", "Case No", "Test #", "Test No", "ID", "TC#"
  - For test case names: "Name", "Title", "Description", "Summary"

## Output Format

### Test Case Summary JSON

```json
{
  "sheet_name": "Sheet1",
  "test_case_number": "TC001",
  "test_case_name": "Verify Login with Valid Credentials",
  "purpose": "Test that users can log in with valid username and password",
  "inputs": "Valid username and password",
  "expected_results": "User should be logged in and redirected to dashboard",
  "observations": "Test is missing specific credential details",
  "comprehensive_summary": "This test verifies the core login functionality...",
  "metadata": {
    "model": "gpt-4",
    "temperature": 0.0,
    "usage": {
      "prompt_tokens": 800,
      "completion_tokens": 250,
      "cost": 0.015
    }
  }
}
```

### Aggregated Test Suite Analysis

The tool generates both JSON and markdown analysis that includes:
1. Executive Summary of the test suite
2. Key areas tested across all test cases
3. Sheet-by-sheet analysis
4. Test coverage assessment
5. Recommendations for improving test cases
6. Detailed summaries for each test case

## HTML Reports

The generated HTML reports include:
- Executive summary section
- Key areas tested
- Recommendations for improvement
- Collapsible sections for each sheet
- Individual test case summaries organized by sheet
- Color-coded indicators for test quality and completeness

## License

Internal use only - RBC Proprietary