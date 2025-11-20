#!/usr/bin/env python3
"""
Script to compare two src folders and display differences in a screenshot-friendly format.
"""

import os
import difflib
import html
from pathlib import Path
import argparse
from typing import List, Tuple, Dict
import webbrowser
import tempfile


def get_all_files(directory: Path, base_path: Path) -> List[Path]:
    """Get all files in a directory recursively, returning relative paths."""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            # Skip common non-source files
            if filename.endswith(('.pyc', '.pyo', '__pycache__', '.DS_Store', '.git')):
                continue
            file_path = Path(root) / filename
            relative_path = file_path.relative_to(base_path)
            files.append(relative_path)
    return sorted(files)


def read_file_safely(file_path: Path) -> List[str]:
    """Read file and return lines, handling encoding errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.readlines()
        except:
            return [f"[Binary or unreadable file: {file_path}]\n"]
    except Exception as e:
        return [f"[Error reading file: {e}]\n"]


def create_diff_html(old_path: Path, new_path: Path) -> str:
    """Create an HTML report of differences between two directories."""
    old_files = set(get_all_files(old_path, old_path))
    new_files = set(get_all_files(new_path, new_path))
    
    all_files = sorted(old_files | new_files)
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Source Code Comparison</title>
        <style>
            body {
                font-family: 'Courier New', monospace;
                margin: 20px;
                background-color: #f5f5f5;
            }
            h1, h2, h3 {
                font-family: Arial, sans-serif;
            }
            .summary {
                background-color: #e0e0e0;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .file-section {
                background-color: white;
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                page-break-inside: avoid;
            }
            .file-header {
                background-color: #333;
                color: white;
                padding: 10px;
                margin: -20px -20px 15px -20px;
                border-radius: 5px 5px 0 0;
                font-weight: bold;
            }
            .new-file {
                background-color: #2e7d32;
            }
            .deleted-file {
                background-color: #c62828;
            }
            .modified-file {
                background-color: #1976d2;
            }
            .diff-container {
                overflow-x: auto;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            table.diff {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }
            td {
                padding: 3px 10px;
                vertical-align: top;
                white-space: pre;
                font-family: 'Courier New', monospace;
            }
            .linenum {
                width: 50px;
                text-align: right;
                color: #666;
                background-color: #f0f0f0;
                border-right: 1px solid #ddd;
            }
            .added {
                background-color: #dff0d8;
            }
            .removed {
                background-color: #f2dede;
            }
            .unchanged {
                background-color: #f9f9f9;
            }
            .nav {
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: white;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                max-width: 300px;
                max-height: 80vh;
                overflow-y: auto;
            }
            .nav h3 {
                margin-top: 0;
            }
            .nav ul {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            .nav li {
                margin: 5px 0;
            }
            .nav a {
                text-decoration: none;
                color: #333;
                display: block;
                padding: 3px 5px;
                border-radius: 3px;
            }
            .nav a:hover {
                background-color: #f0f0f0;
            }
            .nav .new { color: #2e7d32; }
            .nav .deleted { color: #c62828; }
            .nav .modified { color: #1976d2; }
            @media print {
                .nav { display: none; }
            }
        </style>
    </head>
    <body>
    """
    
    # Add summary
    only_in_old = old_files - new_files
    only_in_new = new_files - old_files
    common_files = old_files & new_files
    
    modified_files = []
    for file in common_files:
        old_content = read_file_safely(old_path / file)
        new_content = read_file_safely(new_path / file)
        if old_content != new_content:
            modified_files.append(file)
    
    html_content += f"""
    <h1>Source Code Comparison Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Original path:</strong> {old_path}</p>
        <p><strong>Modified path:</strong> {new_path}</p>
        <p><strong>Files only in original:</strong> {len(only_in_old)}</p>
        <p><strong>Files only in modified:</strong> {len(only_in_new)}</p>
        <p><strong>Modified files:</strong> {len(modified_files)}</p>
        <p><strong>Unchanged files:</strong> {len(common_files) - len(modified_files)}</p>
    </div>
    """
    
    # Add navigation
    html_content += """
    <div class="nav">
        <h3>Navigation</h3>
        <ul>
    """
    
    nav_items = []
    
    # Process deleted files
    if only_in_old:
        nav_items.append('<li><strong>Deleted Files:</strong></li>')
        for file in sorted(only_in_old):
            file_id = str(file).replace('/', '_').replace('.', '_')
            nav_items.append(f'<li>&nbsp;&nbsp;<a href="#{file_id}" class="deleted">- {file}</a></li>')
    
    # Process new files
    if only_in_new:
        nav_items.append('<li><strong>New Files:</strong></li>')
        for file in sorted(only_in_new):
            file_id = str(file).replace('/', '_').replace('.', '_')
            nav_items.append(f'<li>&nbsp;&nbsp;<a href="#{file_id}" class="new">+ {file}</a></li>')
    
    # Process modified files
    if modified_files:
        nav_items.append('<li><strong>Modified Files:</strong></li>')
        for file in sorted(modified_files):
            file_id = str(file).replace('/', '_').replace('.', '_')
            nav_items.append(f'<li>&nbsp;&nbsp;<a href="#{file_id}" class="modified">± {file}</a></li>')
    
    html_content += '\n'.join(nav_items)
    html_content += """
        </ul>
    </div>
    """
    
    # Process deleted files
    if only_in_old:
        html_content += "<h2>Files Only in Original (Deleted)</h2>"
        for file in sorted(only_in_old):
            file_id = str(file).replace('/', '_').replace('.', '_')
            html_content += f'''
            <div class="file-section" id="{file_id}">
                <div class="file-header deleted-file">DELETED: {file}</div>
                <div class="diff-container">
                    <table class="diff">
            '''
            content = read_file_safely(old_path / file)
            for i, line in enumerate(content, 1):
                escaped_line = html.escape(line.rstrip())
                html_content += f'''
                    <tr>
                        <td class="linenum">{i}</td>
                        <td class="removed">- {escaped_line}</td>
                    </tr>
                '''
            html_content += '''
                    </table>
                </div>
            </div>
            '''
    
    # Process new files
    if only_in_new:
        html_content += "<h2>Files Only in Modified (New)</h2>"
        for file in sorted(only_in_new):
            file_id = str(file).replace('/', '_').replace('.', '_')
            html_content += f'''
            <div class="file-section" id="{file_id}">
                <div class="file-header new-file">NEW: {file}</div>
                <div class="diff-container">
                    <table class="diff">
            '''
            content = read_file_safely(new_path / file)
            for i, line in enumerate(content, 1):
                escaped_line = html.escape(line.rstrip())
                html_content += f'''
                    <tr>
                        <td class="linenum">{i}</td>
                        <td class="added">+ {escaped_line}</td>
                    </tr>
                '''
            html_content += '''
                    </table>
                </div>
            </div>
            '''
    
    # Process modified files
    if modified_files:
        html_content += "<h2>Modified Files</h2>"
        for file in sorted(modified_files):
            file_id = str(file).replace('/', '_').replace('.', '_')
            old_content = read_file_safely(old_path / file)
            new_content = read_file_safely(new_path / file)
            
            html_content += f'''
            <div class="file-section" id="{file_id}">
                <div class="file-header modified-file">MODIFIED: {file}</div>
                <div class="diff-container">
                    <table class="diff">
            '''
            
            # Generate unified diff
            diff = difflib.unified_diff(
                old_content,
                new_content,
                fromfile=f"original/{file}",
                tofile=f"modified/{file}",
                lineterm='',
                n=3
            )
            
            # Convert to side-by-side format for better screenshots
            old_lines = []
            new_lines = []
            for line in diff:
                if line.startswith('---') or line.startswith('+++'):
                    continue
                elif line.startswith('@@'):
                    # Parse line numbers
                    html_content += f'''
                    <tr>
                        <td colspan="2" style="text-align: center; background-color: #e0e0e0; font-weight: bold;">{html.escape(line)}</td>
                    </tr>
                    '''
                elif line.startswith('-'):
                    html_content += f'''
                    <tr>
                        <td class="linenum"></td>
                        <td class="removed">- {html.escape(line[1:].rstrip())}</td>
                    </tr>
                    '''
                elif line.startswith('+'):
                    html_content += f'''
                    <tr>
                        <td class="linenum"></td>
                        <td class="added">+ {html.escape(line[1:].rstrip())}</td>
                    </tr>
                    '''
                else:
                    html_content += f'''
                    <tr>
                        <td class="linenum"></td>
                        <td class="unchanged">  {html.escape(line[1:].rstrip())}</td>
                    </tr>
                    '''
            
            html_content += '''
                    </table>
                </div>
            </div>
            '''
    
    html_content += """
    </body>
    </html>
    """
    
    return html_content


def main():
    parser = argparse.ArgumentParser(description='Compare two source directories and generate HTML report')
    parser.add_argument('old_src', help='Path to the original src folder')
    parser.add_argument('new_src', help='Path to the modified src folder')
    parser.add_argument('-o', '--output', default=None, help='Output HTML file (default: opens in browser)')
    
    args = parser.parse_args()
    
    old_path = Path(args.old_src).resolve()
    new_path = Path(args.new_src).resolve()
    
    if not old_path.exists():
        print(f"Error: Original path does not exist: {old_path}")
        return 1
    
    if not new_path.exists():
        print(f"Error: Modified path does not exist: {new_path}")
        return 1
    
    print(f"Comparing:\n  Original: {old_path}\n  Modified: {new_path}")
    
    html_content = create_diff_html(old_path, new_path)
    
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nReport saved to: {output_path}")
        print(f"Open the file in a web browser to view the differences.")
    else:
        # Create temporary file and open in browser
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name
        
        print(f"\nOpening report in web browser...")
        webbrowser.open(f'file://{temp_path}')
        print(f"\nTemporary report saved to: {temp_path}")
        print("The report will remain available until you delete the temporary file.")
    
    return 0


if __name__ == '__main__':
    exit(main())