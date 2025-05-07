#!/usr/bin/env python
"""
Simple wrapper script to run the Test Case Analysis Tool from the project root.

Usage:
    python analyze_test_cases.py /path/to/excel/directory [options]
"""

import os
import sys
import argparse

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set your OpenAI API key here (or use environment variable)
OPENAI_API_KEY = "your-openai-api-key-here"


def main():
    parser = argparse.ArgumentParser(description="Test Case Analysis Tool")
    parser.add_argument("excel_dir", help="Directory containing Excel test case files")
    parser.add_argument("--output_dir", default="./results", help="Directory to save results")
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories for Excel files")
    parser.add_argument("--sheet", help="Specific sheet name to process")
    parser.add_argument("--no_html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--html_only", action="store_true", help="Convert existing JSON to HTML without running summarization")
    
    args = parser.parse_args()
    
    # Import the local auth settings and update API key
    from modified_test_evaluation_tool.oauth import local_auth_settings
    local_auth_settings.OPENAI_API_KEY = OPENAI_API_KEY
    
    # Import the main function
    from modified_test_evaluation_tool.main import main as run_main
    
    # Build arguments list for main function
    cmd_args = [
        "--excel_dir", args.excel_dir,
        "--output_dir", args.output_dir,
        "--model", args.model
    ]
    
    if args.recursive:
        cmd_args.append("--recursive")
    
    if args.sheet:
        cmd_args.extend(["--sheet", args.sheet])
        
    if args.no_html:
        cmd_args.append("--no_html")
        
    if args.html_only:
        cmd_args.append("--html_only")
    
    # Run the main function
    run_main(cmd_args)


if __name__ == "__main__":
    main()