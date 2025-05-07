"""
Example script demonstrating how to evaluate a single Excel file.

Usage:
    python evaluate_single_file.py path/to/excel/file.xlsx
"""

import argparse
import logging
import os
import sys

# Add parent directory to path to import test_evaluation_tool
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_evaluation_tool.excel_processing import excel_to_markdown, save_markdown_to_file
from test_evaluation_tool.judge import evaluate_test_result
from test_evaluation_tool.oauth import setup_oauth
from test_evaluation_tool.utils import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Evaluate a single Excel file")
    parser.add_argument("excel_file", help="Path to Excel file")
    parser.add_argument("--output_dir", default="./results", help="Output directory")
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--sheet", help="Specific sheet to process")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level="INFO")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Get authentication token (API key)
        oauth_token = setup_oauth()
        
        # Convert Excel to markdown
        print(f"Converting Excel file to markdown: {args.excel_file}")
        markdown = excel_to_markdown(args.excel_file, sheet_name=args.sheet)
        
        # Save markdown to file
        markdown_file = os.path.join(args.output_dir, "test_results.md")
        save_markdown_to_file(markdown, markdown_file)
        print(f"Markdown saved to: {markdown_file}")
        
        # Evaluate the test result
        print(f"Evaluating test result with model: {args.model}")
        evaluation = evaluate_test_result(
            test_markdown=markdown,
            oauth_token=oauth_token,
            model=args.model,
            save_result=True,
            output_dir=args.output_dir
        )
        
        print("Evaluation complete!")
        print(f"Results saved to: {args.output_dir}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()