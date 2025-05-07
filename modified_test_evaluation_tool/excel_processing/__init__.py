"""
Excel Processing Module

This package provides functionality for processing Excel files, extracting test cases,
and converting them to markdown format for LLM summarization.
"""

from .excel_converter import excel_to_markdown, save_markdown_to_file, extract_test_cases