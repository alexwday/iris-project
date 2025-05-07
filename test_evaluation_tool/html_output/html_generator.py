"""
HTML Output Generator

This module converts evaluation results to HTML format for easy viewing.
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

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
    </style>
</head>
<body>
    <h1>IRIS Test Evaluation Report</h1>
    
    <div class="report-meta">
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Evaluations: {len(evaluations)}</p>
    </div>
    """
    
    # Add summary section if available
    if summary and 'summary' in summary:
        html += f"""
    <h2>Executive Summary</h2>
    <div class="summary-container">
        {summary['summary']}
    </div>
    """
    
    # Add detailed evaluations section
    html += """
    <h2>Individual Test Evaluations</h2>
    """
    
    # Add each evaluation
    for idx, eval_data in enumerate(evaluations):
        if not eval_data:
            continue
            
        # Handle file and sheet information
        file_info = eval_data.get('file', f'Test {idx+1}')
        sheet_info = eval_data.get('sheet', '')
        title = f"{file_info}" + (f" - Sheet: {sheet_info}" if sheet_info else "")
        
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
        
        # Extract relevant scores
        percentage_scores = eval_data.get('percentage_score', {})
        overall_pct = percentage_scores.get('overall_pct')
        db_pct = percentage_scores.get('database_selection_pct')
        doc_pct = percentage_scores.get('document_selection_pct')
        answer_pct = percentage_scores.get('answer_accuracy_pct')
        
        # Extract reviewer score
        reviewer_score = eval_data.get('reviewer_overall_score', {})
        score_value = reviewer_score.get('score')
        max_score = reviewer_score.get('max_score', 5)
        
        # Format score display
        score_display = f"{score_value}/{max_score}" if score_value is not None else "N/A"
        
        # Add evaluation card
        html += f"""
    <div class="evaluation-card">
        <h3>{title}</h3>
        
        <div class="score-container">
            <div class="score-box {get_score_class(overall_pct)}">
                <div class="score-value">{overall_pct}%</div>
                <div class="score-label">Overall</div>
            </div>
            <div class="score-box {get_score_class(db_pct)}">
                <div class="score-value">{db_pct}%</div>
                <div class="score-label">Database Selection</div>
            </div>
            <div class="score-box {get_score_class(doc_pct)}">
                <div class="score-value">{doc_pct}%</div>
                <div class="score-label">Document Selection</div>
            </div>
            <div class="score-box {get_score_class(answer_pct)}">
                <div class="score-value">{answer_pct}%</div>
                <div class="score-label">Answer Accuracy</div>
            </div>
            <div class="score-box">
                <div class="score-value">{score_display}</div>
                <div class="score-label">Reviewer Score</div>
            </div>
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
            # This is a summary file
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