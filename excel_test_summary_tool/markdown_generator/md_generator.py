"""Generate markdown files from Excel test case data."""

import os
import re
from typing import Dict, List, Tuple


def create_markdown_directory(output_dir: str) -> None:
    """
    Create output directory for markdown files if it doesn't exist.
    
    Args:
        output_dir: Directory path to create
    """
    os.makedirs(output_dir, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: String to sanitize
        
    Returns:
        Sanitized string
    """
    # Replace non-alphanumeric characters with underscores
    sanitized = re.sub(r'[^\w\-\.]', '_', filename)
    # Remove consecutive underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    # Ensure the filename is not too long
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def test_case_to_markdown(sheet_name: str, test_case: Dict, test_id: str) -> str:
    """
    Convert a test case dictionary to markdown content.
    
    Args:
        sheet_name: Name of the sheet/system
        test_case: Dictionary of test case data
        test_id: Unique identifier for the test case
        
    Returns:
        Markdown content as a string
    """
    # Start with the sheet name as the top-level heading
    markdown = f"# System: {sheet_name}\n\n"
    
    # Add test ID if available
    markdown += f"## Test ID: {test_id}\n\n"
    
    # Add all available fields from the test case
    for field, value in test_case.items():
        # Clean up field name
        clean_field = field.strip()
        # Format value as string, handling different types
        str_value = str(value).strip() if value is not None else ""
        
        # Add the field to the markdown
        markdown += f"### {clean_field}\n\n{str_value}\n\n"
    
    return markdown


def generate_markdown_files(
    test_cases: List[Tuple[str, Dict, str]], 
    output_dir: str
) -> Dict[str, str]:
    """
    Generate markdown files for each test case.
    
    Args:
        test_cases: List of tuples (sheet_name, test_case_dict, test_id)
        output_dir: Directory to save markdown files
        
    Returns:
        Dictionary mapping test case IDs to markdown file paths
    """
    # Create output directory if it doesn't exist
    create_markdown_directory(output_dir)
    
    # Dictionary to store paths to markdown files
    markdown_files = {}
    
    # Generate markdown for each test case
    for sheet_name, test_case, test_id in test_cases:
        # Generate markdown content
        markdown_content = test_case_to_markdown(sheet_name, test_case, test_id)
        
        # Create a sanitized filename
        safe_id = sanitize_filename(test_id)
        file_path = os.path.join(output_dir, f"{safe_id}.md")
        
        # Write the markdown file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Store the path in the dictionary
        markdown_files[test_id] = file_path
    
    return markdown_files