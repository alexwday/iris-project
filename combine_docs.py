#!/usr/bin/env python3
"""
Script to combine markdown documentation files into a single text file
that can be easily pasted into Microsoft Word.

This script:
1. Reads all numbered markdown files in the docs/model_documentation directory
2. Sorts them by number prefix
3. Formats the content for clean pasting into Word
4. Combines them into a single text file
"""

import os
import re
import glob

def format_for_word(text):
    """
    Format markdown content for clean pasting into Word.
    Preserves headings, lists, tables, and basic formatting.
    """
    # Format headings with proper levels
    # Level 1 (# Heading) - Large with double line break
    text = re.sub(r'^# (.*?)$', r'\1\n', text, flags=re.MULTILINE)
    
    # Level 2 (## Heading) - Medium with line break
    text = re.sub(r'^## (.*?)$', r'\1\n', text, flags=re.MULTILINE)
    
    # Level 3 (### Heading) - Small with line break
    text = re.sub(r'^### (.*?)$', r'\1\n', text, flags=re.MULTILINE)
    
    # Level 4+ (#### Heading+) - Small with no line break
    text = re.sub(r'^#{4,} (.*?)$', r'\1', text, flags=re.MULTILINE)
    
    # Format bold text (keep the ** for Word to interpret)
    # Word will automatically recognize ** as bold when pasting
    # text = re.sub(r'(\*\*|__)(.*?)(\*\*|__)', r'\2', text)
    
    # Format emphasis (keep the * for Word to interpret)
    # Word will automatically recognize * as italic when pasting
    # text = re.sub(r'(\*|_)(.*?)(\*|_)', r'\2', text)
    
    # Format lists for Word
    # Bullet lists with proper symbols that Word will recognize
    text = re.sub(r'^\s*- (.*?)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s{2,4}- (.*?)$', r'   ○ \1', text, flags=re.MULTILINE)
    text = re.sub(r'^\s{4,6}- (.*?)$', r'      ▪ \1', text, flags=re.MULTILINE)
    
    # Preserve numbered lists (Word will recognize these properly)
    # No change needed for numbered lists as they will paste correctly
    
    # Handle tables by preserving pipe format
    # Word will interpret pipe tables as plain text, but they'll be readable
    
    # Remove code blocks but preserve content
    text = re.sub(r'```.*?\n(.*?)```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    # Replace links with just the text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove image markup but keep alt text
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Format blockquotes as indented text
    text = re.sub(r'^> (.*?)$', r'   \1', text, flags=re.MULTILINE)
    
    # Remove horizontal rules and replace with line breaks
    text = re.sub(r'^-{3,}$', r'\n', text, flags=re.MULTILINE)
    text = re.sub(r'^_{3,}$', r'\n', text, flags=re.MULTILINE)
    text = re.sub(r'^\*{3,}$', r'\n', text, flags=re.MULTILINE)
    
    # Ensure proper spacing between sections (normalize to at most 2 newlines)
    text = re.sub(r'\n{3,}', r'\n\n', text)
    
    return text

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
    
    # Combine content
    combined_text = ""
    
    for _, file_path in numbered_files:
        with open(file_path, 'r') as file:
            content = file.read()
            
            # Add section divider between documents
            if combined_text:
                combined_text += "\n" + "-" * 80 + "\n\n"
                
            # Format content for Word
            formatted_content = format_for_word(content)
            
            # Add to combined text
            combined_text += formatted_content + "\n\n"
    
    # Write to output file
    output_path = "combined_model_documentation.txt"
    with open(output_path, 'w') as outfile:
        outfile.write(combined_text)
    
    print(f"Combined document written to {output_path}")
    print("You can now copy the content from this file and paste it into Word.")
    print("The content has been formatted to preserve structure when pasted into Word.")

if __name__ == "__main__":
    main()