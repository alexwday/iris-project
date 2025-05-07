# Test Case Analysis Tool - Quick Start Guide

This quick start guide provides step-by-step instructions to get started with the Test Case Analysis Tool.

## Installation

1. **Clone or download the repository**:
   Make sure you have the test_evaluation_tool directory.

2. **Install the package in development mode**:
   ```bash
   cd /path/to/modified_test_evaluation_tool
   pip install -e .
   ```

## Setting Up Your Environment

### Local Environment

For local development, set your OpenAI API key as an environment variable:

```bash
# macOS/Linux
export OPENAI_API_KEY=your-api-key-here

# Windows
set OPENAI_API_KEY=your-api-key-here
```

Alternatively, you can edit the `oauth/local_auth_settings.py` file to include your API key directly.

### RBC Environment

For RBC environment, you'll need to:

1. Make sure you have the SSL certificate file (`rbc-ca-bundle.cer`) in the ssl directory
2. Update OAuth settings in `oauth/oauth_settings.py` with your credentials
3. Run with the `--rbc_env`, `--use_ssl`, and `--use_oauth` flags

## Example Usage

### Analyzing a Single Excel File

```bash
# Using the command-line tool
analyze-test-cases --excel_dir /path/to/excel/directory --output_dir ./results

# Using the run_evaluation.py script
python run_evaluation.py /path/to/excel/directory --output_dir ./results
```

### Batch Processing Multiple Files

```bash
# Using the command-line tool with recursion
analyze-test-cases --excel_dir /path/to/excel/directory --recursive --output_dir ./results

# Specifying a particular sheet to analyze
analyze-test-cases --excel_dir /path/to/excel/directory --sheet "Test Cases" --output_dir ./results
```

## Expected Output

The tool generates:

1. **Markdown files** of the extracted test cases
2. **JSON files** with structured test case summaries
3. **HTML reports** with collapsible sections for easy navigation
4. **Aggregated analysis files**:
   - `test_suite_analysis.json`: Structured analysis data
   - `test_suite_analysis.md`: Human-readable markdown summary
   - `*_test_summary.html`: Interactive HTML report with all test cases

## Troubleshooting

If you encounter errors:

1. **SSL Certificate Issues**:
   - Ensure the certificate file exists and is valid
   - Try running without SSL for local testing

2. **Authentication Failures**:
   - Check your API key or OAuth credentials
   - Verify connectivity to the API endpoint

3. **Excel Processing Errors**:
   - Ensure Excel files have header rows with column names
   - Each row should represent a test case
   - Check that pandas and openpyxl are properly installed

4. **General Errors**:
   - Check the logs for detailed error messages
   - Run with `--log_level DEBUG` for more verbose output

## Need Help?

For more detailed documentation, refer to the full README.md file or the source code docstrings.