# Test Evaluation Tool

A standalone tool for evaluating IRIS test results using LLM judgments. This tool takes Excel sheets containing test questions, expected results, and reviewer notes, and processes them to generate structured evaluations and summaries.

## Features

- Convert Excel test results to markdown format
- Evaluate test results using LLM (GPT-4 by default)
- Generate structured JSON evaluations for each test
- Aggregate evaluations into comprehensive summaries
- Support for both local and RBC environments
- SSL and OAuth configuration from the IRIS project

## Installation

```bash
# Clone the repository
cd /path/to/iris-project/test_evaluation_tool

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
from test_evaluation_tool.excel_processing import excel_to_markdown
from test_evaluation_tool.judge import evaluate_test_result, aggregate_evaluations
from test_evaluation_tool.oauth import setup_oauth

# Setup authentication
oauth_token = setup_oauth()

# Convert Excel to markdown
markdown = excel_to_markdown("test_results.xlsx")

# Evaluate a test result
evaluation = evaluate_test_result(markdown, oauth_token)

# Aggregate multiple evaluations
summary = aggregate_evaluations([evaluation1, evaluation2], oauth_token)
```

## Command-line Options

| Option | Description |
|--------|-------------|
| `--excel_dir` | Directory containing Excel test files (required) |
| `--output_dir` | Directory to save results (default: ./results) |
| `--model` | LLM model to use (default: gpt-4) |
| `--log_file` | Path to log file |
| `--log_level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `--recursive` | Search subdirectories for Excel files |
| `--sheet` | Specific sheet name to process |
| `--rbc_env` | Use RBC environment settings |
| `--use_ssl` | Use SSL for API calls |
| `--use_oauth` | Use OAuth for API authentication |

## Environment Variables

- `IS_RBC_ENV`: Set to "true" to use RBC environment
- `USE_SSL`: Set to "true" to enable SSL
- `USE_OAUTH`: Set to "true" to use OAuth authentication
- `OPENAI_API_KEY`: Your OpenAI API key (local environment only)

## Excel File Format

The tool expects Excel files with test results in the following format:
- Column A: Test data (questions, context, or test descriptions)
- Column B: The expected results or IRIS's responses
- Column C: Reviewer notes, scores, and feedback

## Output Format

### Evaluation JSON

```json
{
  "database_selection": {
    "correct": true,
    "comments": "Based on reviewer notes"
  },
  "document_selection": {
    "correct": true,
    "comments": "Based on reviewer notes"
  },
  "answer_accuracy": {
    "score": 4,
    "comments": "Based on reviewer notes"
  },
  "overall_assessment": "Short summary of the test result",
  "metadata": {
    "model": "gpt-4",
    "temperature": 0.0,
    "usage": {
      "prompt_tokens": 1200,
      "completion_tokens": 300,
      "cost": 0.018
    }
  }
}
```

### Aggregated Summary

The tool generates both JSON and markdown summaries that include:
1. Overall Performance
2. Database Selection Accuracy
3. Document Selection Accuracy 
4. Answer Accuracy
5. Key Strengths
6. Key Weaknesses
7. Quantitative Summary

## License

Internal use only - RBC Proprietary