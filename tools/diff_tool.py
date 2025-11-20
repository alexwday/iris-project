#!/usr/bin/env python3
"""
Diff Tool - Compare two directory trees and generate multiple output formats.

Usage:
    python diff_tool.py <dir1> <dir2> --output <output_prefix>

Example:
    python diff_tool.py /path/to/IT/iris/src /path/to/local/iris/src --output sync_report
"""

import os
import sys
import argparse
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime


class DiffTool:
    """Compare two directory trees and generate comprehensive diff reports."""

    def __init__(self, dir1: Path, dir2: Path):
        self.dir1 = Path(dir1).resolve()
        self.dir2 = Path(dir2).resolve()
        self.files_only_in_dir1: Set[str] = set()
        self.files_only_in_dir2: Set[str] = set()
        self.modified_files: Dict[str, Tuple[List[str], List[str]]] = {}
        self.identical_files: Set[str] = set()

    def scan_directory(self, directory: Path, base_path: Path) -> Dict[str, Path]:
        """Recursively scan directory and return relative paths to files."""
        files = {}
        for item in directory.rglob('*'):
            if item.is_file():
                # Skip common non-source files
                if self._should_skip(item):
                    continue
                rel_path = str(item.relative_to(base_path))
                files[rel_path] = item
        return files

    def _should_skip(self, path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__',
            '.pyc',
            '.git',
            '.DS_Store',
            '.egg-info',
            'node_modules',
            '.venv',
            'venv',
            '.pytest_cache',
            '.mypy_cache',
        ]
        path_str = str(path)
        return any(pattern in path_str for pattern in skip_patterns)

    def compare_directories(self):
        """Compare the two directories and categorize files."""
        print(f"Scanning {self.dir1}...")
        files1 = self.scan_directory(self.dir1, self.dir1)

        print(f"Scanning {self.dir2}...")
        files2 = self.scan_directory(self.dir2, self.dir2)

        all_files = set(files1.keys()) | set(files2.keys())

        print(f"\nComparing {len(all_files)} files...")

        for rel_path in sorted(all_files):
            if rel_path in files1 and rel_path in files2:
                # File exists in both - compare content
                content1 = self._read_file(files1[rel_path])
                content2 = self._read_file(files2[rel_path])

                if content1 == content2:
                    self.identical_files.add(rel_path)
                else:
                    self.modified_files[rel_path] = (content1, content2)
            elif rel_path in files1:
                self.files_only_in_dir1.add(rel_path)
            else:
                self.files_only_in_dir2.add(rel_path)

    def _read_file(self, path: Path) -> List[str]:
        """Read file and return lines."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except UnicodeDecodeError:
            # Binary file or non-UTF8
            return [f"<Binary file: {path.name}>\n"]

    def generate_unified_diff(self, output_path: Path):
        """Generate unified diff format (.patch file)."""
        print(f"\nGenerating unified diff: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Diff generated: {datetime.now()}\n")
            f.write(f"# Source 1: {self.dir1}\n")
            f.write(f"# Source 2: {self.dir2}\n\n")

            for rel_path in sorted(self.modified_files.keys()):
                content1, content2 = self.modified_files[rel_path]

                diff = difflib.unified_diff(
                    content1,
                    content2,
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm=''
                )

                f.write('\n'.join(diff))
                f.write('\n\n')

            # Document added/deleted files
            if self.files_only_in_dir1:
                f.write("\n# Files only in dir1 (deleted in dir2):\n")
                for path in sorted(self.files_only_in_dir1):
                    f.write(f"# - {path}\n")

            if self.files_only_in_dir2:
                f.write("\n# Files only in dir2 (added in dir2):\n")
                for path in sorted(self.files_only_in_dir2):
                    f.write(f"# + {path}\n")

    def generate_text_diff(self, output_path: Path):
        """Generate human-readable text diff."""
        print(f"Generating text diff: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DIFF REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Source 1 (IT/Modified): {self.dir1}\n")
            f.write(f"Source 2 (Reference):   {self.dir2}\n")
            f.write("=" * 80 + "\n\n")

            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Modified files:  {len(self.modified_files)}\n")
            f.write(f"Identical files: {len(self.identical_files)}\n")
            f.write(f"Only in dir1:    {len(self.files_only_in_dir1)}\n")
            f.write(f"Only in dir2:    {len(self.files_only_in_dir2)}\n")
            f.write("\n\n")

            # Modified files with diffs
            if self.modified_files:
                f.write("MODIFIED FILES\n")
                f.write("=" * 80 + "\n\n")

                for rel_path in sorted(self.modified_files.keys()):
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"FILE: {rel_path}\n")
                    f.write("=" * 80 + "\n\n")

                    content1, content2 = self.modified_files[rel_path]

                    diff = difflib.unified_diff(
                        content1,
                        content2,
                        fromfile="IT/Modified version",
                        tofile="Reference version",
                        lineterm=''
                    )

                    f.write('\n'.join(diff))
                    f.write('\n\n')

            # Files only in dir1
            if self.files_only_in_dir1:
                f.write("\n" + "=" * 80 + "\n")
                f.write("FILES ONLY IN DIR1 (Deleted in dir2)\n")
                f.write("=" * 80 + "\n")
                for path in sorted(self.files_only_in_dir1):
                    f.write(f"  - {path}\n")

            # Files only in dir2
            if self.files_only_in_dir2:
                f.write("\n" + "=" * 80 + "\n")
                f.write("FILES ONLY IN DIR2 (Added in dir2)\n")
                f.write("=" * 80 + "\n")
                for path in sorted(self.files_only_in_dir2):
                    f.write(f"  + {path}\n")

    def generate_html_diff(self, output_path: Path):
        """Generate clean HTML diff optimized for phone photography."""
        print(f"Generating HTML diff: {output_path}")

        html = []
        html.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Code Diff Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
            background: #1a1a1a;
            color: #e0e0e0;
        }
        .view {
            display: none;
        }
        .view.active {
            display: block;
        }

        /* File List */
        .file-list {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .list-header {
            background: #2d2d2d;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 5px solid #4CAF50;
        }
        .list-header h1 {
            font-size: 24px;
            color: #4CAF50;
            margin-bottom: 10px;
        }
        .stats {
            font-size: 14px;
            color: #aaa;
        }
        .file-item {
            background: #2d2d2d;
            padding: 15px 20px;
            margin-bottom: 10px;
            cursor: pointer;
            border-left: 4px solid #555;
            transition: all 0.2s;
        }
        .file-item:hover {
            background: #3d3d3d;
            border-left-color: #4CAF50;
        }
        .file-item.modified { border-left-color: #FF9800; }
        .file-item.added { border-left-color: #4CAF50; }
        .file-item.deleted { border-left-color: #f44336; }
        .file-name {
            font-size: 16px;
            font-weight: bold;
            color: #fff;
        }

        /* Diff View */
        .diff-view {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .diff-nav {
            background: #2d2d2d;
            padding: 15px 20px;
            border-bottom: 2px solid #444;
            flex-shrink: 0;
        }
        .diff-filename {
            font-size: 16px;
            color: #4CAF50;
            margin-bottom: 10px;
            font-weight: bold;
        }
        .nav-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 8px 16px;
            background: #4CAF50;
            color: #000;
            border: none;
            cursor: pointer;
            font-family: inherit;
            font-size: 13px;
            font-weight: bold;
        }
        .btn:hover {
            background: #45a049;
        }
        .btn-secondary {
            background: #555;
            color: #fff;
        }
        .btn-secondary:hover {
            background: #666;
        }

        /* Split View */
        .split-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            flex: 1;
            overflow: hidden;
        }
        .pane {
            overflow-y: auto;
            padding: 10px;
        }
        .pane-left {
            background: #1a1a1a;
            border-right: 2px solid #444;
        }
        .pane-right {
            background: #1a1a1a;
        }
        .pane-header {
            position: sticky;
            top: 0;
            padding: 10px;
            font-weight: bold;
            font-size: 14px;
            z-index: 10;
            margin-bottom: 10px;
        }
        .pane-left .pane-header {
            background: #8B0000;
            color: #fff;
        }
        .pane-right .pane-header {
            background: #006400;
            color: #fff;
        }

        /* Code Display */
        .code-container {
            font-size: 11px;
            line-height: 1.4;
        }
        .code-line {
            padding: 1px 5px;
            white-space: pre;
            font-family: inherit;
        }
        .pane-left .code-line {
            color: #e0e0e0;
        }
        .pane-right .code-line {
            color: #e0e0e0;
        }
        .code-line.highlight {
            background: rgba(255, 255, 0, 0.15);
            font-weight: bold;
        }
        .pane-left .code-line.highlight {
            background: rgba(255, 0, 0, 0.2);
        }
        .pane-right .code-line.highlight {
            background: rgba(0, 255, 0, 0.2);
        }
        .line-num {
            display: inline-block;
            width: 45px;
            color: #666;
            text-align: right;
            margin-right: 10px;
            user-select: none;
        }
    </style>
</head>
<body>
    <div id="listView" class="view active">
        <div class="file-list">
            <div class="list-header">
                <h1>Code Diff Report</h1>
                <div class="stats">
                    Modified: """ + str(len(self.modified_files)) + """ | Added: """ + str(len(self.files_only_in_dir2)) + """ | Deleted: """ + str(len(self.files_only_in_dir1)) + """
                </div>
            </div>
            <h3 style="color: #FF9800; margin: 20px 0 10px 0; font-size: 14px;">MODIFIED FILES - Click to view</h3>""")

        # Modified files
        file_list = sorted(self.modified_files.keys())
        for idx, rel_path in enumerate(file_list):
            html.append(f"""
            <div class="file-item modified" onclick="showFile({idx})">
                <div class="file-name">{rel_path}</div>
            </div>""")

        # Added files
        if self.files_only_in_dir2:
            html.append('<h3 style="color: #4CAF50; margin: 20px 0 10px 0; font-size: 14px;">NEW FILES</h3>')
            for path in sorted(self.files_only_in_dir2):
                html.append(f"""
            <div class="file-item added">
                <div class="file-name">{path} (NEW - needs to be created)</div>
            </div>""")

        # Deleted files
        if self.files_only_in_dir1:
            html.append('<h3 style="color: #f44336; margin: 20px 0 10px 0; font-size: 14px;">DELETED FILES</h3>')
            for path in sorted(self.files_only_in_dir1):
                html.append(f"""
            <div class="file-item deleted">
                <div class="file-name">{path} (DELETE this file)</div>
            </div>""")

        html.append("""
        </div>
    </div>""")

        # Generate individual file diff views
        for idx, rel_path in enumerate(file_list):
            content1, content2 = self.modified_files[rel_path]

            html.append(f"""
    <div id="diffView{idx}" class="view diff-view">
        <div class="diff-nav">
            <div class="diff-filename">FILE {idx + 1} of {len(file_list)}: {rel_path}</div>
            <div class="nav-buttons">
                <button class="btn btn-secondary" onclick="showList()">← Back to List</button>""")

            if idx > 0:
                html.append(f"""
                <button class="btn" onclick="showFile({idx - 1})">↑ Previous</button>""")
            if idx < len(file_list) - 1:
                html.append(f"""
                <button class="btn" onclick="showFile({idx + 1})">↓ Next</button>""")

            html.append(f"""
                <span class="btn-secondary" style="padding: 8px 16px;">{idx + 1}/{len(file_list)}</span>
            </div>
        </div>
        <div class="split-container">
            <div class="pane pane-left">
                <div class="pane-header">CURRENT CODE (will be replaced)</div>
                <div class="code-container">""")

            # Left side - current code
            for line_num, line in enumerate(content1, 1):
                is_diff = (line_num - 1 >= len(content2) or line != content2[line_num - 1])
                css_class = " highlight" if is_diff else ""
                html.append(f'<div class="code-line{css_class}"><span class="line-num">{line_num}</span>{self._html_escape(line.rstrip())}</div>')

            html.append("""
                </div>
            </div>
            <div class="pane pane-right">
                <div class="pane-header">IT MODIFIED CODE (copy this)</div>
                <div class="code-container">""")

            # Right side - IT code
            for line_num, line in enumerate(content2, 1):
                is_diff = (line_num - 1 >= len(content1) or line != content1[line_num - 1])
                css_class = " highlight" if is_diff else ""
                html.append(f'<div class="code-line{css_class}"><span class="line-num">{line_num}</span>{self._html_escape(line.rstrip())}</div>')

            html.append("""
                </div>
            </div>
        </div>
    </div>""")

        # JavaScript
        html.append(f"""
    <script>
        function showList() {{
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('listView').classList.add('active');
        }}
        function showFile(idx) {{
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('diffView' + idx).classList.add('active');
        }}
        document.addEventListener('keydown', function(e) {{
            const active = document.querySelector('.view.active');
            if (!active || active.id === 'listView') return;
            const match = active.id.match(/diffView(\\d+)/);
            if (!match) return;
            const idx = parseInt(match[1]);
            if (e.key === 'ArrowUp' && idx > 0) showFile(idx - 1);
            else if (e.key === 'ArrowDown' && idx < {len(file_list) - 1}) showFile(idx + 1);
            else if (e.key === 'Escape') showList();
        }});
    </script>
</body>
</html>""")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))

    def _html_escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def generate_summary_markdown(self, output_path: Path):
        """Generate markdown summary."""
        print(f"Generating summary markdown: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Diff Summary\n\n")
            f.write(f"**Generated:** {datetime.now()}\n\n")
            f.write(f"**Source 1 (IT/Modified):** `{self.dir1}`\n\n")
            f.write(f"**Source 2 (Reference):** `{self.dir2}`\n\n")
            f.write("---\n\n")

            f.write("## Statistics\n\n")
            f.write(f"- **Modified files:** {len(self.modified_files)}\n")
            f.write(f"- **Identical files:** {len(self.identical_files)}\n")
            f.write(f"- **Only in dir1:** {len(self.files_only_in_dir1)}\n")
            f.write(f"- **Only in dir2:** {len(self.files_only_in_dir2)}\n\n")

            if self.modified_files:
                f.write("## Modified Files\n\n")
                for rel_path in sorted(self.modified_files.keys()):
                    content1, content2 = self.modified_files[rel_path]
                    lines_changed = sum(1 for line in difflib.unified_diff(content1, content2)
                                      if line.startswith(('+', '-')))
                    f.write(f"- `{rel_path}` ({lines_changed} lines changed)\n")
                f.write("\n")

            if self.files_only_in_dir1:
                f.write("## Files Only in Dir1 (Deleted)\n\n")
                for path in sorted(self.files_only_in_dir1):
                    f.write(f"- `{path}`\n")
                f.write("\n")

            if self.files_only_in_dir2:
                f.write("## Files Only in Dir2 (Added)\n\n")
                for path in sorted(self.files_only_in_dir2):
                    f.write(f"- `{path}`\n")
                f.write("\n")

    def generate_all_reports(self, output_prefix: str):
        """Generate all report formats."""
        output_prefix = Path(output_prefix)

        self.generate_unified_diff(Path(f"{output_prefix}.patch"))
        self.generate_text_diff(Path(f"{output_prefix}.txt"))
        self.generate_html_diff(Path(f"{output_prefix}.html"))
        self.generate_summary_markdown(Path(f"{output_prefix}_summary.md"))

        print("\n" + "=" * 80)
        print("✓ All reports generated successfully!")
        print("=" * 80)
        print(f"\nOutput files:")
        print(f"  - {output_prefix}.patch (unified diff - can be applied with 'git apply')")
        print(f"  - {output_prefix}.txt (plain text diff)")
        print(f"  - {output_prefix}.html (visual side-by-side - open in browser)")
        print(f"  - {output_prefix}_summary.md (overview)")
        print("\nTo apply the patch:")
        print(f"  git apply {output_prefix}.patch")


def main():
    parser = argparse.ArgumentParser(
        description="Compare two directory trees and generate comprehensive diff reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare IT's modified code vs remote main clone
  python diff_tool.py /path/to/IT/iris/src /path/to/cloned/iris/src --output sync_report

  # Compare with custom output location
  python diff_tool.py dir1 dir2 --output ~/Desktop/my_diff
        """
    )

    parser.add_argument('dir1', help='First directory (IT/modified version)')
    parser.add_argument('dir2', help='Second directory (reference version)')
    parser.add_argument('--output', '-o', required=True,
                       help='Output prefix for generated reports')

    args = parser.parse_args()

    # Validate directories
    dir1 = Path(args.dir1)
    dir2 = Path(args.dir2)

    if not dir1.exists():
        print(f"Error: Directory not found: {dir1}", file=sys.stderr)
        sys.exit(1)

    if not dir2.exists():
        print(f"Error: Directory not found: {dir2}", file=sys.stderr)
        sys.exit(1)

    if not dir1.is_dir():
        print(f"Error: Not a directory: {dir1}", file=sys.stderr)
        sys.exit(1)

    if not dir2.is_dir():
        print(f"Error: Not a directory: {dir2}", file=sys.stderr)
        sys.exit(1)

    # Run the diff tool
    print("=" * 80)
    print("DIRECTORY DIFF TOOL")
    print("=" * 80)

    tool = DiffTool(dir1, dir2)
    tool.compare_directories()
    tool.generate_all_reports(args.output)


if __name__ == '__main__':
    main()
