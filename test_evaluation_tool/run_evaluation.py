#!/usr/bin/env python
"""
Simple script to run the Test Evaluation Tool.

Usage:
    python run_evaluation.py /path/to/excel/directory
"""

import argparse
import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set your OpenAI API key here directly
OPENAI_API_KEY = "your-openai-api-key-here"


def main():
    parser = argparse.ArgumentParser(description="Test Evaluation Tool")
    parser.add_argument("excel_dir", help="Directory containing Excel test files")
    parser.add_argument("--output_dir", default="./results", help="Directory to save results")
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories for Excel files")
    parser.add_argument("--sheet", help="Specific sheet name to process")
    parser.add_argument("--no_html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--html_only", action="store_true", help="Convert existing JSON to HTML without running evaluations")
    
    args = parser.parse_args()
    
    # Update the API key in the settings file - no need for environment variables
    from test_evaluation_tool.oauth import local_auth_settings
    local_auth_settings.OPENAI_API_KEY = OPENAI_API_KEY
    
    # Import and run the main module
    from test_evaluation_tool.main import main as run_main
    
    # Set sys.argv for the main function to use
    sys.argv = [
        "test_evaluation_tool.main",
        "--excel_dir", args.excel_dir,
        "--output_dir", args.output_dir,
        "--model", args.model
    ]
    
    if args.recursive:
        sys.argv.append("--recursive")
    
    if args.sheet:
        sys.argv.extend(["--sheet", args.sheet])
        
    if args.no_html:
        sys.argv.append("--no_html")
        
    if args.html_only:
        sys.argv.append("--html_only")
    
    # Run the main function
    run_main()


if __name__ == "__main__":
    main()