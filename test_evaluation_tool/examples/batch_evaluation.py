"""
Example script demonstrating how to batch process multiple Excel files
and generate an aggregated summary.

Usage:
    python batch_evaluation.py path/to/excel/directory
"""

import argparse
import logging
import os
import sys
import time

# Add parent directory to path to import test_evaluation_tool
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_evaluation_tool.excel_processing import excel_to_markdown, save_markdown_to_file
from test_evaluation_tool.judge import evaluate_test_result, aggregate_evaluations
from test_evaluation_tool.oauth import setup_oauth
from test_evaluation_tool.utils import setup_logging, find_excel_files


def main():
    parser = argparse.ArgumentParser(description="Batch evaluate multiple Excel files")
    parser.add_argument("excel_dir", help="Directory containing Excel files")
    parser.add_argument("--output_dir", default="./results", help="Output directory")
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level="INFO")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Get authentication token (API key)
        oauth_token = setup_oauth()
        
        # Find Excel files
        print(f"Searching for Excel files in: {args.excel_dir}")
        excel_files = find_excel_files(
            directory=args.excel_dir,
            recursive=args.recursive
        )
        
        if not excel_files:
            print(f"No Excel files found in {args.excel_dir}")
            sys.exit(1)
        
        print(f"Found {len(excel_files)} Excel files to process")
        
        # Process each Excel file
        evaluations = []
        for idx, excel_file in enumerate(excel_files):
            print(f"Processing file {idx+1}/{len(excel_files)}: {excel_file}")
            
            try:
                # Create file-specific output directory
                filename = os.path.basename(excel_file).split('.')[0]
                file_output_dir = os.path.join(args.output_dir, filename)
                os.makedirs(file_output_dir, exist_ok=True)
                
                # Convert Excel to markdown
                markdown = excel_to_markdown(excel_file)
                
                # Save markdown to file
                markdown_file = os.path.join(file_output_dir, f"{filename}.md")
                save_markdown_to_file(markdown, markdown_file)
                
                # Evaluate the test result
                evaluation = evaluate_test_result(
                    test_markdown=markdown,
                    oauth_token=oauth_token,
                    model=args.model,
                    save_result=True,
                    output_dir=file_output_dir
                )
                
                evaluations.append(evaluation)
                print(f"Evaluation complete for: {excel_file}")
                
                # Short delay between files to avoid rate limiting
                if idx < len(excel_files) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error processing file {excel_file}: {str(e)}")
                # Continue with next file
        
        # Generate aggregated summary if we have multiple evaluations
        if len(evaluations) > 1:
            print(f"Generating aggregated summary for {len(evaluations)} evaluations")
            
            summary = aggregate_evaluations(
                evaluations=evaluations,
                oauth_token=oauth_token,
                model=args.model,
                save_result=True,
                output_dir=args.output_dir
            )
            
            print("Summary generation complete!")
            print(f"Summary saved to: {args.output_dir}/summary.md")
        
        print("Batch evaluation complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()