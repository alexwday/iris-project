"""
Test Case Summarizer Module

This module implements LLM-based summarization of test cases.
It processes markdown-formatted test cases and generates structured summaries.

Functions:
    summarize_test_case: Summarizes a single test case using LLM
    aggregate_summaries: Aggregates multiple test case summaries into an overview
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from ..llm_connectors import call_llm
from .prompt_templates import TEST_CASE_SUMMARIZATION_PROMPT, AGGREGATION_PROMPT_TEMPLATE

# Get module logger
logger = logging.getLogger(__name__)


def summarize_test_case(
    test_case: Dict[str, Any],
    oauth_token: str,
    model: str = "gpt-4",
    temperature: float = 0.0,
    save_result: bool = True,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Summarize a single test case using LLM.

    Args:
        test_case (dict): Dictionary containing test case information:
                          - sheet_name: Name of the Excel sheet
                          - test_case_number: Identifier for the test case
                          - test_case_name: Name or title of the test case
                          - markdown: Markdown representation of the test case
        oauth_token (str): Authentication token for LLM API
        model (str, optional): LLM model to use. Defaults to "gpt-4".
        temperature (float, optional): Temperature parameter for LLM. Defaults to 0.0.
        save_result (bool, optional): Whether to save summary to file. Defaults to True.
        output_dir (str, optional): Directory to save summary results. Defaults to "results".

    Returns:
        dict: Structured summary of the test case

    Raises:
        Exception: If LLM call fails or returns invalid JSON
    """
    logger.info(f"Summarizing test case {test_case.get('test_case_number')} ({test_case.get('test_case_name')}) with model: {model}")

    # Format the prompt with test case information
    prompt = TEST_CASE_SUMMARIZATION_PROMPT.format(
        sheet_name=test_case.get("sheet_name", "Unknown"),
        test_case_number=test_case.get("test_case_number", "Unknown"),
        test_case_name=test_case.get("test_case_name", "Unknown"),
        test_case_markdown=test_case.get("markdown", "No data available")
    )

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an expert at analyzing and summarizing software test cases."},
        {"role": "user", "content": prompt}
    ]

    try:
        # Define a tool for structured extraction
        summarization_tool = {
            "type": "function",
            "function": {
                "name": "extract_test_case_summary",
                "description": "Extract structured summary from test case data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sheet_name": {
                            "type": "string",
                            "description": "Name of the Excel sheet containing the test case"
                        },
                        "test_case_number": {
                            "type": "string",
                            "description": "Identifier for the test case"
                        },
                        "test_case_name": {
                            "type": "string",
                            "description": "Name or title of the test case"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "Brief description of the test case's purpose or what it's checking"
                        },
                        "inputs": {
                            "type": "string",
                            "description": "Key inputs or preconditions for the test case"
                        },
                        "expected_results": {
                            "type": "string",
                            "description": "Expected outputs or acceptance criteria"
                        },
                        "observations": {
                            "type": "string",
                            "description": "Any notable observations, special handling requirements, or concerns about the test case"
                        },
                        "comprehensive_summary": {
                            "type": "string",
                            "description": "A detailed summary of the test case incorporating all relevant information"
                        }
                    },
                    "required": ["sheet_name", "test_case_number", "test_case_name", "purpose", "comprehensive_summary"]
                }
            }
        }
        
        # Call LLM with tool
        logger.info("Calling LLM for test case summarization using function calling")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1500,
            tools=[summarization_tool],
            tool_choice={"type": "function", "function": {"name": "extract_test_case_summary"}}
        )

        # Create a default template in case extraction fails
        default_template = {
            "sheet_name": test_case.get("sheet_name", "Unknown"),
            "test_case_number": test_case.get("test_case_number", "Unknown"),
            "test_case_name": test_case.get("test_case_name", "Unknown"),
            "purpose": "Unable to determine from LLM response",
            "inputs": "Unable to determine from LLM response",
            "expected_results": "Unable to determine from LLM response",
            "observations": "Unable to determine from LLM response",
            "comprehensive_summary": "Unable to extract summary from LLM response"
        }
        
        try:
            # Extract the structured summary from the tool call
            message = response.choices[0].message
            
            # Check if we got a tool call
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Extract the function call arguments (the summary)
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "extract_test_case_summary":
                    # Parse the function arguments as JSON
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info("Successfully extracted summary from tool call")
                    summary = function_args
                else:
                    logger.error(f"Unexpected tool call: {tool_call.function.name}")
                    summary = default_template
            else:
                # Fallback to content if no tool call
                logger.warning("No tool call found in response, trying to extract from content")
                content = message.content
                if not content:
                    logger.error("No content found in response")
                    summary = default_template
                else:
                    # Try to extract JSON from the content
                    try:
                        # Try different methods to extract JSON
                        if "```json" in content:
                            # Extract from code blocks
                            json_block = content.split("```json")[1].split("```")[0].strip()
                            summary = json.loads(json_block)
                            logger.info("Extracted JSON from markdown code block")
                        else:
                            # Try to parse the entire content as JSON
                            summary = json.loads(content)
                            logger.info("Parsed entire content as JSON")
                    except Exception as parse_error:
                        logger.error(f"Failed to extract JSON from content: {str(parse_error)}")
                        summary = default_template
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            summary = default_template
            
        # Ensure required fields are present
        for field in ["sheet_name", "test_case_number", "test_case_name", "purpose", "comprehensive_summary"]:
            if field not in summary:
                summary[field] = default_template[field]
        
        # Add optional fields with defaults if missing
        for field in ["inputs", "expected_results", "observations"]:
            if field not in summary:
                summary[field] = default_template[field]
        
        # Add original test case data for reference
        summary["original_test_case"] = {
            "markdown": test_case.get("markdown", ""),
            "row_index": test_case.get("row_index", 0)
        }
        
        # Add metadata to summary
        summary["metadata"] = {
            "model": model,
            "temperature": temperature
        }
        
        # Add usage data if available
        if usage_details:
            summary["metadata"]["usage"] = usage_details
        
        # Save summary to file if requested
        if save_result:
            _save_summary(summary, output_dir)
        
        return summary
    
    except Exception as e:
        logger.error(f"Error summarizing test case: {str(e)}")
        raise


def aggregate_summaries(
    summaries: List[Dict[str, Any]],
    oauth_token: str,
    model: str = "gpt-4",
    temperature: float = 0.0,
    save_result: bool = True,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Aggregate multiple test case summaries into an overview.

    Args:
        summaries (list): List of test case summary dictionaries
        oauth_token (str): Authentication token for LLM API
        model (str, optional): LLM model to use. Defaults to "gpt-4".
        temperature (float, optional): Temperature parameter for LLM. Defaults to 0.0.
        save_result (bool, optional): Whether to save aggregate summary to file. Defaults to True.
        output_dir (str, optional): Directory to save results. Defaults to "results".

    Returns:
        dict: Aggregated overview of all test case summaries

    Raises:
        Exception: If LLM call fails
    """
    logger.info(f"Aggregating {len(summaries)} test case summaries with model: {model}")

    # Group summaries by sheet name
    sheets = {}
    for summary in summaries:
        sheet_name = summary.get("sheet_name", "Unknown")
        if sheet_name not in sheets:
            sheets[sheet_name] = []
        sheets[sheet_name].append(summary)
    
    # Format summaries as text, organized by sheet
    summary_content = ""
    for sheet_name, sheet_summaries in sheets.items():
        summary_content += f"## Sheet: {sheet_name}\n\n"
        for idx, summary in enumerate(sheet_summaries):
            summary_content += f"### Test Case {summary.get('test_case_number')}: {summary.get('test_case_name')}\n\n"
            summary_content += f"**Purpose**: {summary.get('purpose', 'N/A')}\n\n"
            summary_content += f"**Inputs**: {summary.get('inputs', 'N/A')}\n\n"
            summary_content += f"**Expected Results**: {summary.get('expected_results', 'N/A')}\n\n"
            summary_content += f"**Observations**: {summary.get('observations', 'N/A')}\n\n"
            summary_content += f"**Comprehensive Summary**: {summary.get('comprehensive_summary', 'N/A')}\n\n"
            if idx < len(sheet_summaries) - 1:
                summary_content += "---\n\n"
        summary_content += "\n\n"
    
    # Format the prompt
    prompt = AGGREGATION_PROMPT_TEMPLATE.format(summary_content=summary_content)

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an expert at analyzing test suites and providing executive summaries."},
        {"role": "user", "content": prompt}
    ]

    try:
        # Define a tool for structured extraction
        aggregation_tool = {
            "type": "function",
            "function": {
                "name": "extract_test_suite_analysis",
                "description": "Extract structured analysis of test suite from test case summaries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "executive_summary": {
                            "type": "string",
                            "description": "Overall analysis of the test suite's purpose, coverage, and quality"
                        },
                        "key_areas_tested": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of main functional areas or features being tested"
                        },
                        "sheets_analysis": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sheet_name": {
                                        "type": "string",
                                        "description": "Name of the Excel sheet"
                                    },
                                    "focus_area": {
                                        "type": "string",
                                        "description": "Main focus or purpose of this group of tests"
                                    },
                                    "test_count": {
                                        "type": "integer",
                                        "description": "Number of tests in this sheet"
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": "Analysis of this sheet's test cases"
                                    },
                                    "observations": {
                                        "type": "string",
                                        "description": "Notable observations or concerns about tests in this sheet"
                                    }
                                },
                                "required": ["sheet_name", "focus_area", "test_count", "summary"]
                            },
                            "description": "Analysis of each sheet's test cases"
                        },
                        "overall_assessment": {
                            "type": "string",
                            "description": "Overall assessment of test coverage and quality"
                        },
                        "recommendations": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Recommendations for improving the test suite"
                        }
                    },
                    "required": ["executive_summary", "key_areas_tested", "sheets_analysis", "overall_assessment"]
                }
            }
        }
        
        # Call LLM with tool
        logger.info("Calling LLM for test suite analysis using function calling")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2500,
            tools=[aggregation_tool],
            tool_choice={"type": "function", "function": {"name": "extract_test_suite_analysis"}}
        )
        
        # Create a default template in case extraction fails
        default_template = {
            "executive_summary": "Unable to generate executive summary from LLM response",
            "key_areas_tested": ["Unable to determine key areas tested"],
            "sheets_analysis": [
                {
                    "sheet_name": sheet_name,
                    "focus_area": "Unable to determine focus area",
                    "test_count": len(sheet_summaries),
                    "summary": "Unable to generate sheet summary from LLM response",
                    "observations": "No observations available"
                }
                for sheet_name, sheet_summaries in sheets.items()
            ],
            "overall_assessment": "Unable to generate overall assessment from LLM response",
            "recommendations": ["No recommendations available"]
        }
        
        try:
            # Extract the structured summary from the tool call
            message = response.choices[0].message
            
            # Check if we got a tool call
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Extract the function call arguments
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "extract_test_suite_analysis":
                    # Parse the function arguments as JSON
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info("Successfully extracted test suite analysis from tool call")
                    analysis = function_args
                else:
                    logger.error(f"Unexpected tool call: {tool_call.function.name}")
                    analysis = default_template
            else:
                # Fallback to content if no tool call
                logger.warning("No tool call found in response, trying to extract from content")
                content = message.content
                if not content:
                    logger.error("No content found in response")
                    analysis = default_template
                else:
                    # Try to extract JSON from the content
                    try:
                        # Try different methods to extract JSON
                        if "```json" in content:
                            # Extract from code blocks
                            json_block = content.split("```json")[1].split("```")[0].strip()
                            analysis = json.loads(json_block)
                            logger.info("Extracted JSON from markdown code block")
                        else:
                            # Try to parse the entire content as JSON
                            analysis = json.loads(content)
                            logger.info("Parsed entire content as JSON")
                    except Exception as parse_error:
                        logger.error(f"Failed to extract JSON from content: {str(parse_error)}")
                        analysis = default_template
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            analysis = default_template
        
        # Ensure all required fields are present
        for field in ["executive_summary", "key_areas_tested", "sheets_analysis", "overall_assessment"]:
            if field not in analysis:
                analysis[field] = default_template[field]
        
        # Add recommendations if missing
        if "recommendations" not in analysis:
            analysis["recommendations"] = default_template["recommendations"]
        
        # Add metadata to analysis
        analysis["metadata"] = {
            "model": model,
            "temperature": temperature,
            "summaries_count": len(summaries),
            "sheets_count": len(sheets)
        }
        
        # Add usage data if available
        if usage_details:
            analysis["metadata"]["usage"] = usage_details
        
        # Save analysis to file if requested
        if save_result:
            _save_aggregate_analysis(analysis, output_dir)
        
        return analysis
    
    except Exception as e:
        logger.error(f"Error aggregating test case summaries: {str(e)}")
        raise


def _save_summary(
    summary: Dict[str, Any],
    output_dir: str,
    filename: Optional[str] = None
) -> None:
    """
    Save test case summary to a JSON file.

    Args:
        summary (dict): Test case summary to save
        output_dir (str): Directory to save the file
        filename (str, optional): Custom filename. Defaults to auto-generated name.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            sheet_name = summary.get("sheet_name", "unknown").replace(" ", "_")
            test_num = summary.get("test_case_number", "unknown").replace(" ", "_")
            filename = f"{sheet_name}_case_{test_num}.json"
        
        # Full file path
        file_path = os.path.join(output_dir, filename)
        
        # Write summary to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Test case summary saved to: {file_path}")
    
    except Exception as e:
        logger.error(f"Error saving test case summary to file: {str(e)}")
        # Don't raise - this is a non-critical operation


def _save_aggregate_analysis(
    analysis: Dict[str, Any],
    output_dir: str,
    filename: str = "test_suite_analysis.json"
) -> None:
    """
    Save aggregate test suite analysis to a JSON file.

    Args:
        analysis (dict): Test suite analysis to save
        output_dir (str): Directory to save the file
        filename (str, optional): Filename. Defaults to "test_suite_analysis.json".
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Full file path
        file_path = os.path.join(output_dir, filename)
        
        # Write analysis to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
            
        # Also save as markdown for easy reading
        md_file_path = os.path.join(output_dir, "test_suite_analysis.md")
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write("# Test Suite Analysis\n\n")
            f.write("## Executive Summary\n\n")
            f.write(analysis["executive_summary"])
            f.write("\n\n## Key Areas Tested\n\n")
            for area in analysis["key_areas_tested"]:
                f.write(f"- {area}\n")
            f.write("\n\n## Overall Assessment\n\n")
            f.write(analysis["overall_assessment"])
            f.write("\n\n## Recommendations\n\n")
            for rec in analysis["recommendations"]:
                f.write(f"- {rec}\n")
            f.write("\n\n## Sheet-by-Sheet Analysis\n\n")
            for sheet in analysis["sheets_analysis"]:
                f.write(f"### {sheet['sheet_name']} ({sheet.get('test_count', 'N/A')} tests)\n\n")
                f.write(f"**Focus Area**: {sheet.get('focus_area', 'N/A')}\n\n")
                f.write(f"**Summary**: {sheet.get('summary', 'N/A')}\n\n")
                if "observations" in sheet and sheet["observations"]:
                    f.write(f"**Observations**: {sheet['observations']}\n\n")
                f.write("---\n\n")
            
        logger.info(f"Test suite analysis saved to: {file_path} and {md_file_path}")
    
    except Exception as e:
        logger.error(f"Error saving test suite analysis to file: {str(e)}")
        # Don't raise - this is a non-critical operation