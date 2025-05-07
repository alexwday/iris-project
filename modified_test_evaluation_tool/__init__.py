"""
Test Evaluation Tool

A standalone tool for processing test results and evaluating them using LLM.
"""

# Import main components for easy access
from .excel_processing import excel_to_markdown, save_markdown_to_file
from .judge import evaluate_test_result, aggregate_evaluations
from .oauth import setup_oauth
from .ssl import setup_ssl
from .utils import setup_logging, find_excel_files

__version__ = "0.1.0"