"""
Excel Test Summary Tool - Main script

This tool processes Excel test files by:
1. Loading an Excel file with test cases
2. Converting each test case row into individual markdown files
3. Using LLM to summarize each test case
4. Generating system-level summaries for each sheet
5. Creating a file-level summary of all test coverage
6. Outputting an HTML report with expandable sections
"""

import os
import sys
import logging
import argparse
from typing import Dict, List, Tuple

from excel_processing.excel_loader import (
    load_excel_file, 
    get_test_case_data, 
    create_unique_test_id
)
from markdown_generator.md_generator import generate_markdown_files
from llm_summarization.summarizer import (
    process_all_test_cases,
    create_system_summaries, 
    create_file_summary
)
from html_output.html_generator import generate_html_report
from config import (
    EXCEL_FILE_INPUT,
    MARKDOWN_OUTPUT_DIR,
    SUMMARY_OUTPUT_DIR,
    HTML_OUTPUT_FILE,
    HTML_TITLE,
    LLM_MODEL
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("excel_test_summary.log")
    ]
)
logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories for output files."""
    os.makedirs(MARKDOWN_OUTPUT_DIR, exist_ok=True)
    os.makedirs(SUMMARY_OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(HTML_OUTPUT_FILE), exist_ok=True)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Excel Test Summary Tool')
    parser.add_argument(
        'excel_file', 
        nargs='?', 
        default=EXCEL_FILE_INPUT,
        help=f'Path to the Excel file to process (default: {EXCEL_FILE_INPUT})'
    )
    parser.add_argument(
        '--api-key', 
        help='OpenAI API key (if not provided, will try to use environment variable OPENAI_API_KEY)'
    )
    parser.add_argument(
        '--model', 
        default=LLM_MODEL,
        help=f'LLM model to use (default: {LLM_MODEL})'
    )
    parser.add_argument(
        '--output', 
        default=HTML_OUTPUT_FILE,
        help=f'Output HTML file path (default: {HTML_OUTPUT_FILE})'
    )
    return parser.parse_args()


def get_api_key(cli_api_key=None):
    """Get OpenAI API key from CLI args or environment variables."""
    api_key = cli_api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            "OpenAI API key is required. Either provide it with --api-key "
            "or set the OPENAI_API_KEY environment variable."
        )
    return api_key


def main():
    """Main function to process Excel test file and generate summary report."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Ensure we have an API key
    api_key = get_api_key(args.api_key)
    
    # Set up directories
    setup_directories()
    
    logger.info(f"Starting Excel Test Summary Tool")
    logger.info(f"Processing Excel file: {args.excel_file}")
    
    try:
        # Step 1: Load Excel file
        excel_data = load_excel_file(args.excel_file)
        logger.info(f"Loaded Excel file with {len(excel_data)} sheets")
        
        # Step 2: Extract test case data
        test_case_data = get_test_case_data(excel_data)
        logger.info(f"Extracted {len(test_case_data)} test cases")
        
        # Step 3: Prepare test cases with IDs
        test_cases_with_ids = []
        for sheet_name, test_case in test_case_data:
            test_id = create_unique_test_id(sheet_name, test_case)
            test_cases_with_ids.append((sheet_name, test_case, test_id))
        
        # Step 4: Generate markdown files
        markdown_files = generate_markdown_files(
            test_cases_with_ids, 
            MARKDOWN_OUTPUT_DIR
        )
        logger.info(f"Generated {len(markdown_files)} markdown files")
        
        # Step 5: Process test cases with LLM
        test_case_list = [
            (sheet_name, test_id, markdown_files[test_id])
            for sheet_name, test_case, test_id in test_cases_with_ids
            if test_id in markdown_files
        ]
        system_test_cases = process_all_test_cases(api_key, test_case_list)
        logger.info(f"Processed test cases for {len(system_test_cases)} systems")
        
        # Step 6: Create system-level summaries
        system_summaries = create_system_summaries(api_key, system_test_cases)
        logger.info(f"Created {len(system_summaries)} system summaries")
        
        # Step 7: Create file-level summary
        file_summary = create_file_summary(api_key, system_summaries)
        logger.info("Created file-level summary")
        
        # Step 8: Generate HTML report
        generate_html_report(
            args.output,
            HTML_TITLE,
            file_summary,
            system_summaries,
            system_test_cases
        )
        logger.info(f"Generated HTML report: {args.output}")
        
        print(f"Successfully processed {len(test_case_data)} test cases from {len(excel_data)} systems.")
        print(f"HTML report generated: {args.output}")
        
    except Exception as e:
        logger.exception(f"Error processing Excel file: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()