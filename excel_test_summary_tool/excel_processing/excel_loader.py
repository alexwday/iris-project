"""Excel file loading and parsing functions."""

import os
import pandas as pd
from typing import Dict, List, Tuple


def load_excel_file(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Load an Excel file and return a dictionary of DataFrames, one per sheet.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dictionary mapping sheet names to pandas DataFrames
        
    Raises:
        FileNotFoundError: If the Excel file is not found
        ValueError: If the Excel file is empty or has no sheets
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    
    # Load the Excel file with pandas
    excel_data = pd.read_excel(file_path, sheet_name=None)
    
    if not excel_data:
        raise ValueError(f"Excel file is empty or has no sheets: {file_path}")
    
    # Clean up sheet data
    for sheet_name, df in excel_data.items():
        # Skip empty sheets
        if df.empty:
            continue
            
        # Drop completely empty rows
        excel_data[sheet_name] = df.dropna(how='all')
        
        # Make sure first row is treated as header
        excel_data[sheet_name].columns = excel_data[sheet_name].iloc[0] \
            if excel_data[sheet_name].columns.str.contains("Unnamed").any() \
            else excel_data[sheet_name].columns
        
        # If headers were in first row, drop that row
        if excel_data[sheet_name].columns.equals(excel_data[sheet_name].iloc[0]):
            excel_data[sheet_name] = excel_data[sheet_name].iloc[1:].reset_index(drop=True)
        
        # Clean column names and convert to string
        excel_data[sheet_name].columns = excel_data[sheet_name].columns.astype(str).str.strip()
    
    return excel_data


def get_test_case_data(excel_data: Dict[str, pd.DataFrame]) -> List[Tuple[str, Dict]]:
    """
    Extract test case data from Excel sheets.
    
    Args:
        excel_data: Dictionary mapping sheet names to pandas DataFrames
        
    Returns:
        List of tuples containing (sheet_name, test_case_dict)
    """
    all_test_cases = []
    
    for sheet_name, df in excel_data.items():
        # Skip empty sheets
        if df.empty:
            continue
            
        # Convert each row to a dictionary
        for _, row in df.iterrows():
            # Convert row to dictionary, handling NaN values
            test_case = {}
            for col in df.columns:
                if pd.notna(row[col]):
                    test_case[col] = row[col]
            
            # Add to the list
            all_test_cases.append((sheet_name, test_case))
    
    return all_test_cases


def create_unique_test_id(sheet_name: str, test_case: Dict) -> str:
    """
    Create a unique ID for a test case based on sheet name and test case details.
    
    Args:
        sheet_name: Name of the sheet
        test_case: Test case dictionary
        
    Returns:
        A unique ID string
    """
    # Try to use Sr.No or test case ID if available
    test_id = None
    for id_field in ['Sr.No', 'Sr. No', 'Sr.No.', 'Test Case ID', 'ID', 'Test ID']:
        if id_field in test_case:
            test_id = str(test_case[id_field]).strip()
            break
    
    # If no ID field found, try to use Test Case Name
    if not test_id:
        for name_field in ['Test Case Name', 'Test Name', 'Name', 'Test Case']:
            if name_field in test_case:
                # Create a slug from the test name
                test_id = str(test_case[name_field]).lower().replace(' ', '_')[:30]
                break
    
    # If still no ID, use a fallback
    if not test_id:
        test_id = 'test'
    
    # Return a unique ID combining sheet name and test ID
    sheet_slug = sheet_name.lower().replace(' ', '_')
    return f"{sheet_slug}_{test_id}"