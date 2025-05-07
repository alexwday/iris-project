"""
HTML Output Module

This package provides functionality for generating HTML reports from evaluation results 
and test case summaries.
"""

from .html_generator import generate_html_report, json_to_html
from .test_summary_generator import generate_test_summary_report, test_summary_json_to_html

__all__ = ["generate_html_report", "json_to_html", "generate_test_summary_report", "test_summary_json_to_html"]