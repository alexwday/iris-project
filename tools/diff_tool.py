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
        """Generate simple, clean diff viewer."""
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

        /* Diff Content */
        .diff-content {
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
        }
        .diff-line {
            padding: 2px 8px;
            white-space: pre;
        }
        .diff-add {
            background: #e6ffed;
            color: #22863a;
        }
        .diff-remove {
            background: #ffeef0;
            color: #cb2431;
        }
        .diff-context {
            background: #f6f8fa;
            color: #666;
        }
        .line-indicator {
            display: inline-block;
            width: 20px;
            font-weight: bold;
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

        html.append("""
        </div>
    </div>""")

        # Diff views
        for idx, rel_path in enumerate(file_list):
            content1, content2 = self.modified_files[rel_path]

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                content1,
                content2,
                fromfile='Current (Remote Main)',
                tofile='IT Modified',
                lineterm=''
            ))

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
        <div class="diff-content">""")

            # Show unified diff
            for line in diff_lines:
                if line.startswith('+++') or line.startswith('---'):
                    continue
                elif line.startswith('+'):
                    html.append(f'<div class="diff-line diff-add"><span class="line-indicator">+</span>{self._html_escape(line[1:])}</div>')
                elif line.startswith('-'):
                    html.append(f'<div class="diff-line diff-remove"><span class="line-indicator">-</span>{self._html_escape(line[1:])}</div>')
                elif line.startswith('@@'):
                    html.append(f'<div class="diff-line" style="background: #e0e0e0; font-weight: bold; margin-top: 10px;">{self._html_escape(line)}</div>')
                else:
                    html.append(f'<div class="diff-line diff-context"><span class="line-indicator"> </span>{self._html_escape(line[1:] if line else "")}</div>')

            html.append("""
        </div>
    </div>""")

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
