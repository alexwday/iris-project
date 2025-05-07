"""
Setup script for the Test Case Analysis Tool
"""

from setuptools import setup, find_packages

setup(
    name="modified_test_evaluation_tool",
    version="0.1.0",
    description="A tool for analyzing and summarizing test cases with LLM",
    author="IRIS Project Team",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.3.0",
        "openpyxl>=3.0.7",
        "openai>=1.0.0",
        "requests>=2.25.1",
        "cryptography>=39.0.0",
    ],
    entry_points={
        "console_scripts": [
            "analyze-test-cases=modified_test_evaluation_tool.main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)