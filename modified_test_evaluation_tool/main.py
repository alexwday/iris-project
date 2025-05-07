"""
Test Case Analysis Tool

This module provides the main entry point for the Test Case Analysis Tool,
which processes Excel test case files, summarizes them using LLM, and generates
comprehensive reports.

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
from .excel_processing import excel_to_markdown, save_markdown_to_file, extract_test_cases
from .summarizer import summarize_test_case, aggregate_summaries, summarize_sheet_test_cases
from .oauth import setup_oauth
from .ssl import setup_ssl
from .utils import setup_logging, find_excel_files
from .html_output import generate_test_summary_report, test_summary_json_to_html

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
    Process a single Excel file: extract test cases, summarize with LLM.
    Processes all test cases from each sheet in a single LLM call.

    Args:
        excel_file (str): Path to Excel file
        oauth_token (str): Authentication token for LLM API
        output_dir (str): Directory to save results
        model (str, optional): LLM model to use. Defaults to DEFAULT_MODEL.
        sheet_name (str, optional): Specific sheet to process. If None, processes all sheets.
        save_intermediate (bool, optional): Save intermediate markdown files. Defaults to True.

    Returns:
        dict: Summary results for the Excel file, with test cases organized by sheet
    """
    logger.info(f"Processing Excel file: {excel_file}")
    
    try:
        # Create file-specific output directory
        filename = os.path.basename(excel_file).split('.')[0]
        file_output_dir = os.path.join(output_dir, filename)
        os.makedirs(file_output_dir, exist_ok=True)

        # Extract test cases from Excel, grouped by sheet
        test_cases_by_sheet = extract_test_cases(excel_file, sheet_name=sheet_name, group_by_sheet=True)
        
        # Count total test cases
        total_test_cases = sum(len(cases) for cases in test_cases_by_sheet.values())
        logger.info(f"Extracted {total_test_cases} test cases from {len(test_cases_by_sheet)} sheets in {excel_file}")
        
        if not test_cases_by_sheet:
            logger.warning(f"No test cases found in {excel_file}")
            return {
                "file": excel_file,
                "status": "warning",
                "message": "No test cases found",
                "test_cases_count": 0
            }
        
        # Process each sheet with a batch call
        all_summaries = []
        
        for sheet_name, sheet_test_cases in test_cases_by_sheet.items():
            logger.info(f"Processing sheet '{sheet_name}' with {len(sheet_test_cases)} test cases")
            
            # Create sheet-specific directory
            sheet_dir = os.path.join(file_output_dir, f"sheet_{sheet_name}")
            os.makedirs(sheet_dir, exist_ok=True)
            
            # Save markdown files if requested
            if save_intermediate:
                for test_case in sheet_test_cases:
                    test_case_number = test_case.get("test_case_number", "unknown")
                    md_file_path = os.path.join(sheet_dir, f"test_case_{test_case_number}.md")
                    save_markdown_to_file(test_case.get("markdown", ""), md_file_path)
            
            try:
                # Summarize all test cases in the sheet with a single LLM call
                logger.info(f"Batch summarizing {len(sheet_test_cases)} test cases from sheet '{sheet_name}'")
                sheet_summaries = summarize_sheet_test_cases(
                    sheet_name=sheet_name,
                    test_cases=sheet_test_cases,
                    oauth_token=oauth_token,
                    model=model
                )
                
                # Save individual summaries
                for summary in sheet_summaries:
                    test_case_number = summary.get("test_case_number", "unknown")
                    summary_path = os.path.join(sheet_dir, f"test_case_{test_case_number}_summary.json")
                    with open(summary_path, "w") as f:
                        json.dump(summary, f, indent=2)
                
                all_summaries.extend(sheet_summaries)
                logger.info(f"Batch summarization complete for sheet '{sheet_name}'")
                
            except Exception as e:
                logger.error(f"Error batch summarizing sheet '{sheet_name}': {str(e)}")
                # Create minimal summaries with error information for all test cases in the sheet
                for test_case in sheet_test_cases:
                    error_summary = {
                        "sheet_name": sheet_name,
                        "test_case_number": test_case.get("test_case_number", "unknown"),
                        "test_case_name": test_case.get("test_case_name", "Unknown"),
                        "error": str(e),
                        "status": "failed"
                    }
                    all_summaries.append(error_summary)
            
            # Short delay between processing sheets to avoid rate limiting
            if len(test_cases_by_sheet) > 1:
                time.sleep(1)
        
        # Aggregate all test case summaries
        try:
            logger.info("Aggregating test case summaries")
            # Filter out failed summaries
            valid_summaries = [s for s in all_summaries if "status" not in s or s["status"] != "failed"]
            
            if valid_summaries:
                analysis = aggregate_summaries(
                    summaries=valid_summaries,
                    oauth_token=oauth_token,
                    model=model,
                    save_result=True,
                    output_dir=file_output_dir
                )
                logger.info("Aggregation complete")
            else:
                logger.warning("No valid summaries to aggregate")
                analysis = {
                    "executive_summary": "No valid test case summaries available for aggregation",
                    "sheets_analysis": []
                }
        except Exception as e:
            logger.error(f"Error aggregating test case summaries: {str(e)}")
            analysis = {
                "error": str(e),
                "executive_summary": "Error occurred during test case aggregation",
                "status": "failed"
            }
        
        # Generate HTML report
        try:
            logger.info("Generating HTML report")
            html_file = os.path.join(file_output_dir, f"{filename}_test_summary.html")
            generate_test_summary_report(
                test_suite_analysis=analysis,
                test_case_summaries=all_summaries,
                output_file=html_file
            )
            logger.info(f"HTML report generated: {html_file}")
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
        
        # Create an overall results summary
        summary = {
            "file": excel_file,
            "test_cases_count": total_test_cases,
            "successful_summaries": sum(1 for s in all_summaries if "status" not in s or s["status"] != "failed"),
            "sheets": list(test_cases_by_sheet.keys()),
            "analysis": analysis,
            "summaries": all_summaries
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


def main(args=None):
    """
    Main entry point for the Test Case Analysis Tool.
    
    Args:
        args (list, optional): Command line arguments as a list. If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser(description="Test Case Analysis Tool")
    parser.add_argument("--excel_dir", required=True, help="Directory containing Excel test case files")
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
    parser.add_argument("--html_only", action="store_true", help="Convert existing JSON to HTML without running summarization")
    
    args = parser.parse_args(args)
    
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
    logger.info("Starting Test Case Analysis Tool")
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
                    if file.endswith('test_suite_analysis.json'):
                        json_files.append(os.path.join(root, file))
            
            if not json_files:
                logger.error(f"No test suite analysis JSON files found in {args.output_dir}")
                return
            
            logger.info(f"Found {len(json_files)} JSON files to convert to HTML")
            for json_file in json_files:
                try:
                    html_file = test_summary_json_to_html(json_file)
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
        summaries = []
        for idx, excel_file in enumerate(excel_files):
            logger.info(f"Processing file {idx+1}/{len(excel_files)}: {excel_file}")
            
            file_summary = process_excel_file(
                excel_file=excel_file,
                oauth_token=oauth_token,
                output_dir=args.output_dir,
                model=args.model,
                sheet_name=args.sheet
            )
            
            summaries.append(file_summary)
            
            # HTML is generated in process_excel_file function, no need to generate it here
            
            # Short delay between files to avoid rate limiting
            if idx < len(excel_files) - 1:
                time.sleep(1)
        
        # Aggregate all test case summaries across files if there's more than one file
        if len(excel_files) > 1:
            try:
                logger.info("Creating cross-file aggregation")
                # Extract all test case summaries from all files
                all_test_case_summaries = []
                
                for file_summary in summaries:
                    if "summaries" in file_summary:
                        # Filter out failed summaries
                        valid_summaries = [s for s in file_summary["summaries"] 
                                          if "status" not in s or s["status"] != "failed"]
                        all_test_case_summaries.extend(valid_summaries)
                
                if all_test_case_summaries:
                    # Generate a cross-file aggregation
                    aggregate_analysis = aggregate_summaries(
                        summaries=all_test_case_summaries,
                        oauth_token=oauth_token,
                        model=args.model,
                        save_result=True,
                        output_dir=args.output_dir
                    )
                    
                    logger.info("Cross-file aggregation complete")
                    
                    # Generate HTML summary report for all files if not disabled
                    if not args.no_html:
                        try:
                            html_file = os.path.join(args.output_dir, "all_test_cases_summary.html")
                            generate_test_summary_report(
                                test_suite_analysis=aggregate_analysis,
                                test_case_summaries=all_test_case_summaries,
                                output_file=html_file
                            )
                            logger.info(f"Generated cross-file HTML report: {html_file}")
                        except Exception as e:
                            logger.error(f"Error generating cross-file HTML report: {str(e)}")
                else:
                    logger.warning("No valid test case summaries to aggregate across files")
            except Exception as e:
                logger.error(f"Error in cross-file aggregation: {str(e)}")
        
        logger.info("Test case analysis completed successfully")
    
    except Exception as e:
        logger.error(f"Error in test case analysis process: {str(e)}")
        raise


if __name__ == "__main__":
    main()