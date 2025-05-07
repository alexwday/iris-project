"""
Batch Test Case Summarizer Module

This module provides functionality for summarizing multiple test cases
from a single sheet in one LLM call for better efficiency.
"""

import json
import logging
from typing import Dict, List, Any

from ..llm_connectors import call_llm
from .prompt_templates import TEST_CASE_SUMMARIZATION_PROMPT

# Get module logger
logger = logging.getLogger(__name__)


def summarize_sheet_test_cases(
    sheet_name: str,
    test_cases: List[Dict[str, Any]],
    oauth_token: str,
    model: str = "gpt-4",
    temperature: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Summarize all test cases from a sheet in a single LLM call.
    
    Args:
        sheet_name (str): The name of the sheet
        test_cases (List[Dict[str, Any]]): List of test cases from the sheet
        oauth_token (str): Authentication token for LLM API
        model (str, optional): LLM model to use. Defaults to "gpt-4".
        temperature (float, optional): Temperature parameter for LLM. Defaults to 0.0.
    
    Returns:
        List[Dict[str, Any]]: List of test case summaries
    """
    if not test_cases:
        logger.warning(f"No test cases provided for sheet '{sheet_name}'")
        return []
    
    logger.info(f"Batch summarizing {len(test_cases)} test cases from sheet '{sheet_name}' with model: {model}")
    
    # Construct a prompt with all test cases
    batch_prompt = f"""# Test Cases Batch Summarization

You are analyzing a sheet of test cases from an Excel file. Each row represents a single test case.
You will extract and summarize information for ALL the test cases in this sheet in a SINGLE response.

## Sheet Information

Sheet Name: {sheet_name}
Number of Test Cases: {len(test_cases)}

## Test Cases to Analyze

"""

    # Add each test case to the prompt
    for i, test_case in enumerate(test_cases):
        test_number = test_case.get("test_case_number", f"{i+1}")
        test_name = test_case.get("test_case_name", f"Test Case {test_number}")
        
        batch_prompt += f"""### Test Case {test_number}: {test_name}

```
{test_case.get("markdown", "No data available")}
```

"""

    # Add instructions for the response format
    batch_prompt += """## Instructions

For EACH test case, analyze and extract:
1. The purpose of the test
2. Key inputs or conditions required
3. Expected results or acceptance criteria
4. Any notable observations

Provide your analysis in a structured JSON format that will be parsed by a function. 
Do not include any explanatory text outside the JSON response.

The JSON should be an array of test case summaries, where each summary includes the following fields:
- sheet_name: The name of the sheet (provided above)
- test_case_number: The identifier for the test case
- test_case_name: The name or title of the test case
- purpose: A brief description of what the test is checking
- inputs: Key inputs or conditions for the test
- expected_results: Expected outputs or acceptance criteria
- observations: Any notable observations or special handling required
- comprehensive_summary: A detailed summary of the test case

Your response should include a summary for ALL test cases in the provided list.
"""

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an expert at analyzing and summarizing software test cases. You can extract structured information from multiple test cases at once."},
        {"role": "user", "content": batch_prompt}
    ]

    try:
        # Define a tool for structured extraction
        batch_summarization_tool = {
            "type": "function",
            "function": {
                "name": "extract_test_case_summaries",
                "description": "Extract structured summaries from multiple test cases",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_case_summaries": {
                            "type": "array",
                            "description": "Array of test case summaries",
                            "items": {
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
                    },
                    "required": ["test_case_summaries"]
                }
            }
        }
        
        # Call LLM with tool
        logger.info(f"Calling LLM to summarize {len(test_cases)} test cases at once")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4000,  # Increase token limit for batch processing
            tools=[batch_summarization_tool],
            tool_choice={"type": "function", "function": {"name": "extract_test_case_summaries"}}
        )

        # Create a mapping of test case numbers to their original data for reference
        test_case_map = {tc.get("test_case_number", str(i)): tc for i, tc in enumerate(test_cases)}
        
        try:
            # Extract the structured summaries from the tool call
            message = response.choices[0].message
            
            # Check if we got a tool call
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Extract the function call arguments
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "extract_test_case_summaries":
                    # Parse the function arguments as JSON
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info("Successfully extracted batch summaries from tool call")
                    
                    # Get the test case summaries from the response
                    summaries = function_args.get("test_case_summaries", [])
                    
                    # Add metadata and original test case information
                    for summary in summaries:
                        test_case_number = summary.get("test_case_number")
                        original_test_case = test_case_map.get(test_case_number, {})
                        
                        # Add original test case data for reference
                        summary["original_test_case"] = {
                            "markdown": original_test_case.get("markdown", ""),
                            "row_index": original_test_case.get("row_index", 0)
                        }
                        
                        # Add metadata to summary
                        summary["metadata"] = {
                            "model": model,
                            "temperature": temperature,
                            "batch_processed": True
                        }
                    
                    # Add usage data if available
                    if usage_details:
                        # Since this is a batch, divide usage across all test cases
                        usage_per_case = {}
                        for k, v in usage_details.items():
                            if isinstance(v, (int, float)) and k not in ('model', 'response_time_ms', 'cost'):
                                usage_per_case[k] = v / len(test_cases) if len(test_cases) > 0 else v
                            else:
                                usage_per_case[k] = v
                                
                        for summary in summaries:
                            summary["metadata"]["usage"] = usage_per_case
                    
                    logger.info(f"Successfully processed {len(summaries)} test case summaries")
                    return summaries
                else:
                    logger.error(f"Unexpected tool call: {tool_call.function.name}")
            else:
                # Fallback to content if no tool call
                logger.warning("No tool call found in response, trying to extract from content")
                content = message.content
                if content:
                    try:
                        # Try to extract JSON array from the content
                        if "```json" in content:
                            json_block = content.split("```json")[1].split("```")[0].strip()
                            extracted_data = json.loads(json_block)
                        else:
                            extracted_data = json.loads(content)
                        
                        # Check if it's an array or object with test_case_summaries key
                        if isinstance(extracted_data, list):
                            summaries = extracted_data
                        elif isinstance(extracted_data, dict) and "test_case_summaries" in extracted_data:
                            summaries = extracted_data["test_case_summaries"]
                        else:
                            logger.error("Unexpected JSON structure in response")
                            return _create_default_summaries(test_cases, model, temperature, usage_details)
                        
                        # Add metadata and original test case information
                        for summary in summaries:
                            test_case_number = summary.get("test_case_number")
                            original_test_case = test_case_map.get(test_case_number, {})
                            
                            # Add original test case data
                            summary["original_test_case"] = {
                                "markdown": original_test_case.get("markdown", ""),
                                "row_index": original_test_case.get("row_index", 0)
                            }
                            
                            # Add metadata
                            summary["metadata"] = {
                                "model": model,
                                "temperature": temperature,
                                "batch_processed": True
                            }
                            
                            # Add usage data if available
                            if usage_details:
                                # Since this is a batch, divide usage across all test cases
                                usage_per_case = {}
                                for k, v in usage_details.items():
                                    if isinstance(v, (int, float)) and k not in ('model', 'response_time_ms', 'cost'):
                                        usage_per_case[k] = v / len(test_cases) if len(test_cases) > 0 else v
                                    else:
                                        usage_per_case[k] = v
                                        
                                summary["metadata"]["usage"] = usage_per_case
                        
                        logger.info(f"Successfully processed {len(summaries)} test case summaries from content")
                        return summaries
                    except Exception as parse_error:
                        logger.error(f"Failed to extract JSON from content: {str(parse_error)}")
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
        
        # If we reach here, something went wrong - return default summaries
        return _create_default_summaries(test_cases, model, temperature, usage_details)
    
    except Exception as e:
        logger.error(f"Error in batch summarization: {str(e)}")
        return _create_default_summaries(test_cases, model, temperature)


def _create_default_summaries(
    test_cases: List[Dict[str, Any]],
    model: str,
    temperature: float,
    usage_details: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Create default summaries when the LLM fails to process the batch.
    
    Args:
        test_cases (List[Dict[str, Any]]): The original test cases
        model (str): The model used
        temperature (float): The temperature setting
        usage_details (Dict[str, Any], optional): Usage details from the LLM call
    
    Returns:
        List[Dict[str, Any]]: List of default summaries
    """
    default_summaries = []
    
    for test_case in test_cases:
        sheet_name = test_case.get("sheet_name", "Unknown")
        test_case_number = test_case.get("test_case_number", "Unknown")
        test_case_name = test_case.get("test_case_name", "Unknown")
        
        default_summary = {
            "sheet_name": sheet_name,
            "test_case_number": test_case_number,
            "test_case_name": test_case_name,
            "purpose": "Unable to determine from LLM response",
            "inputs": "Unable to determine from LLM response",
            "expected_results": "Unable to determine from LLM response",
            "observations": "Unable to determine from LLM response",
            "comprehensive_summary": f"Unable to extract summary for test case {test_case_number} from LLM response",
            "original_test_case": {
                "markdown": test_case.get("markdown", ""),
                "row_index": test_case.get("row_index", 0)
            },
            "metadata": {
                "model": model,
                "temperature": temperature,
                "batch_processed": True,
                "error": "Failed to process batch response"
            }
        }
        
        # Add usage data if available
        if usage_details:
            default_summary["metadata"]["usage"] = usage_details
        
        default_summaries.append(default_summary)
    
    return default_summaries