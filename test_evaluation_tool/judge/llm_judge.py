"""
LLM Judge Module

This module implements the LLM-based evaluation of test results.
It processes markdown-formatted test results and generates structured evaluations.

Functions:
    evaluate_test_result: Evaluates a single test result using LLM
    aggregate_evaluations: Aggregates multiple evaluations into a summary
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from ..llm_connectors import call_llm
from .judge_prompt import JUDGE_PROMPT_TEMPLATE, AGGREGATION_PROMPT_TEMPLATE

# Get module logger
logger = logging.getLogger(__name__)


def evaluate_test_result(
    test_markdown: str,
    oauth_token: str,
    model: str = "gpt-4",
    temperature: float = 0.0,
    save_result: bool = True,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Evaluate a single test result using LLM judge.

    Args:
        test_markdown (str): Markdown content of the test result
        oauth_token (str): Authentication token for LLM API
        model (str, optional): LLM model to use. Defaults to "gpt-4".
        temperature (float, optional): Temperature parameter for LLM. Defaults to 0.0.
        save_result (bool, optional): Whether to save evaluation to file. Defaults to True.
        output_dir (str, optional): Directory to save evaluation results. Defaults to "results".

    Returns:
        dict: Structured evaluation of the test result

    Raises:
        Exception: If LLM call fails or returns invalid JSON
    """
    logger.info(f"Evaluating test result with model: {model}")

    # Format the prompt with test result markdown
    prompt = JUDGE_PROMPT_TEMPLATE.format(test_markdown=test_markdown)

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an expert evaluator of AI assistant test results."},
        {"role": "user", "content": prompt}
    ]

    try:
        # Define a tool for structured extraction
        evaluation_tool = {
            "type": "function",
            "function": {
                "name": "extract_evaluation",
                "description": "Extract structured evaluation from test results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_selection": {
                            "type": "object",
                            "properties": {
                                "correct": {
                                    "type": ["boolean", "null"],
                                    "description": "Whether the database selection was correct (true/false) or unknown (null)"
                                },
                                "score": {
                                    "type": ["number", "null"],
                                    "description": "Numerical score if available (1-5) or null"
                                },
                                "comments": {
                                    "type": "string",
                                    "description": "Brief explanation based on reviewer notes"
                                }
                            },
                            "required": ["correct", "comments"]
                        },
                        "document_selection": {
                            "type": "object",
                            "properties": {
                                "correct": {
                                    "type": ["boolean", "null"],
                                    "description": "Whether the document selection was correct (true/false) or unknown (null)"
                                },
                                "score": {
                                    "type": ["number", "null"],
                                    "description": "Numerical score if available (1-5) or null"
                                },
                                "comments": {
                                    "type": "string",
                                    "description": "Brief explanation based on reviewer notes"
                                }
                            },
                            "required": ["correct", "comments"]
                        },
                        "answer_accuracy": {
                            "type": "object",
                            "properties": {
                                "score": {
                                    "type": ["number", "null"],
                                    "description": "Numerical score if available (1-5) or null"
                                },
                                "comments": {
                                    "type": "string",
                                    "description": "Brief explanation based on reviewer notes"
                                }
                            },
                            "required": ["score", "comments"]
                        },
                        "reviewer_overall_score": {
                            "type": "object",
                            "properties": {
                                "score": {
                                    "type": ["number", "null"],
                                    "description": "The overall score given by the reviewer (typically out of 5)"
                                },
                                "max_score": {
                                    "type": ["number", "null"],
                                    "description": "The maximum possible score (typically 5)"
                                },
                                "comments": {
                                    "type": "string",
                                    "description": "Any overall comments from the reviewer"
                                }
                            },
                            "required": ["score"]
                        },
                        "percentage_score": {
                            "type": "object",
                            "properties": {
                                "database_selection_pct": {
                                    "type": ["number", "null"],
                                    "description": "Percentage score for database selection (0-100)"
                                },
                                "document_selection_pct": {
                                    "type": ["number", "null"],
                                    "description": "Percentage score for document selection (0-100)"
                                },
                                "answer_accuracy_pct": {
                                    "type": ["number", "null"],
                                    "description": "Percentage score for answer accuracy (0-100)"
                                },
                                "overall_pct": {
                                    "type": ["number", "null"],
                                    "description": "Overall percentage score (0-100)"
                                }
                            },
                            "required": ["overall_pct"]
                        },
                        "question": {
                            "type": "string",
                            "description": "The actual question that was asked to IRIS (usually found near the top of the sheet)"
                        },
                        "overall_assessment": {
                            "type": "string",
                            "description": "Short 1-2 sentence summary of the test result"
                        }
                    },
                    "required": ["database_selection", "document_selection", "answer_accuracy", "reviewer_overall_score", "percentage_score", "question", "overall_assessment"]
                }
            }
        }
        
        # Call LLM with tool
        logger.info("Calling LLM for test evaluation using function calling")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1500,
            tools=[evaluation_tool],
            tool_choice={"type": "function", "function": {"name": "extract_evaluation"}}
        )

        # Create a default template in case extraction fails
        default_template = {
            "database_selection": {
                "correct": None,
                "score": None,
                "comments": "Unable to determine from LLM response"
            },
            "document_selection": {
                "correct": None,
                "score": None,
                "comments": "Unable to determine from LLM response"
            },
            "answer_accuracy": {
                "score": None,
                "comments": "Unable to determine from LLM response"
            },
            "reviewer_overall_score": {
                "score": None,
                "max_score": 5,
                "comments": "Unable to determine from LLM response"
            },
            "percentage_score": {
                "database_selection_pct": None,
                "document_selection_pct": None,
                "answer_accuracy_pct": None,
                "overall_pct": None
            },
            "question": "Unable to extract question from sheet",
            "overall_assessment": "Unable to extract evaluation from LLM response"
        }
        
        try:
            # Extract the structured evaluation from the tool call
            message = response.choices[0].message
            
            # Check if we got a tool call
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Extract the function call arguments (the evaluation)
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "extract_evaluation":
                    # Parse the function arguments as JSON
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info("Successfully extracted evaluation from tool call")
                    evaluation = function_args
                else:
                    logger.error(f"Unexpected tool call: {tool_call.function.name}")
                    evaluation = default_template
            else:
                # Fallback to content if no tool call
                logger.warning("No tool call found in response, trying to extract from content")
                content = message.content
                if not content:
                    logger.error("No content found in response")
                    evaluation = default_template
                else:
                    # Try to extract JSON from the content
                    try:
                        # Try different methods to extract JSON
                        if "```json" in content:
                            # Extract from code blocks
                            json_block = content.split("```json")[1].split("```")[0].strip()
                            evaluation = json.loads(json_block)
                            logger.info("Extracted JSON from markdown code block")
                        else:
                            # Try to parse the entire content as JSON
                            evaluation = json.loads(content)
                            logger.info("Parsed entire content as JSON")
                    except Exception as parse_error:
                        logger.error(f"Failed to extract JSON from content: {str(parse_error)}")
                        evaluation = default_template
        except Exception as e:
            logger.error(f"Error processing LLM response: {str(e)}")
            evaluation = default_template
            
        # Validate and ensure the evaluation has the expected structure
        for field in ["database_selection", "document_selection", "answer_accuracy", "reviewer_overall_score", "percentage_score"]:
            if field not in evaluation:
                logger.warning(f"Field '{field}' missing from evaluation, adding default")
                evaluation[field] = default_template[field]
            else:
                # Ensure nested structure is valid based on field type
                if field in ["database_selection", "document_selection", "answer_accuracy"]:
                    for required in ["comments"]:
                        if required not in evaluation[field]:
                            evaluation[field][required] = default_template[field][required]
                
                elif field == "reviewer_overall_score":
                    if "max_score" not in evaluation[field]:
                        evaluation[field]["max_score"] = 5
                
                elif field == "percentage_score":
                    for pct_field in ["database_selection_pct", "document_selection_pct", "answer_accuracy_pct", "overall_pct"]:
                        if pct_field not in evaluation[field]:
                            evaluation[field][pct_field] = None
        
        # Ensure question and overall assessment are present        
        if "question" not in evaluation:
            evaluation["question"] = default_template["question"]
                
        if "overall_assessment" not in evaluation:
            evaluation["overall_assessment"] = default_template["overall_assessment"]
        
        # Add metadata to evaluation
        evaluation["metadata"] = {
            "model": model,
            "temperature": temperature
        }
        
        # Add usage data if available
        if usage_details:
            evaluation["metadata"]["usage"] = usage_details
        
        # Save evaluation to file if requested
        if save_result:
            _save_evaluation(evaluation, output_dir)
        
        return evaluation
    
    except Exception as e:
        logger.error(f"Error evaluating test result: {str(e)}")
        raise


def aggregate_evaluations(
    evaluations: List[Dict[str, Any]],
    oauth_token: str,
    model: str = "gpt-4",
    temperature: float = 0.0,
    save_result: bool = True,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Aggregate multiple test evaluations into a summary.

    Args:
        evaluations (list): List of evaluation dictionaries
        oauth_token (str): Authentication token for LLM API
        model (str, optional): LLM model to use. Defaults to "gpt-4".
        temperature (float, optional): Temperature parameter for LLM. Defaults to 0.0.
        save_result (bool, optional): Whether to save summary to file. Defaults to True.
        output_dir (str, optional): Directory to save results. Defaults to "results".

    Returns:
        dict: Aggregated summary of all evaluations

    Raises:
        Exception: If LLM call fails
    """
    logger.info(f"Aggregating {len(evaluations)} test evaluations with model: {model}")

    # Format evaluations as text
    evaluation_text = json.dumps(evaluations, indent=2)
    
    # Format the prompt
    prompt = AGGREGATION_PROMPT_TEMPLATE.format(evaluation_results=evaluation_text)

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an expert at synthesizing test evaluation results."},
        {"role": "user", "content": prompt}
    ]

    try:
        # Call LLM
        logger.info("Calling LLM for evaluation aggregation")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2500
        )

        # Extract the summary from the response
        summary = response.choices[0].message.content.strip()
        
        # Prepare result object
        result = {
            "summary": summary,
            "metadata": {
                "model": model,
                "temperature": temperature,
                "evaluations_count": len(evaluations)
            }
        }
        
        # Add usage data if available
        if usage_details:
            result["metadata"]["usage"] = usage_details
        
        # Save summary to file if requested
        if save_result:
            _save_summary(result, output_dir)
        
        return result
    
    except Exception as e:
        logger.error(f"Error aggregating evaluations: {str(e)}")
        raise


def _save_evaluation(
    evaluation: Dict[str, Any],
    output_dir: str,
    filename: Optional[str] = None
) -> None:
    """
    Save evaluation result to a JSON file.

    Args:
        evaluation (dict): Evaluation result to save
        output_dir (str): Directory to save the file
        filename (str, optional): Custom filename. Defaults to auto-generated name.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            import time
            timestamp = int(time.time())
            filename = f"evaluation_{timestamp}.json"
        
        # Full file path
        file_path = os.path.join(output_dir, filename)
        
        # Write evaluation to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2)
            
        logger.info(f"Evaluation saved to: {file_path}")
    
    except Exception as e:
        logger.error(f"Error saving evaluation to file: {str(e)}")
        # Don't raise - this is a non-critical operation


def _save_summary(
    summary: Dict[str, Any],
    output_dir: str,
    filename: str = "summary.json"
) -> None:
    """
    Save aggregated summary to a JSON file.

    Args:
        summary (dict): Summary result to save
        output_dir (str): Directory to save the file
        filename (str, optional): Filename. Defaults to "summary.json".
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Full file path
        file_path = os.path.join(output_dir, filename)
        
        # Write summary to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
            
        # Also save as markdown for easy reading
        md_file_path = os.path.join(output_dir, "summary.md")
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write("# Test Evaluation Summary\n\n")
            f.write(summary["summary"])
            
        logger.info(f"Summary saved to: {file_path} and {md_file_path}")
    
    except Exception as e:
        logger.error(f"Error saving summary to file: {str(e)}")
        # Don't raise - this is a non-critical operation