"""
HTML Output Generator

This module converts evaluation results to HTML format for easy viewing.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

# Get module logger
logger = logging.getLogger(__name__)


def generate_html_report(
    summary: Dict[str, Any],
    evaluations: List[Dict[str, Any]],
    output_file: str
) -> str:
    """
    Generate an HTML report from evaluation summary and individual evaluations.

    Args:
        summary (dict): The aggregated summary of evaluations
        evaluations (list): List of individual evaluations
        output_file (str): Path to save the HTML report

    Returns:
        str: Path to the generated HTML file
    """
    logger.info(f"Generating HTML report: {output_file}")
    
    html_content = _generate_html_content(summary, evaluations)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write HTML to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error saving HTML report: {str(e)}")
        raise


def _markdown_to_html(markdown_text):
    """
    Convert markdown text to HTML.
    This is a simple conversion for headings, lists, and basic formatting.
    """
    if not markdown_text:
        return ""
    
    # Handle code blocks (```code```) - protect them from other processing
    code_blocks = []
    def replace_code_block(match):
        code_blocks.append(match.group(1))
        return f"CODE_BLOCK_{len(code_blocks)-1}"
    
    html = re.sub(r'```(.*?)```', replace_code_block, markdown_text, flags=re.DOTALL)
    
    # Convert headers (# Header -> <h1>Header</h1>, etc.)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # Convert unordered lists - improved to handle multiple separate lists properly
    # Find all continuous blocks of list items
    list_blocks = re.finditer(r'(?:^- .*?$\n?)+', html, flags=re.MULTILINE)
    
    for block in list_blocks:
        block_text = block.group(0)
        list_items = re.findall(r'^- (.*?)$', block_text, flags=re.MULTILINE)
        
        if list_items:
            html_list = '<ul>\n'
            for item in list_items:
                html_list += f'  <li>{item}</li>\n'
            html_list += '</ul>'
            # Replace this specific block with its HTML equivalent
            html = html.replace(block_text, html_list)
    
    # Convert ordered lists - improved to handle multiple separate lists properly
    ordered_list_pattern = r'^(\d+)\. (.*?)$'
    ol_sections = re.finditer(r'(?:^\d+\. .*?$\n?)+', html, flags=re.MULTILINE)
    
    # Process each ordered list block separately
    for section in ol_sections:
        section_text = section.group(0)
        items = re.findall(ordered_list_pattern, section_text, flags=re.MULTILINE)
        
        if items:
            html_list = '<ol>\n'
            for _, item in items:
                html_list += f'  <li>{item}</li>\n'
            html_list += '</ol>'
            
            # Replace only this specific block
            html = html.replace(section_text, html_list)
    
    # Handle **bold** sections with proper HTML
    # We need a more specific pattern to avoid conflicts with list items and other markdown
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Convert italic (*text* -> <em>text</em>)
    # Be cautious with asterisks that might be part of lists
    html = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', html)
    
    # Convert paragraphs (blank lines separate paragraphs)
    paragraphs = html.split('\n\n')
    html = ''
    for p in paragraphs:
        if not p.strip():
            continue
        if not (p.startswith('<h') or p.startswith('<ul') or p.startswith('<ol')):
            html += f'<p>{p}</p>\n'
        else:
            html += p + '\n'
    
    # Convert tables
    if '|' in markdown_text:
        table_sections = re.finditer(r'((?:^\|.*\|$\n)+)', markdown_text, flags=re.MULTILINE)
        for section in table_sections:
            table_text = section.group(0)
            rows = table_text.strip().split('\n')
            html_table = '<table class="md-table">\n'
            
            for i, row in enumerate(rows):
                if not row.strip():
                    continue
                
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                if i == 0:  # Header row
                    html_table += '  <thead>\n    <tr>\n'
                    for cell in cells:
                        html_table += f'      <th>{cell}</th>\n'
                    html_table += '    </tr>\n  </thead>\n  <tbody>\n'
                elif i == 1 and all(c.strip().startswith('-') for c in cells):
                    # Skip the separator row
                    continue
                else:  # Data rows
                    html_table += '    <tr>\n'
                    for cell in cells:
                        html_table += f'      <td>{cell}</td>\n'
                    html_table += '    </tr>\n'
            
            html_table += '  </tbody>\n</table>\n'
            html = html.replace(table_text, html_table)
    
    # Restore code blocks
    for i, code in enumerate(code_blocks):
        html = html.replace(f"CODE_BLOCK_{i}", f'<pre><code>{code}</code></pre>')
    
    # Add more specific styling for key sections - use regex for more flexible matching
    html = re.sub(r'<strong>\s*Key\s+Strengths:\s*</strong>', '<strong class="key-section strengths">Key Strengths:</strong>', html)
    html = re.sub(r'<strong>\s*Areas\s+for\s+Improvement:\s*</strong>', '<strong class="key-section improvements">Areas for Improvement:</strong>', html)
    
    return html


def _generate_html_content(
    summary: Dict[str, Any],
    evaluations: List[Dict[str, Any]]
) -> str:
    """
    Generate the HTML content from the summary and evaluations.

    Args:
        summary (dict): The aggregated summary
        evaluations (list): List of individual evaluations

    Returns:
        str: HTML content as a string
    """
    # Start with HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IRIS Test Evaluation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3, h4 {{
            color: #2c3e50;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        .report-meta {{
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .summary-container {{
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 30px;
            line-height: 1.6;
            font-size: 1.05em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .metric-header {{
            background-color: #e8f4f8;
            padding: 5px 10px;
            margin-top: 25px;
            border-radius: 3px;
        }}
        .evaluation-card {{
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 20px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .score-container {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        .score-box {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 5px;
            padding: 10px;
            margin: 5px;
            flex: 1;
            min-width: 150px;
            text-align: center;
        }}
        .score-value {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2980b9;
        }}
        .score-label {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .high-score {{
            background-color: #d4edda;
        }}
        .medium-score {{
            background-color: #fff3cd;
        }}
        .low-score {{
            background-color: #f8d7da;
        }}
        .comments {{
            font-style: italic;
            margin: 10px 0;
            padding-left: 10px;
            border-left: 3px solid #ddd;
        }}
        .md-table {{
            width: 100%;
            margin: 20px 0;
        }}
        .md-table th {{
            background-color: #eef1f5;
        }}
        .collapsible {{
            background-color: #f1f1f1;
            color: #444;
            cursor: pointer;
            padding: 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .active, .collapsible:hover {{
            background-color: #e1e6f0;
        }}
        .collapsible-content {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            flex: 1;
        }}
        .collapsible-title {{
            font-weight: bold;
            color: #2c3e50;
        }}
        .collapsible-question {{
            font-style: italic;
            color: #555;
            margin: 5px 0;
            max-width: 80%;
        }}
        .collapsible-score {{
            font-size: 0.9em;
            color: #666;
        }}
        .content {{
            padding: 0 18px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
            background-color: #fafbfc;
            border-radius: 0 0 5px 5px;
            margin-bottom: 20px;
        }}
        .collapsible-indicators {{
            display: flex;
            gap: 10px;
        }}
        .indicator {{
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: inline-block;
        }}
        .indicator-green {{
            background-color: #28a745;
        }}
        .indicator-yellow {{
            background-color: #ffc107;
        }}
        .indicator-red {{
            background-color: #dc3545;
        }}
        .indicator-none {{
            background-color: #6c757d;
        }}
        .executive-summary-score-container {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 20px 0;
            background-color: #eef8fc;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .executive-score-box {{
            background-color: white;
            border-radius: 10px;
            padding: 15px;
            margin: 10px;
            min-width: 180px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }}
        .executive-score-value {{
            font-size: 2em;
            font-weight: bold;
            color: #0056b3;
        }}
        .executive-text-summary {{
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .executive-text-summary h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .key-section {{
            display: block;
            margin-top: 15px;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .key-section.strengths {{
            color: #28a745;
        }}
        .key-section.improvements {{
            color: #dc3545;
            margin-top: 20px;
        }}
    </style>
    <script>
        window.onload = function() {{
            var coll = document.getElementsByClassName("collapsible");
            for (var i = 0; i < coll.length; i++) {{
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
        }}
    </script>
</head>
<body>
    <h1>IRIS Test Evaluation Report</h1>
    
    <div class="report-meta">
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Evaluations: {len(evaluations)}</p>
    </div>
    """
    
    # Extract average scores from evaluations for executive summary
    overall_pct_scores = []
    db_pct_scores = []
    doc_pct_scores = []
    answer_pct_scores = []
    
    for eval_data in evaluations:
        if not eval_data:
            continue
        
        percentage_scores = eval_data.get('percentage_score', {})
        
        if percentage_scores.get('overall_pct') is not None:
            overall_pct_scores.append(percentage_scores.get('overall_pct'))
        if percentage_scores.get('database_selection_pct') is not None:
            db_pct_scores.append(percentage_scores.get('database_selection_pct'))
        if percentage_scores.get('document_selection_pct') is not None:
            doc_pct_scores.append(percentage_scores.get('document_selection_pct'))
        if percentage_scores.get('answer_accuracy_pct') is not None:
            answer_pct_scores.append(percentage_scores.get('answer_accuracy_pct'))
    
    # Calculate averages if we have scores
    avg_overall = round(sum(overall_pct_scores) / len(overall_pct_scores), 1) if overall_pct_scores else None
    avg_db = round(sum(db_pct_scores) / len(db_pct_scores), 1) if db_pct_scores else None
    avg_doc = round(sum(doc_pct_scores) / len(doc_pct_scores), 1) if doc_pct_scores else None
    avg_answer = round(sum(answer_pct_scores) / len(answer_pct_scores), 1) if answer_pct_scores else None
    
    # Color function for percentage scores
    def get_score_class(score):
        if score is None:
            return ""
        if score >= 80:
            return "high-score"
        elif score >= 60:
            return "medium-score"
        else:
            return "low-score"
    
    # Add executive summary section if available
    if summary and 'summary' in summary:
        html += f"""
    <h2>Executive Summary</h2>
    
    <div class="executive-summary-score-container">
        <div class="executive-score-box {get_score_class(avg_overall)}">
            <div class="executive-score-value">{avg_overall if avg_overall is not None else 'N/A'}%</div>
            <div class="score-label">Overall Score</div>
        </div>
        <div class="executive-score-box {get_score_class(avg_db)}">
            <div class="executive-score-value">{avg_db if avg_db is not None else 'N/A'}%</div>
            <div class="score-label">Database Selection</div>
        </div>
        <div class="executive-score-box {get_score_class(avg_doc)}">
            <div class="executive-score-value">{avg_doc if avg_doc is not None else 'N/A'}%</div>
            <div class="score-label">Document Selection</div>
        </div>
        <div class="executive-score-box {get_score_class(avg_answer)}">
            <div class="executive-score-value">{avg_answer if avg_answer is not None else 'N/A'}%</div>
            <div class="score-label">Answer Accuracy</div>
        </div>
    </div>
    
    <div class="executive-text-summary">
        <h3>Executive Summary</h3>
        <div class="summary-container">
            {_markdown_to_html(summary['summary'])}
        </div>
    </div>
    """
    
    # Add detailed evaluations section with collapsible items
    html += """
    <h2>Individual Test Evaluations</h2>
    """
    
    # Add each evaluation as a collapsible section
    for idx, eval_data in enumerate(evaluations):
        if not eval_data:
            continue
            
        # Handle file and sheet information
        file_info = eval_data.get('file', f'Test {idx+1}')
        sheet_info = eval_data.get('sheet', '')
        title = f"{file_info}" + (f" - Sheet: {sheet_info}" if sheet_info else "")
        
        # Extract relevant scores for indicators
        percentage_scores = eval_data.get('percentage_score', {})
        overall_pct = percentage_scores.get('overall_pct')
        db_pct = percentage_scores.get('database_selection_pct')
        doc_pct = percentage_scores.get('document_selection_pct')
        answer_pct = percentage_scores.get('answer_accuracy_pct')
        
        # Determine indicators based on scores
        def get_indicator_class(score):
            if score is None:
                return "indicator-none"
            if score >= 80:
                return "indicator-green"
            elif score >= 60:
                return "indicator-yellow"
            else:
                return "indicator-red"
        
        # Format overall percentage score
        overall_display = f"{overall_pct}%" if overall_pct is not None else "N/A"
        
        # Get the question if available
        question = eval_data.get('question', 'Question not found')
        
        # Format file name for display (extract from path if needed)
        if isinstance(file_info, str) and '/' in file_info:
            # Extract just the file name without path
            display_file = os.path.basename(file_info)
        else:
            display_file = file_info
            
        # Create collapsible button with indicators
        html += f"""
    <button class="collapsible">
        <div class="collapsible-content">
            <div class="collapsible-title">{display_file}{' - ' + sheet_info if sheet_info else ''}</div>
            <div class="collapsible-question">{question}</div>
            <div class="collapsible-score">Overall Score: {overall_display}</div>
        </div>
        <div class="collapsible-indicators">
            <span class="indicator {get_indicator_class(db_pct)}" title="Database Selection"></span>
            <span class="indicator {get_indicator_class(doc_pct)}" title="Document Selection"></span>
            <span class="indicator {get_indicator_class(answer_pct)}" title="Answer Accuracy"></span>
        </div>
    </button>
    <div class="content">
        <div class="evaluation-card">
            <div class="score-container">
                <div class="score-box {get_score_class(overall_pct)}">
                    <div class="score-value">{overall_pct if overall_pct is not None else 'N/A'}%</div>
                    <div class="score-label">Overall</div>
                </div>
                <div class="score-box {get_score_class(db_pct)}">
                    <div class="score-value">{db_pct if db_pct is not None else 'N/A'}%</div>
                    <div class="score-label">Database Selection</div>
                </div>
                <div class="score-box {get_score_class(doc_pct)}">
                    <div class="score-value">{doc_pct if doc_pct is not None else 'N/A'}%</div>
                    <div class="score-label">Document Selection</div>
                </div>
                <div class="score-box {get_score_class(answer_pct)}">
                    <div class="score-value">{answer_pct if answer_pct is not None else 'N/A'}%</div>
                    <div class="score-label">Answer Accuracy</div>
                </div>
    """
        
        # Add reviewer score if available
        reviewer_score = eval_data.get('reviewer_overall_score', {})
        score_value = reviewer_score.get('score')
        max_score = reviewer_score.get('max_score', 5)
        
        if score_value is not None:
            # Format score display
            score_display = f"{score_value}/{max_score}"
            reviewer_pct = (score_value / max_score) * 100 if max_score else 0
            
            html += f"""
                <div class="score-box {get_score_class(reviewer_pct)}">
                    <div class="score-value">{score_display}</div>
                    <div class="score-label">Reviewer Score</div>
                </div>
    """
        
        # Close the score container and add details
        html += f"""
            </div>
            
            <div class="question-container">
                <h4 class="metric-header">Question</h4>
                <div class="question-text">{question}</div>
            </div>
            
            <h4 class="metric-header">Database Selection</h4>
            <p><strong>Correct:</strong> {eval_data.get('database_selection', {}).get('correct')}</p>
            <div class="comments">{eval_data.get('database_selection', {}).get('comments', 'No comments provided')}</div>
            
            <h4 class="metric-header">Document Selection</h4>
            <p><strong>Correct:</strong> {eval_data.get('document_selection', {}).get('correct')}</p>
            <div class="comments">{eval_data.get('document_selection', {}).get('comments', 'No comments provided')}</div>
            
            <h4 class="metric-header">Answer Accuracy</h4>
            <p><strong>Score:</strong> {eval_data.get('answer_accuracy', {}).get('score')}</p>
            <div class="comments">{eval_data.get('answer_accuracy', {}).get('comments', 'No comments provided')}</div>
            
            <h4 class="metric-header">Overall Assessment</h4>
            <div class="comments">{eval_data.get('overall_assessment', 'No assessment provided')}</div>
        </div>
    </div>
    """
    
    # Close the HTML
    html += """
</body>
</html>
    """
    
    return html


def json_to_html(
    json_file: str,
    output_file: Optional[str] = None
) -> str:
    """
    Convert a JSON evaluation file to HTML report.

    Args:
        json_file (str): Path to the JSON evaluation file
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
        
        # Determine if this is a summary file or individual evaluation
        if isinstance(data, dict) and 'summary' in data:
            # This is a summary file with content
            return generate_html_report(data, [], output_file)
        elif isinstance(data, dict) and 'results_by_sheet' in data:
            # This is a file with results by sheet
            evaluations = list(data['results_by_sheet'].values())
            return generate_html_report({'summary': 'Individual file evaluation'}, evaluations, output_file)
        else:
            # This is an individual evaluation
            return generate_html_report({'summary': 'Individual evaluation'}, [data], output_file)
    
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {str(e)}")
        raise