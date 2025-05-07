#!/usr/bin/env python3
"""
Script to combine markdown documentation files into HTML
that can be easily pasted into Microsoft Word.

This script:
1. Reads all numbered markdown files in the docs/model_documentation directory
2. Sorts them by number prefix
3. Converts markdown to HTML suitable for Word
4. Combines them into a single HTML file
"""

import os
import re
import glob
import markdown

def convert_markdown_to_html(text):
    """
    Convert markdown content to HTML for clean pasting into Word.
    """
    # Pre-process markdown to handle some special cases
    
    # Ensure tables have empty cells instead of ----- or empty values
    text = re.sub(r'\|\s*-----+\s*\|', '| |', text)
    text = re.sub(r'\|\s*\|', '| |', text)
    
    # Convert markdown to HTML using the Python Markdown library
    html = markdown.markdown(text, extensions=['tables', 'fenced_code'])
    
    return html

def main():
    # Directory containing markdown files
    doc_dir = "docs/model_documentation"
    
    # Get all markdown files
    files = glob.glob(f"{doc_dir}/*.md")
    
    # Extract numbers and sort files by number
    numbered_files = []
    for file in files:
        basename = os.path.basename(file)
        match = re.match(r'(\d+)_', basename)
        if match:
            number = int(match.group(1))
            numbered_files.append((number, file))
    
    numbered_files.sort()
    
    # Start with HTML header
    html_output = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Model Documentation</title>
    <style>
        body {
            font-family: Calibri, Arial, sans-serif;
            line-height: 1.5;
            margin: 2em;
        }
        h1 {
            font-size: 24pt;
            color: #333;
            margin-top: 1.5em;
        }
        h2 {
            font-size: 18pt;
            color: #333;
            margin-top: 1.2em;
        }
        h3 {
            font-size: 14pt;
            color: #333;
            margin-top: 1em;
        }
        p {
            margin-bottom: 0.8em;
        }
        ul, ol {
            margin-bottom: 1em;
        }
        li {
            margin-bottom: 0.5em;
        }
        table {
            border-collapse: collapse;
            margin: 1em 0;
            width: 100%;
        }
        th, td {
            padding: 8px;
            border: 1px solid #ccc;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        .section-divider {
            border-top: 1px solid #ccc;
            margin: 2em 0;
        }
    </style>
</head>
<body>
"""
    
    # Process each file
    for i, (_, file_path) in enumerate(numbered_files):
        with open(file_path, 'r') as file:
            content = file.read()
            
            # Add section divider between documents except for first one
            if i > 0:
                html_output += '<div class="section-divider"></div>\n'
                
            # Convert markdown to HTML
            html_content = convert_markdown_to_html(content)
            
            # Add to combined HTML
            html_output += html_content + "\n"
    
    # Close HTML tags
    html_output += """
</body>
</html>
"""
    
    # Write to output file
    output_path = "combined_model_documentation.html"
    with open(output_path, 'w') as outfile:
        outfile.write(html_output)
    
    print(f"Combined HTML document written to {output_path}")
    print("You can now open this file in a browser and copy the content to paste into Word.")
    print("This HTML format should paste much more cleanly into Word with proper formatting.")

if __name__ == "__main__":
    main()