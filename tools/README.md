# Diff Tool

A comprehensive directory comparison tool that generates multiple output formats for analyzing differences between two codebases.

## Purpose

This tool was created to sync code changes between IT's modified IRIS codebase and the local development version. It allows you to:
- Compare two directory trees
- Generate detailed diff reports in multiple formats
- Transfer changes between environments via portable files

## Installation

No additional dependencies required - uses Python standard library only.

## Usage

### Basic Command

```bash
python tools/diff_tool.py <dir1> <dir2> --output <output_prefix>
```

### On Your Work Computer

#### Step 1: Clone the remote repository

```bash
cd ~/temp
git clone https://github.com/your-org/iris-project.git iris-remote
cd iris-remote
git checkout main
```

#### Step 2: Run the diff tool

```bash
python tools/diff_tool.py \
  /path/to/IT/modified/iris/src \
  ~/temp/iris-remote/iris/src \
  --output ~/Desktop/sync_report
```

### Output Files

The tool generates four files:

1. **`sync_report.patch`** - Unified diff format
   - Can be applied directly with `git apply sync_report.patch`
   - Most compact format
   - **RECOMMENDED for transferring changes**

2. **`sync_report.txt`** - Plain text diff
   - Human-readable text format
   - Easy to copy-paste in emails or chat
   - Good for reviewing changes

3. **`sync_report.html`** - Visual side-by-side diff
   - Color-coded changes
   - Navigation menu for jumping between files
   - Open in any web browser
   - **BEST for reviewing and understanding changes**

4. **`sync_report_summary.md`** - Overview
   - High-level statistics
   - List of modified/added/deleted files
   - Quick reference

## Transfer Methods

### Method 1: Patch File (RECOMMENDED)

1. On work computer: Generate reports
2. Email yourself `sync_report.patch`
3. On personal computer: Save the patch file
4. Apply changes: `git apply sync_report.patch`

### Method 2: Text Copy-Paste

1. Open `sync_report.txt`
2. Copy contents
3. Paste into email/Slack/text file
4. Send to personal computer

### Method 3: HTML Review

1. Open `sync_report.html` in browser
2. Review all changes visually
3. Use browser's "Save Page As" to save complete HTML
4. Transfer file via USB/email

## Applying Changes

### Automatic (Using Patch)

```bash
# Navigate to your local iris project
cd /Users/alexwday/Projects/iris-project

# Apply the patch
git apply ~/Downloads/sync_report.patch

# Verify changes
git status
git diff
```

### Manual (With Claude Code)

1. Share the patch/text/HTML file with Claude Code
2. Claude will parse the diffs and apply changes to local files
3. Review and test changes

## Features

- **Smart filtering**: Skips `__pycache__`, `.pyc`, `.git`, `venv`, etc.
- **Binary file detection**: Handles non-UTF8 files gracefully
- **Line-by-line comparison**: Shows exact changes with context
- **File additions/deletions**: Tracks new and removed files
- **Zero dependencies**: Uses only Python standard library

## Example Output

```
================================================================================
DIRECTORY DIFF TOOL
================================================================================
Scanning /path/to/IT/iris/src...
Scanning /path/to/cloned/iris/src...

Comparing 87 files...

Generating unified diff: /Users/you/Desktop/sync_report.patch
Generating text diff: /Users/you/Desktop/sync_report.txt
Generating HTML diff: /Users/you/Desktop/sync_report.html
Generating summary markdown: /Users/you/Desktop/sync_report_summary.md

================================================================================
✓ All reports generated successfully!
================================================================================

Output files:
  - sync_report.patch (unified diff - can be applied with 'git apply')
  - sync_report.txt (plain text diff)
  - sync_report.html (visual side-by-side - open in browser)
  - sync_report_summary.md (overview)

To apply the patch:
  git apply sync_report.patch
```

## Troubleshooting

### "Directory not found" error
- Verify both paths exist
- Use absolute paths or ensure you're in the correct working directory

### "Not a directory" error
- Ensure you're pointing to directories, not files
- Check that paths are correct

### Permission errors
- Ensure you have read access to both directories
- On Unix/Mac, you may need to make the script executable: `chmod +x tools/diff_tool.py`

### Binary file diffs not showing
- Binary files are detected and marked as `<Binary file: filename>`
- The tool focuses on text-based source code files

## Tips

- Use the HTML output for initial review - it's the most readable
- Use the patch file for transferring - it's the most reliable
- Keep both directories in sync by re-running periodically
- The tool is idempotent - safe to run multiple times
