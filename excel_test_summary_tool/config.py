"""Configuration settings for the Excel Test Summary Tool."""

import os
import logging

# Get module logger
logger = logging.getLogger(__name__)

# Environment configuration
IS_RBC_ENV = os.environ.get("IS_RBC_ENV", "0").lower() in ["1", "true"]
USE_OAUTH = os.environ.get("USE_OAUTH", "1").lower() in ["1", "true"]
USE_SSL = os.environ.get("USE_SSL", "1").lower() in ["1", "true"]

# API configuration
BASE_URL = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
MAX_RETRY_ATTEMPTS = int(os.environ.get("MAX_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_SECONDS = int(os.environ.get("RETRY_DELAY_SECONDS", "2"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "180"))
TOKEN_PREVIEW_LENGTH = 7

# Excel processing configuration
EXCEL_FILE_INPUT = "input.xlsx"
MARKDOWN_OUTPUT_DIR = "results/markdown"
SUMMARY_OUTPUT_DIR = "results/summaries"

# LLM configuration
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))

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

# Log configuration information
logger.debug(f"Environment: {'RBC' if IS_RBC_ENV else 'local'}")
logger.debug(f"OAuth authentication: {'enabled' if USE_OAUTH else 'disabled'}")
logger.debug(f"SSL verification: {'enabled' if USE_SSL else 'disabled'}")
logger.debug(f"API base URL: {BASE_URL}")
logger.debug(f"Using LLM model: {LLM_MODEL}")