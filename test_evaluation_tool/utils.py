"""
Utility Functions for Test Evaluation Tool

This module provides various utility functions for the test evaluation tool.
"""

import logging
import os
import sys
from typing import Dict, List, Optional

# Get module logger
logger = logging.getLogger(__name__)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True
) -> None:
    """
    Configure logging settings for the test evaluation tool.

    Args:
        log_level (str, optional): Logging level. Defaults to "INFO".
        log_file (str, optional): Path to log file. If None, file logging is disabled.
        console_output (bool, optional): Whether to output logs to console. Defaults to True.
    """
    # Convert log level string to logging constant
    level_dict = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level_value = level_dict.get(log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_value)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if log_file is provided
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logger.debug("Logging configured")


def find_excel_files(
    directory: str,
    recursive: bool = True,
    extensions: List[str] = [".xlsx", ".xls", ".xlsm"]
) -> List[str]:
    """
    Find all Excel files in a directory.

    Args:
        directory (str): Directory to search
        recursive (bool, optional): Whether to search subdirectories. Defaults to True.
        extensions (List[str], optional): File extensions to include. 
                                       Defaults to [".xlsx", ".xls", ".xlsm"].

    Returns:
        List[str]: List of Excel file paths
    """
    excel_files = []
    
    # Check if directory exists
    if not os.path.exists(directory):
        logger.error(f"Directory not found: {directory}")
        return []
    
    try:
        # Walk directory structure
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        excel_files.append(os.path.join(root, file))
        else:
            # Non-recursive search
            for file in os.listdir(directory):
                if any(file.endswith(ext) for ext in extensions):
                    excel_files.append(os.path.join(directory, file))
        
        logger.info(f"Found {len(excel_files)} Excel files in {directory}")
        return excel_files
    
    except Exception as e:
        logger.error(f"Error finding Excel files: {str(e)}")
        return []