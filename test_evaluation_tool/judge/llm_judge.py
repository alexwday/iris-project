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
        # Call LLM
        logger.info("Calling LLM for test evaluation")
        response, usage_details = call_llm(
            oauth_token=oauth_token,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1500
        )

        # Extract the evaluation from the response
        evaluation_text = response.choices[0].message.content.strip()
        
        # Create a default template in case parsing fails
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
            "overall_assessment": "Unable to parse LLM response into a valid evaluation",
            "raw_response": evaluation_text
        }
        
        # Parse JSON response
        try:
            # Try to parse the entire response as JSON
            evaluation = json.loads(evaluation_text)
            logger.info("Successfully parsed LLM response as JSON")
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks
            logger.warning("Failed to parse entire response as JSON, trying to extract JSON from code blocks")
            try:
                if "```json" in evaluation_text:
                    # Extract JSON from markdown code blocks
                    json_block = evaluation_text.split("```json")[1].split("```")[0].strip()
                    evaluation = json.loads(json_block)
                    logger.info("Successfully extracted JSON from code block")
                else:
                    # If no code blocks, try to find any JSON-like structure
                    logger.warning("No JSON code blocks found, attempting to extract JSON-like structure")
                    import re
                    json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                    if json_match:
                        evaluation = json.loads(json_match.group(0))
                        logger.info("Successfully extracted JSON-like structure")
                    else:
                        logger.error("Failed to extract valid JSON from LLM response")
                        evaluation = default_template
            except Exception as parse_error:
                logger.error(f"JSON parsing error: {str(parse_error)}")
                evaluation = default_template
        
        # Validate and ensure the evaluation has the expected structure
        for field in ["database_selection", "document_selection", "answer_accuracy"]:
            if field not in evaluation:
                logger.warning(f"Field '{field}' missing from evaluation, adding default")
                evaluation[field] = default_template[field]
                
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