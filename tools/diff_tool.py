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
        """Generate side-by-side diff viewer with line numbers."""
        print(f"Generating HTML diff: {output_path}")

        html = []
        html.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Diff Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
            background: #f5f5f5;
            color: #333;
        }
        .view { display: none; }
        .view.active { display: block; }

        /* List View */
        .list-view {
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .stats {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .file-item {
            background: white;
            padding: 15px 20px;
            margin-bottom: 8px;
            border-left: 4px solid #2196F3;
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        .file-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            transform: translateX(4px);
        }
        .file-name {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .file-meta {
            font-size: 12px;
            color: #999;
        }

        /* Diff View */
        .diff-view {
            background: white;
            min-height: 100vh;
        }
        .diff-header {
            background: #2196F3;
            color: white;
            padding: 15px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .diff-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .diff-buttons button {
            background: white;
            color: #2196F3;
            border: none;
            padding: 6px 12px;
            margin-right: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            border-radius: 3px;
        }
        .diff-buttons button:hover {
            background: #f0f0f0;
        }

        /* Side-by-side Diff */
        .diff-content {
            padding: 20px;
        }
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', Consolas, monospace;
            font-size: 12px;
            line-height: 1.5;
        }
        .diff-table td {
            padding: 2px 8px;
            vertical-align: top;
            border-right: 1px solid #ddd;
        }
        .diff-table td:last-child {
            border-right: none;
        }
        .line-num {
            width: 50px;
            text-align: right;
            color: #999;
            user-select: none;
            background: #fafafa;
            font-weight: normal;
            padding-right: 12px;
        }
        .line-code {
            white-space: pre-wrap;
            word-wrap: break-word;
            max-width: 45vw;
            padding-left: 8px;
        }
        .line-code-continuation {
            padding-left: 24px;
            border-left: 2px solid #ccc;
            margin-left: 4px;
        }
        .diff-unchanged {
            background: white;
        }
        .diff-context {
            background: #fafafa;
            color: #666;
        }
        .diff-add {
            background: #e6ffed;
        }
        .diff-add .line-code {
            color: #22863a;
        }
        .diff-remove {
            background: #ffeef0;
        }
        .diff-remove .line-code {
            color: #cb2431;
        }
        .diff-empty {
            background: #f6f8fa;
        }
        .diff-header-row {
            background: #e0e0e0;
            font-weight: bold;
            color: #333;
        }
        .diff-header-row td {
            padding: 8px;
            border-bottom: 2px solid #999;
        }
        .side-label {
            font-weight: 600;
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            padding: 8px !important;
            background: #f0f0f0;
        }
        .diff-separator {
            background: #e8e8e8;
            height: 8px;
        }
        .hunk-header {
            background: #f0f0f0;
            color: #666;
            font-weight: bold;
            font-size: 11px;
            padding: 6px 8px !important;
            border-top: 2px solid #ccc;
            border-bottom: 1px solid #ddd;
        }
        .ws-diff {
            border: 2px solid #ff9800 !important;
            background: #fff3e0 !important;
        }
        .ws-diff.diff-remove {
            background: #ffeef0 !important;
            border-color: #ff9800 !important;
        }
        .ws-diff.diff-add {
            background: #e6ffed !important;
            border-color: #ff9800 !important;
        }
    </style>
</head>
<body>
    <div id="listView" class="view active">
        <div class="list-view">
            <h1>Diff Report</h1>
            <div class="stats">
                """ + str(len(self.modified_files)) + """ files modified | """ + str(len(self.files_only_in_dir2)) + """ added | """ + str(len(self.files_only_in_dir1)) + """ deleted
            </div>""")

        # File list
        file_list = sorted(self.modified_files.keys())
        for idx, rel_path in enumerate(file_list):
            content1, content2 = self.modified_files[rel_path]

            # Count changed lines
            diff = list(difflib.unified_diff(content1, content2, lineterm=''))
            changes = sum(1 for line in diff if line.startswith(('+', '-')) and not line.startswith(('+++', '---')))

            html.append(f"""
            <div class="file-item" onclick="showFile({idx})">
                <div class="file-name">{rel_path}</div>
                <div class="file-meta">{changes} lines changed</div>
            </div>""")

        # Added files (new files)
        if self.files_only_in_dir2:
            for file_idx, path in enumerate(sorted(self.files_only_in_dir2)):
                html.append(f"""
            <div class="file-item" onclick="showFile({len(file_list) + file_idx})">
                <div class="file-name">{path}</div>
                <div class="file-meta">NEW FILE</div>
            </div>""")

        # Deleted files
        if self.files_only_in_dir1:
            for file_idx, path in enumerate(sorted(self.files_only_in_dir1)):
                html.append(f"""
            <div class="file-item" onclick="showFile({len(file_list) + len(self.files_only_in_dir2) + file_idx})">
                <div class="file-name">{path}</div>
                <div class="file-meta">DELETED FILE</div>
            </div>""")

        html.append("""
        </div>
    </div>""")

        # Diff views for modified files
        for idx, rel_path in enumerate(file_list):
            content1, content2 = self.modified_files[rel_path]

            html.append(f"""
    <div id="diffView{idx}" class="view diff-view">
        <div class="diff-header">
            <div class="diff-title">{rel_path}</div>
            <div class="diff-buttons">
                <button onclick="showList()">← Back</button>""")

            if idx > 0:
                html.append(f"""<button onclick="showFile({idx - 1})">← Prev</button>""")
            if idx < len(file_list) - 1:
                html.append(f"""<button onclick="showFile({idx + 1})">Next →</button>""")

            html.append("""
            </div>
        </div>
        <div class="diff-content">
            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin-bottom: 15px; font-size: 12px; border-radius: 4px;">
                <strong>Whitespace Legend:</strong>
                <span style="background: #ffeb3b; color: #000; font-weight: bold; margin-left: 10px;">·</span> = trailing space
                <span style="background: #ff9800; color: #000; font-weight: bold; margin-left: 10px;">→</span> = tab character
                <span style="border: 2px solid #ff9800; padding: 2px 8px; margin-left: 10px;">Orange border</span> = whitespace-only difference (hover for tooltip)
            </div>""")

            # Add comprehensive byte analysis for ALL differences
            html.append("""
            <div style="background: #fff; border: 2px solid #ff5722; padding: 12px; margin-bottom: 15px; font-size: 12px;">
                <strong style="color: #ff5722; font-size: 14px;">🔍 BYTE-LEVEL ANALYSIS OF ALL DIFFERENCES</strong><br><br>""")

            diff_count = 0
            for i in range(len(content1)):
                if i < len(content2):
                    line1 = content1[i].rstrip('\n')
                    line2 = content2[i].rstrip('\n')
                    if line1 != line2:
                        diff_count += 1
                        html.append(f"""<div style="margin-bottom: 15px; padding: 8px; background: #f9f9f9; border-left: 3px solid #ff5722;">
                        <strong>Line {i + 1}:</strong><br>""")
                        html.append(self._get_byte_analysis(line1, line2))
                        html.append("</div>")

            if diff_count == 0:
                html.append("<em>No line differences found</em>")
            else:
                html.append(f"<strong>Total differences: {diff_count} lines</strong>")

            html.append("""
            </div>
            <table class="diff-table">
                <tr class="diff-header-row">
                    <td class="side-label" colspan="2">Current (Remote Main)</td>
                    <td class="side-label" colspan="2">IT Modified</td>
                </tr>""")

            # Generate side-by-side diff with context (only show changed blocks)
            matcher = difflib.SequenceMatcher(None, content1, content2)
            context_lines = 3  # Number of context lines to show before/after changes

            opcodes = list(matcher.get_opcodes())
            last_shown_line = -1

            for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
                # Skip if this is just context between changes
                if tag == 'equal':
                    # Determine if we should show this equal block
                    show_start = max(i1, last_shown_line + 1)
                    show_end = i2

                    # Check if there's a change coming after this
                    has_next_change = idx + 1 < len(opcodes) and opcodes[idx + 1][0] != 'equal'
                    # Check if there was a change before this
                    has_prev_change = last_shown_line >= 0

                    if has_prev_change:
                        # Show context lines after previous change
                        show_start = i1
                        show_end = min(i1 + context_lines, i2)

                    if has_next_change:
                        # Show context lines before next change
                        show_start = max(i2 - context_lines, show_start)
                        show_end = i2

                    # If this equal block is between two changes and small, show it all
                    if has_prev_change and has_next_change and (i2 - i1) <= context_lines * 2:
                        show_start = i1
                        show_end = i2

                    # Skip if no context to show
                    if not has_prev_change and not has_next_change:
                        continue

                    # Show context collapse indicator if we're skipping lines
                    if has_prev_change and i1 < show_start:
                        html.append(f"""
                <tr class="diff-separator">
                    <td colspan="4"></td>
                </tr>
                <tr>
                    <td colspan="4" class="hunk-header">... ({show_start - i1} lines hidden) ...</td>
                </tr>""")

                    # Show context lines
                    for i in range(show_start, show_end):
                        line1 = content1[i].rstrip('\n')
                        line2 = content2[j1 + (i - i1)].rstrip('\n')

                        # Check if these "equal" lines are actually different (shouldn't happen but check anyway)
                        byte_analysis = ''
                        if line1 != line2:
                            byte_analysis = self._get_byte_analysis(line1, line2)

                        html.append(f"""
                <tr class="diff-context">
                    <td class="line-num">{i + 1}</td>
                    <td class="line-code">{self._html_escape(line1)}</td>
                    <td class="line-num">{j1 + (i - i1) + 1}</td>
                    <td class="line-code">{self._html_escape(line2)}</td>
                </tr>""")

                        if byte_analysis:
                            html.append(f"""
                <tr>
                    <td colspan="4" style="padding: 0;">{byte_analysis}</td>
                </tr>""")

                    last_shown_line = show_end - 1
                    continue

                # Show hunk header if there was a gap
                if last_shown_line >= 0 and i1 > last_shown_line + 1:
                    html.append(f"""
                <tr class="diff-separator">
                    <td colspan="4"></td>
                </tr>
                <tr>
                    <td colspan="4" class="hunk-header">@@ -{i1 + 1},{i2 - i1} +{j1 + 1},{j2 - j1} @@</td>
                </tr>""")

                # Show the actual change
                if tag == 'replace':
                    # Show removed lines on left, added lines on right
                    max_lines = max(i2 - i1, j2 - j1)
                    for k in range(max_lines):
                        left_line = content1[i1 + k].rstrip('\n') if i1 + k < i2 else ''
                        left_num = i1 + k + 1 if i1 + k < i2 else ''
                        right_line = content2[j1 + k].rstrip('\n') if j1 + k < j2 else ''
                        right_num = j1 + k + 1 if j1 + k < j2 else ''

                        left_class = 'diff-remove' if left_line else 'diff-empty'
                        right_class = 'diff-add' if right_line else 'diff-empty'

                        # Check if lines differ only by whitespace
                        ws_only_diff = ''
                        byte_analysis = ''
                        if left_line and right_line and self._lines_differ_only_by_whitespace(left_line, right_line):
                            ws_only_diff = ' title="⚠ Whitespace-only difference"'
                            left_class += ' ws-diff'
                            right_class += ' ws-diff'

                        # Add byte-level analysis for any difference
                        if left_line and right_line and left_line != right_line:
                            byte_analysis = self._get_byte_analysis(left_line, right_line)

                        html.append(f"""
                <tr>
                    <td class="line-num {left_class}">{left_num}</td>
                    <td class="line-code {left_class}"{ws_only_diff}>{self._html_escape(left_line) if left_line else '&nbsp;'}</td>
                    <td class="line-num {right_class}">{right_num}</td>
                    <td class="line-code {right_class}"{ws_only_diff}>{self._html_escape(right_line) if right_line else '&nbsp;'}</td>
                </tr>""")

                        # Add byte analysis row if there's a difference
                        if byte_analysis:
                            html.append(f"""
                <tr>
                    <td colspan="4" style="padding: 0;">{byte_analysis}</td>
                </tr>""")
                elif tag == 'delete':
                    for i in range(i1, i2):
                        line = content1[i].rstrip('\n')
                        html.append(f"""
                <tr>
                    <td class="line-num diff-remove">{i + 1}</td>
                    <td class="line-code diff-remove">{self._html_escape(line)}</td>
                    <td class="line-num diff-empty"></td>
                    <td class="line-code diff-empty">&nbsp;</td>
                </tr>""")
                elif tag == 'insert':
                    for j in range(j1, j2):
                        line = content2[j].rstrip('\n')
                        html.append(f"""
                <tr>
                    <td class="line-num diff-empty"></td>
                    <td class="line-code diff-empty">&nbsp;</td>
                    <td class="line-num diff-add">{j + 1}</td>
                    <td class="line-code diff-add">{self._html_escape(line)}</td>
                </tr>""")

                last_shown_line = i2 - 1

            html.append("""
            </table>
        </div>
    </div>""")

        # Diff views for new files
        new_file_idx = len(file_list)
        for path in sorted(self.files_only_in_dir2):
            # Read the new file content
            full_path = self.dir2 / path
            content = self._read_file(full_path)

            html.append(f"""
    <div id="diffView{new_file_idx}" class="view diff-view">
        <div class="diff-header">
            <div class="diff-title">{path} (NEW FILE)</div>
            <div class="diff-buttons">
                <button onclick="showList()">← Back</button>
            </div>
        </div>
        <div class="diff-content">""")

            # Show entire file content as additions
            for line_num, line in enumerate(content, 1):
                html.append(f'<div class="diff-line diff-add"><span class="line-indicator">{line_num}</span>{self._html_escape(line.rstrip())}</div>')

            html.append("""
        </div>
    </div>""")
            new_file_idx += 1

        # Diff views for deleted files
        deleted_file_idx = new_file_idx
        for path in sorted(self.files_only_in_dir1):
            # Read the deleted file content
            full_path = self.dir1 / path
            content = self._read_file(full_path)

            html.append(f"""
    <div id="diffView{deleted_file_idx}" class="view diff-view">
        <div class="diff-header">
            <div class="diff-title">{path} (DELETED FILE)</div>
            <div class="diff-buttons">
                <button onclick="showList()">← Back</button>
            </div>
        </div>
        <div class="diff-content">""")

            # Show entire file content as removals
            for line_num, line in enumerate(content, 1):
                html.append(f'<div class="diff-line diff-remove"><span class="line-indicator">{line_num}</span>{self._html_escape(line.rstrip())}</div>')

            html.append("""
        </div>
    </div>""")
            deleted_file_idx += 1

        # JavaScript
        html.append("""
    <script>
        function showList() {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('listView').classList.add('active');
            window.scrollTo(0, 0);
        }
        function showFile(idx) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('diffView' + idx).classList.add('active');
            window.scrollTo(0, 0);
        }
    </script>
</body>
</html>""")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))

    def _html_escape(self, text: str) -> str:
        """Escape HTML special characters and visualize whitespace."""
        # First escape HTML
        escaped = (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

        # Visualize trailing spaces with visible marker
        if escaped.endswith(' '):
            # Count trailing spaces
            stripped = escaped.rstrip(' ')
            trailing_count = len(escaped) - len(stripped)
            escaped = stripped + '<span style="background: #ffeb3b; color: #000; font-weight: bold;">·</span>' * trailing_count

        # Visualize tabs
        escaped = escaped.replace('\t', '<span style="background: #ff9800; color: #000; font-weight: bold;">→</span>')

        return escaped

    def _lines_differ_only_by_whitespace(self, line1: str, line2: str) -> bool:
        """Check if two lines differ only by whitespace."""
        return line1.strip() == line2.strip() and line1 != line2

    def _get_byte_analysis(self, line1: str, line2: str) -> str:
        """Generate detailed byte-level analysis of two different lines."""
        analysis = []

        # Basic info
        analysis.append(f"<div style='font-family: monospace; font-size: 11px; background: #f9f9f9; padding: 8px; margin-top: 4px; border-left: 3px solid #ff5722;'>")
        analysis.append(f"<strong style='color: #ff5722;'>🔍 BYTE-LEVEL ANALYSIS:</strong><br>")
        analysis.append(f"Line 1 length: {len(line1)} bytes | Line 2 length: {len(line2)} bytes<br>")

        # Show hex dump of each line
        hex1 = ' '.join(f'{ord(c):02x}' for c in line1)
        hex2 = ' '.join(f'{ord(c):02x}' for c in line2)

        analysis.append(f"<br><strong>Line 1 hex:</strong> {hex1}<br>")
        analysis.append(f"<strong>Line 2 hex:</strong> {hex2}<br>")

        # Character-by-character comparison
        max_len = max(len(line1), len(line2))
        diffs = []

        for i in range(max_len):
            c1 = line1[i] if i < len(line1) else None
            c2 = line2[i] if i < len(line2) else None

            if c1 != c2:
                c1_repr = f"'{c1}' (0x{ord(c1):02x})" if c1 else "EOF"
                c2_repr = f"'{c2}' (0x{ord(c2):02x})" if c2 else "EOF"

                # Special character names
                if c1 and ord(c1) < 32:
                    c1_repr += f" [{self._get_control_char_name(ord(c1))}]"
                if c2 and ord(c2) < 32:
                    c2_repr += f" [{self._get_control_char_name(ord(c2))}]"

                diffs.append(f"Pos {i}: {c1_repr} ≠ {c2_repr}")

        if diffs:
            analysis.append(f"<br><strong>Differences found at {len(diffs)} position(s):</strong><br>")
            for diff in diffs[:10]:  # Show first 10 differences
                analysis.append(f"• {diff}<br>")
            if len(diffs) > 10:
                analysis.append(f"• ... and {len(diffs) - 10} more<br>")

        analysis.append("</div>")
        return ''.join(analysis)

    def _get_control_char_name(self, byte_val: int) -> str:
        """Get name for control characters."""
        names = {
            0: 'NUL', 9: 'TAB', 10: 'LF', 13: 'CR', 32: 'SPACE'
        }
        return names.get(byte_val, f'CTRL-{byte_val}')

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
