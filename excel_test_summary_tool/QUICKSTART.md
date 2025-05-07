# Excel Test Summary Tool - Quick Start Guide

This tool processes Excel test files and generates a hierarchical HTML summary report using LLM to analyze test cases.

## Setup

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key:

```bash
# Option 1: Set environment variable
export OPENAI_API_KEY=your_api_key_here

# Option 2: Pass as command-line argument
# (See the Usage section below)
```

## Usage

Run the tool on your Excel file:

```bash
# Using the environment variable for API key
python run_summary.py path/to/your/excel_file.xlsx

# Or specify the API key directly
python run_summary.py path/to/your/excel_file.xlsx --api-key your_api_key_here
```

### Additional Options

```bash
# Specify a different output file
python run_summary.py path/to/your/excel_file.xlsx --output custom_report.html

# Use a different LLM model
python run_summary.py path/to/your/excel_file.xlsx --model gpt-3.5-turbo
```

## Expected Excel Format

The tool is designed to work with Excel files where:

- Each sheet represents a different system
- The first row contains headers
- Each subsequent row is a test case
- Common fields include "Sr.No", "Test Case Name", "Navigation", "Test Description", "Expected Results", etc.

The tool will adapt to whatever headers are available in each sheet.

## Output

The tool generates:

1. Individual markdown files for each test case
2. LLM-generated summaries for each test case
3. System-level summaries for each sheet
4. A file-level summary
5. An HTML report with expandable sections

The HTML report will be saved at `results/test_summary_report.html` by default.

## Environment Configuration

### Local Environment (Recommended)

For local development, the simplest approach is to disable all enterprise features:

```bash
# Run in local environment mode (disables SSL and OAuth)
python run_summary.py path/to/your/excel_file.xlsx --local-env

# Or explicitly using environment variables
export IS_RBC_ENV=0
export USE_SSL=0
export USE_OAUTH=0
python run_summary.py path/to/your/excel_file.xlsx
```

### Enterprise Environment

For enterprise environments that require SSL certificates and OAuth authentication:

```bash
# Enable via command-line arguments
python run_summary.py path/to/your/excel_file.xlsx --rbc-env --use-ssl --use-oauth

# Or via environment variables
export IS_RBC_ENV=1
export USE_SSL=1
export USE_OAUTH=1
python run_summary.py path/to/your/excel_file.xlsx
```

#### SSL Certificate Configuration

When SSL is enabled (`--use-ssl` or `USE_SSL=1`), the tool looks for a certificate file:
- It will first check for `ssl_correct/rbc-ca-bundle.cer`
- If not found, it will fall back to `ssl/rbc-ca-bundle.cer`

Make sure to place your SSL certificate in one of these locations when running with SSL enabled.

When running in a local environment, the tool will use the OPENAI_API_KEY directly without OAuth authentication and SSL by default.