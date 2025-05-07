"""Generate HTML report from test case summaries."""

import os
import logging
from typing import Dict, List
import html

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2980b9;
            margin-top: 30px;
        }}
        h3 {{
            color: #3498db;
        }}
        .collapsible {{
            background-color: #f1f8ff;
            color: #0366d6;
            cursor: pointer;
            padding: 18px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 2px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .active, .collapsible:hover {{
            background-color: #ddeeff;
        }}
        .content {{
            padding: 0 18px;
            background-color: white;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
            border-left: 1px solid #eaecef;
            border-right: 1px solid #eaecef;
            border-bottom: 1px solid #eaecef;
            margin-bottom: 20px;
        }}
        .content-inner {{
            padding: 16px 0;
        }}
        .test-case {{
            margin-bottom: 20px;
            border-left: 4px solid #e1e4e8;
            padding-left: 16px;
        }}
        .test-case h4 {{
            margin-bottom: 5px;
            color: #24292e;
        }}
        .test-info {{
            color: #586069;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .summary {{
            background-color: #f6f8fa;
            padding: 16px;
            border-radius: 4px;
            margin-top: 20px;
            margin-bottom: 30px;
        }}
        .system-label {{
            display: inline-block;
            background-color: #0366d6;
            color: white;
            border-radius: 3px;
            padding: 2px 8px;
            font-size: 12px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        {file_summary}
    </div>
    
    <h2>System Summaries</h2>
    {system_summaries}
    
    <h2>Test Case Details</h2>
    {test_case_details}
    
    <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;
        
        for (i = 0; i < coll.length; i++) {{
            coll[i].addEventListener("click", function() {{
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.maxHeight) {{
                    content.style.maxHeight = null;
                }} else {{
                    content.style.maxHeight = content.scrollHeight + "px";
                }}
            }});
        }}
        
        // Expand the first level by default
        document.addEventListener('DOMContentLoaded', function() {{
            var systemSummaries = document.querySelectorAll('.system-summary-button');
            for (var i = 0; i < systemSummaries.length; i++) {{
                systemSummaries[i].click();
            }}
        }});
    </script>
</body>
</html>
"""


def generate_html_report(
    output_file_path: str,
    title: str,
    file_summary: str,
    system_summaries: Dict[str, str],
    system_test_cases: Dict[str, List[Dict]]
) -> None:
    """
    Generate an HTML report with expandable sections.
    
    Args:
        output_file_path: Path to save the HTML file
        title: Report title
        file_summary: Overall file-level summary
        system_summaries: Dictionary of system-level summaries
        system_test_cases: Dictionary of test cases organized by system
    """
    logger.info(f"Generating HTML report: {output_file_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    
    # Generate the system summaries section with collapsible buttons
    systems_html = ""
    for system_name, summary in system_summaries.items():
        safe_summary = html.escape(summary).replace('\n', '<br>')
        systems_html += f"""
        <button class="collapsible system-summary-button">{system_name} System Summary</button>
        <div class="content">
            <div class="content-inner">
                {safe_summary}
            </div>
        </div>
        """
    
    # Generate the test case details section with nested collapsible buttons
    test_cases_html = ""
    for system_name, test_cases in system_test_cases.items():
        test_cases_html += f"""
        <button class="collapsible">{system_name} Test Cases ({len(test_cases)})</button>
        <div class="content">
            <div class="content-inner">
        """
        
        for test_case in test_cases:
            test_number = test_case.get('test_number', 'N/A')
            test_case_name = html.escape(test_case['test_case_name'])
            summary = html.escape(test_case['summary']).replace('\n', '<br>')
            
            test_cases_html += f"""
            <div class="test-case">
                <h4>{test_case_name}</h4>
                <div class="test-info">
                    <span class="system-label">{system_name}</span>
                    Test Number: {test_number}
                </div>
                <div>{summary}</div>
            </div>
            """
        
        test_cases_html += """
            </div>
        </div>
        """
    
    # Format the file summary
    safe_file_summary = html.escape(file_summary).replace('\n', '<br>')
    
    # Fill the HTML template
    html_content = HTML_TEMPLATE.format(
        title=title,
        file_summary=safe_file_summary,
        system_summaries=systems_html,
        test_case_details=test_cases_html
    )
    
    # Write the HTML file
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"HTML report generated: {output_file_path}")