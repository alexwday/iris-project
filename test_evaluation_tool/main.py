"""
Test Evaluation Tool

This module provides the main entry point for the Test Evaluation Tool,
which processes Excel test results and evaluates them using LLM.

Usage:
    python -m test_evaluation_tool.main --excel_dir /path/to/excel/files --output_dir /path/to/output
"""

import argparse
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional

from .config import IS_RBC_ENV, USE_SSL, USE_OAUTH, DEFAULT_MODEL
from .excel_processing import excel_to_markdown, save_markdown_to_file
from .judge import evaluate_test_result, aggregate_evaluations
from .oauth import setup_oauth
from .ssl import setup_ssl
from .utils import setup_logging, find_excel_files

# Get module logger
logger = logging.getLogger(__name__)


def process_excel_file(
    excel_file: str,
    oauth_token: str,
    output_dir: str,
    model: str = DEFAULT_MODEL,
    sheet_name: Optional[str] = None,
    save_intermediate: bool = True
) -> Dict[str, Any]:
    """
    Process a single Excel file: convert to markdown, evaluate with LLM.

    Args:
        excel_file (str): Path to Excel file
        oauth_token (str): Authentication token for LLM API
        output_dir (str): Directory to save results
        model (str, optional): LLM model to use. Defaults to DEFAULT_MODEL.
        sheet_name (str, optional): Specific sheet to process. If None, processes all sheets.
        save_intermediate (bool, optional): Save intermediate markdown files. Defaults to True.

    Returns:
        dict: Evaluation results for the Excel file
    """
    logger.info(f"Processing Excel file: {excel_file}")
    
    try:
        # Create file-specific output directory
        filename = os.path.basename(excel_file).split('.')[0]
        file_output_dir = os.path.join(output_dir, filename)
        os.makedirs(file_output_dir, exist_ok=True)

        # Convert Excel to markdown
        markdown = excel_to_markdown(excel_file, sheet_name=sheet_name)
        
        # Save markdown if requested
        if save_intermediate:
            md_file_path = os.path.join(file_output_dir, f"{filename}.md")
            save_markdown_to_file(markdown, md_file_path)
        
        # Evaluate the test result
        evaluation = evaluate_test_result(
            test_markdown=markdown,
            oauth_token=oauth_token,
            model=model,
            save_result=True,
            output_dir=file_output_dir
        )
        
        return evaluation
    
    except Exception as e:
        logger.error(f"Error processing Excel file {excel_file}: {str(e)}")
        return {
            "error": str(e),
            "file": excel_file,
            "status": "failed"
        }


def main():
    """Main entry point for the test evaluation tool."""
    parser = argparse.ArgumentParser(description="Test Evaluation Tool")
    parser.add_argument("--excel_dir", required=True, help="Directory containing Excel test files")
    parser.add_argument("--output_dir", default="./results", help="Directory to save results")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model to use")
    parser.add_argument("--log_file", help="Path to log file")
    parser.add_argument("--log_level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                       help="Logging level")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories for Excel files")
    parser.add_argument("--sheet", help="Specific sheet name to process")
    parser.add_argument("--rbc_env", action="store_true", help="Use RBC environment settings")
    parser.add_argument("--use_ssl", action="store_true", help="Use SSL for API calls")
    parser.add_argument("--use_oauth", action="store_true", help="Use OAuth for API authentication")
    
    args = parser.parse_args()
    
    # Update configuration from arguments
    import sys
    from . import config

    if args.rbc_env:
        # Update module-level config
        config.IS_RBC_ENV = True
        # Also update imported value in this module
        module = sys.modules[__name__]
        module.IS_RBC_ENV = True
    if args.use_ssl:
        config.USE_SSL = True
        module = sys.modules[__name__]
        module.USE_SSL = True
    if args.use_oauth:
        config.USE_OAUTH = True
        module = sys.modules[__name__]
        module.USE_OAUTH = True
    
    # Setup logging
    setup_logging(log_level=args.log_level, log_file=args.log_file)
    
    # Log startup information
    logger.info("Starting Test Evaluation Tool")
    logger.info(f"Environment: {'RBC' if IS_RBC_ENV else 'Local'}")
    logger.info(f"SSL: {'Enabled' if USE_SSL else 'Disabled'}")
    logger.info(f"OAuth: {'Enabled' if USE_OAUTH else 'Disabled'}")
    logger.info(f"Model: {args.model}")
    
    try:
        # Setup SSL if enabled
        if USE_SSL:
            logger.info("Setting up SSL")
            setup_ssl()
        
        # Setup OAuth/Authentication
        logger.info("Setting up authentication")
        oauth_token = setup_oauth()
        
        # Find Excel files
        logger.info(f"Searching for Excel files in {args.excel_dir}")
        excel_files = find_excel_files(
            directory=args.excel_dir,
            recursive=args.recursive
        )
        
        if not excel_files:
            logger.error(f"No Excel files found in {args.excel_dir}")
            return
        
        logger.info(f"Found {len(excel_files)} Excel files to process")
        
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Process each Excel file
        evaluations = []
        for idx, excel_file in enumerate(excel_files):
            logger.info(f"Processing file {idx+1}/{len(excel_files)}: {excel_file}")
            
            evaluation = process_excel_file(
                excel_file=excel_file,
                oauth_token=oauth_token,
                output_dir=args.output_dir,
                model=args.model,
                sheet_name=args.sheet
            )
            
            evaluations.append(evaluation)
            
            # Short delay between files to avoid rate limiting
            if idx < len(excel_files) - 1:
                time.sleep(1)
        
        # Aggregate evaluations
        if len(evaluations) > 1:
            logger.info(f"Aggregating {len(evaluations)} evaluations")
            
            summary = aggregate_evaluations(
                evaluations=evaluations,
                oauth_token=oauth_token,
                model=args.model,
                save_result=True,
                output_dir=args.output_dir
            )
            
            logger.info("Summary generated successfully")
        
        logger.info("Test evaluation completed successfully")
    
    except Exception as e:
        logger.error(f"Error in test evaluation process: {str(e)}")
        raise


if __name__ == "__main__":
    main()