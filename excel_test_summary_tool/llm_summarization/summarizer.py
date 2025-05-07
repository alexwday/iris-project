"""Process test cases with LLM for summarization."""

import os
import logging
from typing import Dict, List, Optional, Tuple

from ..config import (
    TEST_CASE_SUMMARY_PROMPT,
    SYSTEM_SUMMARY_PROMPT,
    FILE_LEVEL_SUMMARY_PROMPT,
    LLM_MODEL,
    LLM_TEMPERATURE,
    SUMMARY_OUTPUT_DIR
)
from .llm_connector import summarize_test_case, summarize_system_tests, create_file_level_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_summary_directory() -> None:
    """Create directory for summary files if it doesn't exist."""
    os.makedirs(SUMMARY_OUTPUT_DIR, exist_ok=True)


def process_test_case(
    api_key: str,
    test_id: str,
    system_name: str,
    markdown_file_path: str,
    prompt_template: Optional[str] = None
) -> Dict:
    """
    Process a single test case with the LLM and return the summary details.
    
    Args:
        api_key: OpenAI API key
        test_id: Unique identifier for the test case
        system_name: Name of the system/sheet
        markdown_file_path: Path to the test case markdown file
        prompt_template: Optional custom prompt template
        
    Returns:
        Dictionary with test case details and summary
    """
    logger.info(f"Processing test case: {test_id}")
    
    # Read the markdown file
    with open(markdown_file_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Use default prompt if not provided
    if prompt_template is None:
        prompt_template = TEST_CASE_SUMMARY_PROMPT
    
    # Get summary from LLM
    summary = summarize_test_case(
        api_key=api_key,
        markdown_content=markdown_content,
        prompt_template=prompt_template,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE
    )
    
    # Extract test case name if available in markdown
    test_case_name = "Unknown"
    for line in markdown_content.split("\n"):
        if line.startswith("### Test Case Name") or line.startswith("### Test Name"):
            test_case_name_line = markdown_content.split(line)[1].strip()
            if test_case_name_line and len(test_case_name_line.split("\n")) > 0:
                test_case_name = test_case_name_line.split("\n")[0].strip()
                break
    
    # Extract test number if available
    test_number = None
    for line in markdown_content.split("\n"):
        for sr_prefix in ["### Sr.No", "### Sr. No", "### Sr.No.", "### Test ID", "### ID"]:
            if line.startswith(sr_prefix):
                test_number_line = markdown_content.split(line)[1].strip()
                if test_number_line and len(test_number_line.split("\n")) > 0:
                    test_number = test_number_line.split("\n")[0].strip()
                    break
        if test_number:
            break
    
    # Create a result dictionary
    result = {
        "test_id": test_id,
        "system_name": system_name,
        "test_case_name": test_case_name,
        "test_number": test_number,
        "summary": summary
    }
    
    # Save the summary to a file
    summary_file_path = os.path.join(SUMMARY_OUTPUT_DIR, f"{test_id}_summary.md")
    with open(summary_file_path, 'w', encoding='utf-8') as f:
        f.write(f"# Test Case Summary: {test_case_name}\n\n")
        f.write(f"**System:** {system_name}\n\n")
        if test_number:
            f.write(f"**Test Number:** {test_number}\n\n")
        f.write(f"**Summary:**\n\n{summary}\n")
    
    logger.info(f"Processed test case: {test_id}")
    return result


def process_all_test_cases(
    api_key: str,
    test_cases: List[Tuple[str, str, str]]
) -> Dict[str, List[Dict]]:
    """
    Process all test cases with the LLM and organize results by system.
    
    Args:
        api_key: OpenAI API key
        test_cases: List of tuples (system_name, test_id, markdown_file_path)
        
    Returns:
        Dictionary mapping system names to lists of test case summaries
    """
    # Create summary directory
    create_summary_directory()
    
    # Process each test case and organize by system
    system_test_cases = {}
    
    for system_name, test_id, markdown_file_path in test_cases:
        # Initialize system entry if not exists
        if system_name not in system_test_cases:
            system_test_cases[system_name] = []
        
        # Process the test case
        result = process_test_case(
            api_key=api_key,
            test_id=test_id,
            system_name=system_name,
            markdown_file_path=markdown_file_path
        )
        
        # Add to system list
        system_test_cases[system_name].append(result)
    
    return system_test_cases


def create_system_summaries(
    api_key: str,
    system_test_cases: Dict[str, List[Dict]],
    prompt_template: Optional[str] = None
) -> Dict[str, str]:
    """
    Create system-level summaries from test case summaries.
    
    Args:
        api_key: OpenAI API key
        system_test_cases: Dictionary mapping system names to lists of test case summaries
        prompt_template: Optional custom prompt template
        
    Returns:
        Dictionary mapping system names to system-level summaries
    """
    system_summaries = {}
    
    # Use default prompt if not provided
    if prompt_template is None:
        prompt_template = SYSTEM_SUMMARY_PROMPT
    
    for system_name, test_cases in system_test_cases.items():
        logger.info(f"Creating system summary for: {system_name}")
        
        # Combine test case summaries for this system
        all_summaries = ""
        for i, test_case in enumerate(test_cases, 1):
            all_summaries += f"Test {i}: {test_case['test_case_name']}\n"
            if test_case.get('test_number'):
                all_summaries += f"Test Number: {test_case['test_number']}\n"
            all_summaries += f"Summary:\n{test_case['summary']}\n\n---\n\n"
        
        # Get summary from LLM
        system_summary = summarize_system_tests(
            api_key=api_key,
            system_name=system_name,
            test_summaries=all_summaries,
            prompt_template=prompt_template,
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE
        )
        
        system_summaries[system_name] = system_summary
        
        # Save the system summary to a file
        system_file_path = os.path.join(SUMMARY_OUTPUT_DIR, f"{system_name}_system_summary.md")
        with open(system_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# System Summary: {system_name}\n\n")
            f.write(f"{system_summary}\n\n")
            f.write("## Individual Test Cases:\n\n")
            for test_case in test_cases:
                f.write(f"### {test_case['test_case_name']}\n")
                if test_case.get('test_number'):
                    f.write(f"**Test Number:** {test_case['test_number']}\n\n")
                f.write(f"{test_case['summary']}\n\n")
        
        logger.info(f"Created system summary for: {system_name}")
    
    return system_summaries


def create_file_summary(
    api_key: str,
    system_summaries: Dict[str, str],
    prompt_template: Optional[str] = None
) -> str:
    """
    Create a file-level summary from all system summaries.
    
    Args:
        api_key: OpenAI API key
        system_summaries: Dictionary mapping system names to system-level summaries
        prompt_template: Optional custom prompt template
        
    Returns:
        File-level summary
    """
    logger.info("Creating file-level summary")
    
    # Use default prompt if not provided
    if prompt_template is None:
        prompt_template = FILE_LEVEL_SUMMARY_PROMPT
    
    # Combine all system summaries
    all_summaries = ""
    for system_name, summary in system_summaries.items():
        all_summaries += f"System: {system_name}\n\n{summary}\n\n---\n\n"
    
    # Get summary from LLM
    file_summary = create_file_level_summary(
        api_key=api_key,
        system_summaries=all_summaries,
        prompt_template=prompt_template,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE
    )
    
    # Save the file summary
    file_summary_path = os.path.join(SUMMARY_OUTPUT_DIR, "file_level_summary.md")
    with open(file_summary_path, 'w', encoding='utf-8') as f:
        f.write("# File-Level Test Summary\n\n")
        f.write(f"{file_summary}\n\n")
        f.write("## System Summaries:\n\n")
        for system_name, summary in system_summaries.items():
            f.write(f"### {system_name}\n\n")
            f.write(f"{summary}\n\n")
    
    logger.info("Created file-level summary")
    return file_summary