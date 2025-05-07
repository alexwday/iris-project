"""
Excel to Markdown Conversion Module

This module provides functionality to convert Excel sheets to markdown format
for processing by LLM models.

The module is specialized for converting test case data, where each sheet contains 
multiple test cases, typically with one test case per row.

Functions:
    excel_to_markdown: Converts Excel data to markdown format
    extract_test_cases: Extracts individual test cases from a sheet
"""

import logging
import os
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

# Import config but don't rely on specific variables that were removed
from .. import config

# Get module logger
logger = logging.getLogger(__name__)


def excel_to_markdown(
    file_path: str,
    sheet_name: Optional[Union[str, int]] = None,
    separate_sheets: bool = True
) -> Union[str, Dict[str, str]]:
    """
    Convert Excel sheet data to markdown format, preserving the original structure.
    This function captures the entire active area of each sheet, including all columns
    and rows with data, and converts it to a markdown table.

    Args:
        file_path (str): Path to the Excel file
        sheet_name (str|int, optional): Sheet name or index to process. 
                                      If None, processes all sheets.
        separate_sheets (bool): If True, returns a dictionary with sheet names as keys
                               and markdown content as values. If False, returns a single
                               markdown string with all sheets.

    Returns:
        Union[str, Dict[str, str]]: If separate_sheets is True, returns a dictionary mapping
                                   sheet names to markdown content. Otherwise, returns a single
                                   markdown string with all sheets.

    Raises:
        FileNotFoundError: If Excel file does not exist
        ValueError: If specified sheet is not found
    """
    # Check if file exists
    if not os.path.exists(file_path):
        error_msg = f"Excel file not found at {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    logger.info(f"Processing Excel file: {file_path}")
    
    try:
        # Read Excel file
        xl = pd.ExcelFile(file_path)
        
        # Get sheet names
        sheet_names = xl.sheet_names
        logger.info(f"Found sheets: {sheet_names}")
        
        if sheet_name is not None:
            # Process a single sheet
            if isinstance(sheet_name, str) and sheet_name not in sheet_names:
                error_msg = f"Sheet '{sheet_name}' not found in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Converting sheet: {sheet_name}")
            markdown = _convert_sheet_to_markdown(xl, sheet_name)
            if separate_sheets:
                return {str(sheet_name): markdown}
            else:
                return f"## Sheet: {sheet_name}\n\n{markdown}"
        else:
            # Process all sheets
            logger.info(f"Converting all sheets")
            
            if separate_sheets:
                # Return a dictionary with sheet names as keys
                result = {}
                for sheet in sheet_names:
                    logger.info(f"Converting sheet: {sheet}")
                    sheet_md = _convert_sheet_to_markdown(xl, sheet)
                    result[sheet] = sheet_md
                return result
            else:
                # Return a single markdown string with all sheets
                md_content = []
                for sheet in sheet_names:
                    logger.info(f"Converting sheet: {sheet}")
                    sheet_md = _convert_sheet_to_markdown(xl, sheet)
                    md_content.append(f"## Sheet: {sheet}\n\n{sheet_md}")
                return "\n\n".join(md_content)
    
    except Exception as e:
        logger.error(f"Error converting Excel to markdown: {str(e)}")
        raise


def _convert_sheet_to_markdown(
    excel_file: pd.ExcelFile,
    sheet_name: Union[str, int]
) -> str:
    """
    Convert a single Excel sheet to markdown format, preserving the original structure.

    Args:
        excel_file (pd.ExcelFile): Excel file object
        sheet_name (str|int): Sheet name or index to process

    Returns:
        str: Markdown representation of the sheet
    """
    # Read sheet into pandas DataFrame with all data preserved
    df = excel_file.parse(sheet_name, header=None)
    
    # Detect valid data ranges - find non-empty cells
    # First filter out completely empty rows and columns
    non_empty_rows = df.notnull().any(axis=1)
    non_empty_cols = df.notnull().any(axis=0)
    
    # Get the indices of non-empty rows and columns
    valid_rows = non_empty_rows[non_empty_rows].index
    valid_cols = non_empty_cols[non_empty_cols].index
    
    if len(valid_rows) == 0 or len(valid_cols) == 0:
        logger.warning(f"Sheet '{sheet_name}' appears to be empty")
        return "*This sheet contains no data*"
    
    # Get min/max row and column indices
    min_row = valid_rows.min()
    max_row = valid_rows.max()
    min_col = valid_cols.min()
    max_col = valid_cols.max()
    
    # Extract the active data area
    active_df = df.iloc[min_row:max_row + 1, min_col:max_col + 1]
    
    # Number of columns in active data
    num_cols = len(active_df.columns)
    
    # Initialize markdown content
    md_lines = []
    
    # Create header row with column letters
    col_headers = [chr(ord('A') + min_col + i) for i in range(num_cols)]
    md_lines.append("| " + " | ".join(col_headers) + " |")
    md_lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    
    # Process each row in the active area
    for row_idx in range(len(active_df)):
        # Extract and format cell values for this row
        row_values = []
        
        for col_idx in range(num_cols):
            cell_value = active_df.iloc[row_idx, col_idx]
            
            # Handle NaN, None values
            if pd.isna(cell_value):
                row_values.append("")
            else:
                # Format cell value, handle special characters
                # Replace pipe characters to avoid breaking markdown tables
                cell_str = str(cell_value).replace("|", "\\|")
                # Handle line breaks within cells
                cell_str = cell_str.replace("\n", "<br>")
                row_values.append(cell_str)
        
        # Add row to markdown
        md_lines.append("| " + " | ".join(row_values) + " |")
    
    # Return the complete markdown table
    return "\n".join(md_lines)


def extract_test_cases(
    file_path: str,
    sheet_name: Optional[Union[str, int]] = None,
    group_by_sheet: bool = False
) -> Union[List[Dict[str, any]], Dict[str, List[Dict[str, any]]]]:
    """
    Extract individual test cases from Excel sheets.
    
    This function assumes each row in a sheet represents a test case,
    and processes each sheet to identify and extract test cases.
    
    Args:
        file_path (str): Path to the Excel file
        sheet_name (str|int, optional): Sheet name or index to process. 
                                       If None, processes all sheets.
        group_by_sheet (bool, optional): If True, returns test cases grouped by sheet name.
                                        If False, returns a flat list of all test cases.
    
    Returns:
        If group_by_sheet is False:
            List[Dict[str, any]]: List of test cases with their metadata and content
        If group_by_sheet is True:
            Dict[str, List[Dict[str, any]]]: Dictionary with sheet names as keys and lists of test cases as values
    """
    # Check if file exists
    if not os.path.exists(file_path):
        error_msg = f"Excel file not found at {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info(f"Extracting test cases from Excel file: {file_path}")
    
    try:
        # Read Excel file
        xl = pd.ExcelFile(file_path)
        
        # Get sheet names
        sheet_names = xl.sheet_names
        logger.info(f"Found sheets: {sheet_names}")
        
        # Container for test cases
        all_test_cases = []
        # For grouped results
        sheet_test_cases = {}
        
        if sheet_name is not None:
            # Process a single sheet
            if isinstance(sheet_name, str) and sheet_name not in sheet_names:
                error_msg = f"Sheet '{sheet_name}' not found in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            process_sheets = [sheet_name]
        else:
            # Process all sheets
            process_sheets = sheet_names
        
        # Process each sheet
        for sheet in process_sheets:
            logger.info(f"Extracting test cases from sheet: {sheet}")
            
            # Initialize list for this sheet's test cases if grouping
            if group_by_sheet:
                sheet_test_cases[str(sheet)] = []
            
            # Convert sheet to markdown
            sheet_md = _convert_sheet_to_markdown(xl, sheet)
            
            # Create a test case for each row (excluding header row)
            sheet_df = xl.parse(sheet, header=0)  # Assuming first row is header
            
            # Skip if sheet is empty
            if sheet_df.empty:
                logger.warning(f"Sheet '{sheet}' is empty")
                continue
            
            # Process each row as a test case
            for idx, row in sheet_df.iterrows():
                try:
                    # Try to get test case number and name from the row
                    # Assuming standard columns for test case information
                    test_case_number = None
                    test_case_name = None
                    
                    # Look for columns that might contain test case number or name
                    for col in sheet_df.columns:
                        col_lower = str(col).lower()
                        
                        # Common patterns for test case number columns
                        if any(term in col_lower for term in ["case #", "case no", "test #", "test no", "id", "tc#"]):
                            test_case_number = str(row[col])
                        
                        # Common patterns for test case name columns
                        if any(term in col_lower for term in ["name", "title", "description", "summary"]):
                            if pd.notna(row[col]):
                                test_case_name = str(row[col])
                    
                    # If we couldn't find a number, use the row index
                    if test_case_number is None or pd.isna(test_case_number):
                        test_case_number = f"{idx+1}"
                    
                    # If we couldn't find a name, use a generic name
                    if test_case_name is None or pd.isna(test_case_name) or not test_case_name.strip():
                        test_case_name = f"Test Case {test_case_number}"
                    
                    # Convert row to markdown
                    row_md = "| " + " | ".join([str(val) if pd.notna(val) else "" for val in row]) + " |"
                    
                    # Create header row with column names
                    header_md = "| " + " | ".join([str(col) for col in sheet_df.columns]) + " |"
                    separator_md = "| " + " | ".join(["---"] * len(sheet_df.columns)) + " |"
                    
                    # Combine to create markdown for this test case
                    test_case_md = f"{header_md}\n{separator_md}\n{row_md}"
                    
                    # Create test case dictionary
                    test_case = {
                        "sheet_name": str(sheet),
                        "test_case_number": test_case_number,
                        "test_case_name": test_case_name,
                        "row_index": idx,
                        "markdown": test_case_md,
                        "full_sheet_markdown": sheet_md  # Include full sheet for context
                    }
                    
                    # Add test case to appropriate container
                    if group_by_sheet:
                        sheet_test_cases[str(sheet)].append(test_case)
                    else:
                        all_test_cases.append(test_case)
                    
                    logger.debug(f"Extracted test case: {test_case_number} - {test_case_name}")
                    
                except Exception as row_error:
                    logger.error(f"Error processing row {idx} in sheet '{sheet}': {str(row_error)}")
                    # Continue with next row
                    continue
        
        # Return test cases in the appropriate format
        if group_by_sheet:
            # Remove any empty sheets
            sheet_test_cases = {sheet: cases for sheet, cases in sheet_test_cases.items() if cases}
            total_cases = sum(len(cases) for cases in sheet_test_cases.values())
            logger.info(f"Extracted {total_cases} test cases from {len(sheet_test_cases)} sheets (grouped by sheet)")
            return sheet_test_cases
        else:
            logger.info(f"Extracted {len(all_test_cases)} test cases from {len(process_sheets)} sheets")
            return all_test_cases
    
    except Exception as e:
        logger.error(f"Error extracting test cases from Excel: {str(e)}")
        raise


def save_markdown_to_file(
    markdown_content: str,
    output_file_path: str
) -> None:
    """
    Save markdown content to a file.

    Args:
        markdown_content (str): Markdown content to save
        output_file_path (str): Path to save the markdown file

    Raises:
        IOError: If file cannot be written
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        # Write markdown content to file
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        logger.info(f"Markdown saved to: {output_file_path}")
    
    except Exception as e:
        logger.error(f"Error saving markdown to file: {str(e)}")
        raise