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
from .html_output import generate_html_report, json_to_html

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
    Processes each sheet separately.

    Args:
        excel_file (str): Path to Excel file
        oauth_token (str): Authentication token for LLM API
        output_dir (str): Directory to save results
        model (str, optional): LLM model to use. Defaults to DEFAULT_MODEL.
        sheet_name (str, optional): Specific sheet to process. If None, processes all sheets.
        save_intermediate (bool, optional): Save intermediate markdown files. Defaults to True.

    Returns:
        dict: Evaluation results for the Excel file, with sheet names as keys
    """
    logger.info(f"Processing Excel file: {excel_file}")
    
    try:
        # Create file-specific output directory
        filename = os.path.basename(excel_file).split('.')[0]
        file_output_dir = os.path.join(output_dir, filename)
        os.makedirs(file_output_dir, exist_ok=True)

        # Convert Excel to markdown - get a dictionary of sheets
        markdown_dict = excel_to_markdown(excel_file, sheet_name=sheet_name, separate_sheets=True)
        
        # Save each sheet's markdown separately and evaluate
        results = {}
        for sheet_name, markdown in markdown_dict.items():
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Create sheet-specific directory
            sheet_dir = os.path.join(file_output_dir, f"sheet_{sheet_name}")
            os.makedirs(sheet_dir, exist_ok=True)
            
            # Save markdown if requested
            if save_intermediate:
                md_file_path = os.path.join(sheet_dir, f"{sheet_name}.md")
                save_markdown_to_file(markdown, md_file_path)
            
            try:
                # Evaluate the test result for this sheet
                logger.info(f"Evaluating sheet: {sheet_name}")
                evaluation = evaluate_test_result(
                    test_markdown=markdown,
                    oauth_token=oauth_token,
                    model=model,
                    save_result=True,
                    output_dir=sheet_dir
                )
                results[sheet_name] = evaluation
                logger.info(f"Evaluation complete for sheet: {sheet_name}")
            
            except Exception as e:
                logger.error(f"Error evaluating sheet {sheet_name}: {str(e)}")
                results[sheet_name] = {
                    "error": str(e),
                    "sheet": sheet_name,
                    "status": "failed"
                }
        
        # Create an overall results summary
        summary = {
            "file": excel_file,
            "sheets_evaluated": len(results),
            "successful_sheets": sum(1 for v in results.values() if v.get("status") != "failed"),
            "results_by_sheet": results
        }
        
        # Save summary to file
        summary_path = os.path.join(file_output_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
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
    parser.add_argument("--no_html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--html_only", action="store_true", help="Convert existing JSON to HTML without running evaluations")
    
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
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Handle HTML-only mode
        if args.html_only:
            logger.info("Running in HTML-only mode (converting existing JSON files to HTML)")
            json_files = []
            for root, _, files in os.walk(args.output_dir):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            
            if not json_files:
                logger.error(f"No JSON files found in {args.output_dir}")
                return
            
            logger.info(f"Found {len(json_files)} JSON files to convert to HTML")
            for json_file in json_files:
                try:
                    html_file = json_to_html(json_file)
                    logger.info(f"Generated HTML: {html_file}")
                except Exception as e:
                    logger.error(f"Error converting {json_file} to HTML: {str(e)}")
            
            return
        
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
            
            # Generate HTML for individual file if not disabled
            if not args.no_html:
                try:
                    # Create file summary HTML
                    file_basename = os.path.basename(excel_file).split('.')[0]
                    html_file = os.path.join(args.output_dir, f"{file_basename}.html")
                    
                    # Get individual evaluations
                    sheet_evals = []
                    if "results_by_sheet" in evaluation:
                        for sheet_name, sheet_eval in evaluation["results_by_sheet"].items():
                            if sheet_eval.get("status") != "failed":
                                # Add file and sheet info
                                sheet_eval["file"] = os.path.basename(excel_file)
                                sheet_eval["sheet"] = sheet_name
                                sheet_evals.append(sheet_eval)
                    
                    if sheet_evals:
                        # Create summary for this file
                        file_summary = {
                            "summary": f"Evaluation results for {os.path.basename(excel_file)}",
                            "file": excel_file,
                            "sheets_evaluated": len(sheet_evals)
                        }
                        generate_html_report(file_summary, sheet_evals, html_file)
                        logger.info(f"Generated HTML report for {excel_file}: {html_file}")
                except Exception as e:
                    logger.error(f"Error generating HTML for {excel_file}: {str(e)}")
            
            # Short delay between files to avoid rate limiting
            if idx < len(excel_files) - 1:
                time.sleep(1)
        
        # Flatten evaluations from each file/sheet for aggregation
        flattened_evaluations = []
        for file_eval in evaluations:
            if "results_by_sheet" in file_eval:
                # Extract individual sheet evaluations
                for sheet_name, sheet_eval in file_eval["results_by_sheet"].items():
                    if "status" not in sheet_eval or sheet_eval["status"] != "failed":
                        sheet_eval["file"] = file_eval["file"]
                        sheet_eval["sheet"] = sheet_name
                        flattened_evaluations.append(sheet_eval)
            else:
                # Add the file evaluation directly if it's not sheet-based
                if "status" not in file_eval or file_eval["status"] != "failed":
                    flattened_evaluations.append(file_eval)
        
        # Aggregate evaluations if we have any successful ones
        if len(flattened_evaluations) > 0:
            logger.info(f"Aggregating {len(flattened_evaluations)} successful evaluations")
            
            summary = aggregate_evaluations(
                evaluations=flattened_evaluations,
                oauth_token=oauth_token,
                model=args.model,
                save_result=True,
                output_dir=args.output_dir
            )
            
            logger.info("Summary generated successfully")
            
            # Generate HTML summary report if not disabled
            if not args.no_html:
                try:
                    html_file = os.path.join(args.output_dir, "summary.html")
                    generate_html_report(summary, flattened_evaluations, html_file)
                    logger.info(f"Generated summary HTML report: {html_file}")
                except Exception as e:
                    logger.error(f"Error generating summary HTML: {str(e)}")
        
        logger.info("Test evaluation completed successfully")
    
    except Exception as e:
        logger.error(f"Error in test evaluation process: {str(e)}")
        raise


if __name__ == "__main__":
    main()