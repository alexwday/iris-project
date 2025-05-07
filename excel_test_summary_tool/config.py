"""Configuration settings for the Excel Test Summary Tool."""

# Excel processing configuration
EXCEL_FILE_INPUT = "input.xlsx"
MARKDOWN_OUTPUT_DIR = "results/markdown"
SUMMARY_OUTPUT_DIR = "results/summaries"

# LLM configuration
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.1

# Individual test case summary prompt
TEST_CASE_SUMMARY_PROMPT = """
You are analyzing a test case from an Excel sheet. Summarize the test case in a clear and concise way.
Extract the key details based on the provided information.

Test case information:
{test_case_markdown}

Please provide:
1. A brief summary (2-3 sentences) of what this test is checking
2. The key steps involved
3. The expected results
4. Any identified preconditions or dependencies

Respond with concise, clear language focusing on the essentials of the test case.
"""

# System/sheet level summary prompt
SYSTEM_SUMMARY_PROMPT = """
You are analyzing a collection of test cases for a system called "{system_name}".
Review the following summaries of individual test cases and provide a comprehensive overview.

Individual test cases:
{test_case_summaries}

Please provide:
1. An overall summary of what this system's tests are covering
2. The main functionality being tested
3. Any patterns or common themes across tests
4. Identify any potential gaps in test coverage (if apparent)

Respond with a clear, concise summary that gives a holistic view of the testing for this system.
"""

# File level summary prompt
FILE_LEVEL_SUMMARY_PROMPT = """
You are analyzing test coverage across multiple systems in a test suite.
Review the following system-level summaries and provide a comprehensive overview.

System summaries:
{system_summaries}

Please provide:
1. An overall assessment of the test coverage across all systems
2. Key systems being tested and their relative coverage
3. Any overarching patterns or themes
4. Recommendations for improving test coverage (if apparent)

Respond with a clear, concise executive summary of the entire test suite.
"""

# HTML output configuration
HTML_OUTPUT_FILE = "results/test_summary_report.html"
HTML_TITLE = "Test Case Summary Report"
"""