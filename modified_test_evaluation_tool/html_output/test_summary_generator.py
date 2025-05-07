"""
Test Summary HTML Generator

This module creates HTML reports from test case summaries.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from .html_generator import _markdown_to_html

# Get module logger
logger = logging.getLogger(__name__)


def generate_test_summary_report(
    test_suite_analysis: Dict[str, Any],
    test_case_summaries: List[Dict[str, Any]],
    output_file: str
) -> str:
    """
    Generate an HTML report from test suite analysis and individual test case summaries.

    Args:
        test_suite_analysis (dict): The aggregated analysis of the test suite
        test_case_summaries (list): List of individual test case summaries
        output_file (str): Path to save the HTML report

    Returns:
        str: Path to the generated HTML file
    """
    logger.info("Generating test summary HTML report: %s", output_file)
    
    html_content = _generate_test_summary_html(test_suite_analysis, test_case_summaries)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write HTML to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("Test summary HTML report saved to: %s", output_file)
        return output_file
    
    except Exception as e:
        logger.error("Error saving test summary HTML report: %s", str(e))
        raise


def _generate_test_summary_html(
    test_suite_analysis: Dict[str, Any],
    test_case_summaries: List[Dict[str, Any]]
) -> str:
    """
    Generate the HTML content for the test summary report.

    Args:
        test_suite_analysis (dict): The aggregated analysis of the test suite
        test_case_summaries (list): List of individual test case summaries

    Returns:
        str: HTML content as a string
    """
    # Start with HTML template and generate timestamp and count info
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    test_case_count = len(test_case_summaries)
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Suite Analysis Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3, h4 {
            color: #2c3e50;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .report-meta {
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }
        .summary-container {
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 30px;
            line-height: 1.6;
            font-size: 1.05em;
        }
        .key-areas {
            background-color: #eef8fc;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .key-areas h3 {
            margin-top: 0;
            border-bottom: 1px solid #bde0f3;
            padding-bottom: 10px;
        }
        .key-areas ul {
            padding-left: 20px;
        }
        .recommendations {
            background-color: #f0f7fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
            border-left: 4px solid #2ecc71;
        }
        .recommendations h3 {
            margin-top: 0;
            color: #2ecc71;
            border-bottom: 1px solid #c5e9d3;
            padding-bottom: 10px;
        }
        .sheet-container {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 30px;
            overflow: hidden;
        }
        .sheet-header {
            background-color: #f1f8fb;
            padding: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sheet-header h3 {
            margin: 0;
        }
        .sheet-header .info {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        .sheet-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background-color: #ffffff;
        }
        .sheet-summary {
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .test-case {
            margin: 15px;
            padding: 15px;
            border: 1px solid #e1e8ed;
            border-radius: 5px;
            background-color: #f8fafc;
        }
        .test-case-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .test-case-title {
            font-weight: bold;
            color: #2980b9;
        }
        .test-case-id {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        .test-case-section {
            margin-top: 10px;
        }
        .test-case-section h4 {
            margin: 0 0 5px 0;
            font-size: 1em;
            color: #34495e;
        }
        .test-case-section p {
            margin: 0;
            padding: 5px 0;
        }
        .collapsible-button {
            background-color: transparent;
            border: none;
            cursor: pointer;
            font-size: 1.5em;
        }
        .active .collapsible-button::after {
            content: "−";
        }
        .collapsible-button::after {
            content: "+";
        }
        .executive-summary {
            background-color: #eef8fc;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .executive-summary h2 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        code {
            font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 0.9em;
            color: #e74c3c;
        }
        pre {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
    </style>
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        // Add click listeners to sheet headers
        var sheetHeaders = document.querySelectorAll('.sheet-header');
        
        sheetHeaders.forEach(function(header) {
            header.addEventListener('click', function() {
                // Toggle active class
                this.classList.toggle('active');
                
                // Toggle content visibility
                var content = this.nextElementSibling;
                if (content.style.maxHeight) {
                    content.style.maxHeight = null;
                } else {
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });
        });
    });
    </script>
</head>
<body>
    <h1>Test Suite Analysis Report</h1>
    
    <div class="report-meta">
        <p>Generated on: """ + timestamp + """</p>
        <p>Total Test Cases: """ + str(test_case_count) + """</p>
    </div>
    """
    
    # Add executive summary section if available
    if test_suite_analysis and 'executive_summary' in test_suite_analysis:
        executive_summary_html = _markdown_to_html(test_suite_analysis['executive_summary'])
        html += """
    <div class="executive-summary">
        <h2>Executive Summary</h2>
        <div class="summary-container">
            """ + executive_summary_html + """
        </div>
    """
        
        # Add key areas tested if available
        if 'key_areas_tested' in test_suite_analysis and test_suite_analysis['key_areas_tested']:
            html += """
        <div class="key-areas">
            <h3>Key Areas Tested</h3>
            <ul>
"""
            for area in test_suite_analysis['key_areas_tested']:
                html += "                <li>" + area + "</li>\n"
            html += """
            </ul>
        </div>
"""
        
        # Add overall assessment if available
        if 'overall_assessment' in test_suite_analysis and test_suite_analysis['overall_assessment']:
            assessment_html = _markdown_to_html(test_suite_analysis['overall_assessment'])
            html += """
        <div class="summary-container">
            <h3>Overall Assessment</h3>
            """ + assessment_html + """
        </div>
"""
        
        # Add recommendations if available
        if 'recommendations' in test_suite_analysis and test_suite_analysis['recommendations']:
            html += """
        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
"""
            for rec in test_suite_analysis['recommendations']:
                html += "                <li>" + rec + "</li>\n"
            html += """
            </ul>
        </div>
"""
        
        html += """
    </div>
"""
    
    # Add sheet-by-sheet analysis (collapsible sections)
    html += """
    <h2>Test Cases by Sheet</h2>
"""
    
    # Group test cases by sheet name
    sheets = {}
    for summary in test_case_summaries:
        sheet_name = summary.get("sheet_name", "Unknown")
        if sheet_name not in sheets:
            sheets[sheet_name] = []
        sheets[sheet_name].append(summary)
    
    # Get sheet analysis from the suite analysis
    sheet_analyses = {}
    if 'sheets_analysis' in test_suite_analysis:
        for sheet in test_suite_analysis['sheets_analysis']:
            sheet_name = sheet.get('sheet_name')
            if sheet_name:
                sheet_analyses[sheet_name] = sheet
    
    # Create collapsible sections for each sheet
    for sheet_name, summaries in sheets.items():
        # Get sheet analysis if available
        sheet_analysis = sheet_analyses.get(sheet_name, {})
        focus_area = sheet_analysis.get('focus_area', 'Not specified')
        observations = sheet_analysis.get('observations', '')
        sheet_summary = sheet_analysis.get('summary', '')
        test_count = len(summaries)
        
        html += """
    <div class="sheet-container">
        <div class="sheet-header">
            <div>
                <h3>""" + sheet_name + """</h3>
                <div class="info">Focus: """ + focus_area + """ • Test Cases: """ + str(test_count) + """</div>
            </div>
            <span class="collapsible-button"></span>
        </div>
        <div class="sheet-content">
            <div class="sheet-summary">
                <h4>Sheet Summary</h4>
                <p>""" + sheet_summary + """</p>
"""
        if observations:
            html += """
                <h4>Observations</h4>
                <p>""" + observations + """</p>
"""
        html += """
            </div>
            <div class="test-cases">
"""
        
        # Add each test case in this sheet
        for summary in summaries:
            test_case_number = summary.get('test_case_number', 'Unknown')
            test_case_name = summary.get('test_case_name', 'Unknown')
            purpose = summary.get('purpose', 'Not provided')
            inputs = summary.get('inputs', 'Not provided')
            expected_results = summary.get('expected_results', 'Not provided')
            observations = summary.get('observations', '')
            comprehensive_summary = summary.get('comprehensive_summary', 'No summary available')
            
            html += """
                <div class="test-case">
                    <div class="test-case-header">
                        <div class="test-case-title">""" + test_case_name + """</div>
                        <div class="test-case-id">Case #""" + test_case_number + """</div>
                    </div>
                    
                    <div class="test-case-section">
                        <h4>Purpose</h4>
                        <p>""" + purpose + """</p>
                    </div>
                    
                    <div class="test-case-section">
                        <h4>Inputs</h4>
                        <p>""" + inputs + """</p>
                    </div>
                    
                    <div class="test-case-section">
                        <h4>Expected Results</h4>
                        <p>""" + expected_results + """</p>
                    </div>
"""
            if observations:
                html += """
                    <div class="test-case-section">
                        <h4>Observations</h4>
                        <p>""" + observations + """</p>
                    </div>
"""
            html += """
                    <div class="test-case-section">
                        <h4>Comprehensive Summary</h4>
                        <p>""" + comprehensive_summary + """</p>
                    </div>
                </div>
"""
        
        # Close the test cases and sheet content divs
        html += """
            </div>
        </div>
    </div>
"""
    
    # Close the HTML
    html += """
</body>
</html>
    """
    
    return html


def test_summary_json_to_html(
    json_file: str,
    output_file: Optional[str] = None
) -> str:
    """
    Convert a JSON test summary file to HTML report.

    Args:
        json_file (str): Path to the JSON test summary file
        output_file (str, optional): Path to save the HTML report. If None, uses the same name with .html extension.

    Returns:
        str: Path to the generated HTML file
    """
    try:
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Default output file if not provided
        if output_file is None:
            output_file = os.path.splitext(json_file)[0] + '.html'
        
        # Determine if this is a test suite analysis or individual test case summary
        if isinstance(data, dict) and 'executive_summary' in data and 'sheets_analysis' in data:
            # This is a test suite analysis file
            # We need test case summaries to generate the full report
            suite_dir = os.path.dirname(json_file)
            case_summary_files = [f for f in os.listdir(suite_dir) if f.endswith('.json') and f != os.path.basename(json_file)]
            
            # Load all individual test case summaries
            test_case_summaries = []
            for case_file in case_summary_files:
                try:
                    with open(os.path.join(suite_dir, case_file), 'r', encoding='utf-8') as f:
                        case_data = json.load(f)
                    # Check if this is a test case summary (has test_case_number)
                    if isinstance(case_data, dict) and 'test_case_number' in case_data:
                        test_case_summaries.append(case_data)
                except Exception as case_error:
                    logger.warning("Error loading test case summary %s: %s", case_file, str(case_error))
            
            return generate_test_summary_report(data, test_case_summaries, output_file)
        
        elif isinstance(data, dict) and 'test_case_number' in data:
            # This is an individual test case summary
            # Convert just this test case to HTML
            return generate_test_summary_report(
                test_suite_analysis={"executive_summary": "Individual test case report"},
                test_case_summaries=[data],
                output_file=output_file
            )
        
        else:
            # Unknown format
            logger.error("Unknown JSON format in %s", json_file)
            raise ValueError("Unknown JSON format in " + json_file)
    
    except Exception as e:
        logger.error("Error converting test summary JSON to HTML: %s", str(e))
        raise