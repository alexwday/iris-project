#!/usr/bin/env python3
"""
Whitespace Checker - Detect invisible character differences between files.

Usage:
    python whitespace_checker.py <file1> <file2>
    python whitespace_checker.py <file1> <file2> --line <line_num>
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple


class WhitespaceChecker:
    """Detect and report invisible character differences."""

    def __init__(self, file1: Path, file2: Path):
        self.file1 = Path(file1)
        self.file2 = Path(file2)

    def read_file_bytes(self, path: Path) -> List[bytes]:
        """Read file as bytes to preserve all characters."""
        with open(path, 'rb') as f:
            return f.readlines()

    def analyze_line(self, line: bytes, line_num: int, file_name: str) -> dict:
        """Analyze a single line for whitespace issues."""
        info = {
            'line_num': line_num,
            'file': file_name,
            'length': len(line),
            'has_trailing_whitespace': False,
            'has_tabs': False,
            'has_crlf': False,
            'leading_spaces': 0,
            'trailing_spaces': 0,
            'invisible_chars': []
        }

        # Check for CRLF
        if line.endswith(b'\r\n'):
            info['has_crlf'] = True
            line_content = line[:-2]
        elif line.endswith(b'\n'):
            line_content = line[:-1]
        else:
            line_content = line

        # Check for tabs
        if b'\t' in line_content:
            info['has_tabs'] = True

        # Count leading spaces
        for byte in line_content:
            if byte == ord(' '):
                info['leading_spaces'] += 1
            elif byte == ord('\t'):
                info['leading_spaces'] += 1  # Count tabs too
            else:
                break

        # Count trailing spaces
        for byte in reversed(line_content):
            if byte == ord(' '):
                info['trailing_spaces'] += 1
            else:
                break

        info['has_trailing_whitespace'] = info['trailing_spaces'] > 0

        # Find invisible/unusual characters
        for i, byte in enumerate(line_content):
            if byte < 32 and byte not in (9, 10, 13):  # Not tab, LF, CR
                info['invisible_chars'].append((i, byte))
            elif byte > 127:  # Non-ASCII
                info['invisible_chars'].append((i, byte))

        return info

    def compare_lines(self, line1: bytes, line2: bytes, line_num: int) -> dict:
        """Compare two lines and find differences."""
        diff = {
            'line_num': line_num,
            'identical': line1 == line2,
            'length_diff': len(line1) - len(line2),
            'differences': []
        }

        if diff['identical']:
            return diff

        # Byte-by-byte comparison
        max_len = max(len(line1), len(line2))
        for i in range(max_len):
            byte1 = line1[i] if i < len(line1) else None
            byte2 = line2[i] if i < len(line2) else None

            if byte1 != byte2:
                diff['differences'].append({
                    'position': i,
                    'file1': self._byte_repr(byte1),
                    'file2': self._byte_repr(byte2)
                })

        return diff

    def _byte_repr(self, byte: int | None) -> str:
        """Get human-readable representation of a byte."""
        if byte is None:
            return 'EOF'
        elif byte == ord(' '):
            return 'SPACE'
        elif byte == ord('\t'):
            return 'TAB'
        elif byte == ord('\n'):
            return 'LF'
        elif byte == ord('\r'):
            return 'CR'
        elif byte < 32:
            return f'CTRL-{byte}'
        elif byte > 127:
            return f'0x{byte:02X}'
        else:
            return chr(byte)

    def check_specific_line(self, line_num: int):
        """Check a specific line number for differences."""
        lines1 = self.read_file_bytes(self.file1)
        lines2 = self.read_file_bytes(self.file2)

        idx = line_num - 1  # Convert to 0-based index

        if idx >= len(lines1):
            print(f"Line {line_num} not in {self.file1.name}")
            return
        if idx >= len(lines2):
            print(f"Line {line_num} not in {self.file2.name}")
            return

        line1 = lines1[idx]
        line2 = lines2[idx]

        print(f"\n{'='*80}")
        print(f"Line {line_num} Comparison")
        print(f"{'='*80}\n")

        # Show raw bytes
        print(f"File 1: {self.file1.name}")
        print(f"  Raw bytes: {line1}")
        print(f"  Repr: {repr(line1)}")
        print(f"  Length: {len(line1)}\n")

        print(f"File 2: {self.file2.name}")
        print(f"  Raw bytes: {line2}")
        print(f"  Repr: {repr(line2)}")
        print(f"  Length: {len(line2)}\n")

        # Analyze each line
        info1 = self.analyze_line(line1, line_num, self.file1.name)
        info2 = self.analyze_line(line2, line_num, self.file2.name)

        print(f"File 1 Analysis:")
        print(f"  Leading spaces: {info1['leading_spaces']}")
        print(f"  Trailing spaces: {info1['trailing_spaces']}")
        print(f"  Has tabs: {info1['has_tabs']}")
        print(f"  Has CRLF: {info1['has_crlf']}")
        if info1['invisible_chars']:
            print(f"  Invisible chars: {info1['invisible_chars']}\n")
        else:
            print()

        print(f"File 2 Analysis:")
        print(f"  Leading spaces: {info2['leading_spaces']}")
        print(f"  Trailing spaces: {info2['trailing_spaces']}")
        print(f"  Has tabs: {info2['has_tabs']}")
        print(f"  Has CRLF: {info2['has_crlf']}")
        if info2['invisible_chars']:
            print(f"  Invisible chars: {info2['invisible_chars']}\n")
        else:
            print()

        # Compare
        comparison = self.compare_lines(line1, line2, line_num)
        if comparison['identical']:
            print("✓ Lines are IDENTICAL")
        else:
            print("✗ Lines are DIFFERENT")
            print(f"\n  Length difference: {comparison['length_diff']} bytes")
            print(f"  Differences at positions:")
            for diff in comparison['differences']:
                print(f"    Position {diff['position']}: '{diff['file1']}' vs '{diff['file2']}'")

    def check_all_lines(self):
        """Check all lines and report differences."""
        lines1 = self.read_file_bytes(self.file1)
        lines2 = self.read_file_bytes(self.file2)

        print(f"\n{'='*80}")
        print(f"Whitespace Analysis: {self.file1.name} vs {self.file2.name}")
        print(f"{'='*80}\n")

        print(f"File 1: {len(lines1)} lines")
        print(f"File 2: {len(lines2)} lines\n")

        # Find lines with trailing whitespace
        trailing_ws_1 = []
        trailing_ws_2 = []

        for i, line in enumerate(lines1, 1):
            info = self.analyze_line(line, i, self.file1.name)
            if info['has_trailing_whitespace']:
                trailing_ws_1.append(i)

        for i, line in enumerate(lines2, 1):
            info = self.analyze_line(line, i, self.file2.name)
            if info['has_trailing_whitespace']:
                trailing_ws_2.append(i)

        if trailing_ws_1:
            print(f"File 1 - Lines with trailing whitespace: {trailing_ws_1}")
        if trailing_ws_2:
            print(f"File 2 - Lines with trailing whitespace: {trailing_ws_2}")

        # Find different lines
        different_lines = []
        max_lines = max(len(lines1), len(lines2))

        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else b''
            line2 = lines2[i] if i < len(lines2) else b''

            if line1 != line2:
                different_lines.append(i + 1)

        if different_lines:
            print(f"\nLines that differ: {len(different_lines)} total")
            print(f"Line numbers: {different_lines[:20]}" +
                  (" ..." if len(different_lines) > 20 else ""))

            # Show details for first few differences
            print(f"\nFirst 5 differences (use --line <num> for details):")
            for line_num in different_lines[:5]:
                idx = line_num - 1
                line1 = lines1[idx] if idx < len(lines1) else b''
                line2 = lines2[idx] if idx < len(lines2) else b''

                comparison = self.compare_lines(line1, line2, line_num)
                print(f"\n  Line {line_num}:")
                print(f"    Length: {len(line1)} vs {len(line2)}")
                if comparison['differences']:
                    first_diff = comparison['differences'][0]
                    print(f"    First diff at pos {first_diff['position']}: "
                          f"'{first_diff['file1']}' vs '{first_diff['file2']}'")
        else:
            print("\n✓ All lines are identical!")


def main():
    parser = argparse.ArgumentParser(
        description="Detect invisible character differences between files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('file1', help='First file to compare')
    parser.add_argument('file2', help='Second file to compare')
    parser.add_argument('--line', '-l', type=int,
                       help='Check specific line number')

    args = parser.parse_args()

    file1 = Path(args.file1)
    file2 = Path(args.file2)

    if not file1.exists():
        print(f"Error: File not found: {file1}", file=sys.stderr)
        sys.exit(1)

    if not file2.exists():
        print(f"Error: File not found: {file2}", file=sys.stderr)
        sys.exit(1)

    checker = WhitespaceChecker(file1, file2)

    if args.line:
        checker.check_specific_line(args.line)
    else:
        checker.check_all_lines()


if __name__ == '__main__':
    main()
