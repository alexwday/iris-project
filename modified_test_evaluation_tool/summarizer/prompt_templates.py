"""
LLM Prompt Templates

This module contains prompt templates used for test case summarization.
"""

# Prompt template for summarizing a single test case
TEST_CASE_SUMMARIZATION_PROMPT = """
# Test Case Summarization

You are a specialized AI trained to analyze and summarize test cases for software applications. You will be provided with a test case in markdown table format extracted from an Excel spreadsheet. Your goal is to extract key information and create a concise, structured summary.

## Test Case Information

Sheet Name: {sheet_name}
Test Case Number: {test_case_number}
Test Case Name: {test_case_name}

## Test Case Data (Markdown Table)

{test_case_markdown}

## Your Task

1. Analyze the test case to understand:
   - The purpose of the test
   - Expected inputs and preconditions
   - Expected outputs or results
   - Any special conditions or constraints

2. Create a structured summary that includes:
   - A brief (1-2 sentences) description of what the test is checking
   - Key inputs or conditions required for the test
   - Expected results or acceptance criteria
   - Any notable observations or special handling required

3. If you find inconsistencies or missing information in the test case, note them in your summary.

## Response Format

Use the provided function to return your analysis in a standardized format.
"""

# Prompt template for aggregating multiple test case summaries
AGGREGATION_PROMPT_TEMPLATE = """
# Test Case Summary Aggregation

You are analyzing a collection of test case summaries to create an executive overview. Below you'll find summaries for multiple test cases grouped by sheet.

## Your Task

1. Review all the test case summaries provided.

2. For each sheet (grouping of test cases):
   - Identify common patterns and themes
   - Assess overall coverage and focus areas
   - Note any gaps or potential issues in the test strategy
   - Summarize how comprehensive the test coverage appears to be

3. Create an executive summary that includes:
   - An overview of the test suite's purpose and scope
   - Key areas being tested
   - Evaluation of test coverage
   - Any significant observations about test quality, organization, or completeness
   - Potential improvements to the test strategy

## Test Case Summaries

{summary_content}

## Response Format

Use the extraction function to provide a structured analysis with an executive summary and sheet-specific sections.
"""