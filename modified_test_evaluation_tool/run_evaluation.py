#!/usr/bin/env python
"""
Simple script to run the Test Case Analysis Tool.

Usage:
    python run_evaluation.py /path/to/excel/directory
"""

import argparse
import os
import sys

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Add the parent directory to sys.path as well
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Set your OpenAI API key here directly
OPENAI_API_KEY = "your-openai-api-key-here"


def main():
    parser = argparse.ArgumentParser(description="Test Case Analysis Tool")
    parser.add_argument("excel_dir", help="Directory containing Excel test case files")
    parser.add_argument("--output_dir", default="./results", help="Directory to save results")
    parser.add_argument("--model", default="gpt-4-turbo", help="LLM model to use (default: gpt-4-turbo)")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories for Excel files")
    parser.add_argument("--sheet", help="Specific sheet name to process")
    parser.add_argument("--no_html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--html_only", action="store_true", help="Convert existing JSON to HTML without running summarization")
    
    args = parser.parse_args()
    
    try:
        # First try the import as a proper package
        from oauth import local_auth_settings
        from main import main as run_main
    except ImportError:
        # Fall back to fully qualified import if used as package
        from modified_test_evaluation_tool.oauth import local_auth_settings
        from modified_test_evaluation_tool.main import main as run_main
    
    # Update the API key in the settings file
    local_auth_settings.OPENAI_API_KEY = OPENAI_API_KEY
    
    # Build command line arguments as a list
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
    
    # Create a new argument parser instance and parse the arguments directly
    # This avoids modifying sys.argv which can cause issues
    try:
        # Run the main function with our arguments
        run_main(cmd_args)
    except TypeError:
        # If main doesn't accept arguments directly, try the old way
        # Set sys.argv and call without arguments
        sys.argv = ["modified_test_evaluation_tool.main"] + cmd_args
        run_main()


if __name__ == "__main__":
    main()