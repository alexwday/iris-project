#!/usr/bin/env python3
"""
Script to convert markdown files to individual HTML files that are
formatted for clean pasting into Microsoft Word.

Special focus on:
1. Proper list formatting
2. Mathematical formulas
3. Tables
4. Special characters and symbols
"""

import os
import re
import glob
import markdown
from pathlib import Path

def convert_md_to_html(md_file, output_dir):
    """
    Convert a markdown file to an HTML file with proper formatting for Word.
    """
    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Pre-process markdown for better Word compatibility
    
    # Fix bullet points to ensure proper nesting in Word
    md_content = re.sub(r'^(\s*)-\s+', r'\1* ', md_content, flags=re.MULTILINE)
    
    # Fix tables by ensuring they have proper cell content
    md_content = re.sub(r'\|\s*-+\s*\|', '| |', md_content)
    
    # Replace math formulas with proper HTML
    # Look for patterns like ±10.4% and convert to HTML entities
    md_content = md_content.replace('±', '&plusmn;')
    
    # Convert markdown to HTML with extensions
    html = markdown.markdown(
        md_content,
        extensions=[
            'tables',             # Support for tables
            'fenced_code',        # Support for code blocks
            'def_list',           # Support for definition lists
            'attr_list',          # Support for attributes
            'md_in_html',         # Support for markdown in HTML
        ]
    )
    
    # Extract filename without extension and path
    base_name = os.path.basename(md_file).rsplit('.', 1)[0]
    output_file = os.path.join(output_dir, f"{base_name}.html")
    
    # Create complete HTML document with styles optimized for Word
    complete_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{base_name}</title>
    <style>
        /* Styles optimized for Word pasting */
        body {{
            font-family: 'Calibri', Arial, sans-serif;
            line-height: 1.5;
            margin: 20px;
            color: #333;
        }}
        h1 {{
            font-size: 24pt;
            margin-top: 24pt;
            margin-bottom: 6pt;
            font-weight: bold;
            color: #000;
        }}
        h2 {{
            font-size: 18pt;
            margin-top: 18pt;
            margin-bottom: 6pt;
            font-weight: bold;
            color: #000;
        }}
        h3 {{
            font-size: 14pt;
            margin-top: 14pt;
            margin-bottom: 4pt;
            font-weight: bold;
            color: #000;
        }}
        h4 {{
            font-size: 12pt;
            margin-top: 12pt;
            margin-bottom: 2pt;
            font-weight: bold;
            color: #000;
        }}
        p {{
            margin-top: 2pt;
            margin-bottom: 8pt;
        }}
        ul, ol {{
            margin-top: 0;
            margin-bottom: 10pt;
            padding-left: 30px;
        }}
        ul ul, ol ol, ul ol, ol ul {{
            margin-top: 0;
            margin-bottom: 0;
        }}
        li {{
            margin-bottom: 4pt;
        }}
        table {{
            border-collapse: collapse;
            margin: 10pt 0;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        code {{
            font-family: "Courier New", Courier, monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: "Courier New", Courier, monospace;
            font-size: 0.9em;
            margin: 10pt 0;
        }}
        strong {{
            font-weight: bold;
        }}
        em {{
            font-style: italic;
        }}
        blockquote {{
            margin: 10pt 0;
            padding: 10px 20px;
            border-left: 5px solid #f2f2f2;
            color: #555;
        }}
    </style>
</head>
<body>
    {html}
</body>
</html>
"""

    # Write HTML to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(complete_html)
    
    print(f"Converted {md_file} to {output_file}")
    return output_file

def create_combined_html(html_files, output_file):
    """
    Create a combined HTML file from multiple HTML files.
    """
    combined_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined Model Documentation</title>
    <style>
        /* Styles optimized for Word pasting */
        body {
            font-family: 'Calibri', Arial, sans-serif;
            line-height: 1.5;
            margin: 20px;
            color: #333;
        }
        h1 {
            font-size: 24pt;
            margin-top: 24pt;
            margin-bottom: 6pt;
            font-weight: bold;
            color: #000;
        }
        h2 {
            font-size: 18pt;
            margin-top: 18pt;
            margin-bottom: 6pt;
            font-weight: bold;
            color: #000;
        }
        h3 {
            font-size: 14pt;
            margin-top: 14pt;
            margin-bottom: 4pt;
            font-weight: bold;
            color: #000;
        }
        h4 {
            font-size: 12pt;
            margin-top: 12pt;
            margin-bottom: 2pt;
            font-weight: bold;
            color: #000;
        }
        p {
            margin-top: 2pt;
            margin-bottom: 8pt;
        }
        ul, ol {
            margin-top: 0;
            margin-bottom: 10pt;
            padding-left: 30px;
        }
        ul ul, ol ol, ul ol, ol ul {
            margin-top: 0;
            margin-bottom: 0;
        }
        li {
            margin-bottom: 4pt;
        }
        table {
            border-collapse: collapse;
            margin: 10pt 0;
            width: 100%;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        code {
            font-family: "Courier New", Courier, monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: "Courier New", Courier, monospace;
            font-size: 0.9em;
            margin: 10pt 0;
        }
        strong {
            font-weight: bold;
        }
        em {
            font-style: italic;
        }
        blockquote {
            margin: 10pt 0;
            padding: 10px 20px;
            border-left: 5px solid #f2f2f2;
            color: #555;
        }
        .section-divider {
            border-top: 2px solid #ccc;
            margin: 30px 0;
        }
    </style>
</head>
<body>
"""

    for i, html_file in enumerate(html_files):
        # Read HTML content (extract just the body)
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            body_content = re.search(r'<body>(.*?)</body>', content, re.DOTALL)
            if body_content:
                body_html = body_content.group(1)
            else:
                continue
        
        # Add section divider (except for first section)
        if i > 0:
            combined_html += '<div class="section-divider"></div>\n'
        
        # Add content
        combined_html += body_html + "\n"
    
    combined_html += """
</body>
</html>
"""

    # Write combined HTML to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(combined_html)
    
    print(f"Created combined HTML file: {output_file}")
    return output_file

def main():
    input_dir = 'docs/model_documentation'
    output_dir = 'docs/model_documentation_html'
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all markdown files and sort by filename
    md_files = sorted(glob.glob(f"{input_dir}/*.md"))
    
    # Convert each file to HTML
    html_files = []
    for md_file in md_files:
        html_file = convert_md_to_html(md_file, output_dir)
        html_files.append(html_file)
    
    # Create combined HTML file
    combined_file = 'combined_model_documentation.html'
    create_combined_html(html_files, combined_file)
    
    print(f"\nConversion complete!")
    print(f"Individual HTML files are in: {output_dir}/")
    print(f"Combined HTML is at: {combined_file}")
    print("\nYou can open any of these HTML files in a browser, select all content,")
    print("and paste directly into a Word document for clean formatting.")

if __name__ == "__main__":
    main()