#!/usr/bin/env python3

import os
import re
import glob
import subprocess

# Files we've already updated
UPDATED_FILES = [
    "iris/src/agents/database_subagents/internal_wiki/subagent.py",
    "iris/src/agents/database_subagents/internal_par/subagent.py",
    "iris/src/agents/database_subagents/external_kpmg/subagent.py",
    "iris/src/agents/database_subagents/internal_memos/subagent.py",
]

# Find the remaining subagent.py files
def find_subagent_files():
    all_files = glob.glob("iris/src/agents/database_subagents/**/subagent.py", recursive=True)
    return [f for f in all_files if f not in UPDATED_FILES]

# Update the imports and type definitions
def update_imports(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add Tuple import and SubagentResult definition
    new_content = re.sub(
        r'from typing import Any, Dict, List, Optional, Union, cast',
        r'from typing import Any, Dict, List, Optional, Union, cast, Tuple',
        content
    )
    
    # Add SubagentResult type definition after DatabaseResponse
    new_content = re.sub(
        r'DatabaseResponse = Union\[MetadataResponse, ResearchResponse\]',
        r'DatabaseResponse = Union[MetadataResponse, ResearchResponse]\nSubagentResult = Tuple[DatabaseResponse, Optional[List[str]]]  # Define a tuple for result + doc_ids',
        new_content
    )
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated imports in {file_path}")

# Update the query_database_sync function
def update_sync_function(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update the return type
    new_content = re.sub(
        r'def query_database_sync\(\s*query: str, scope: str, token: Optional\[str\] = None\s*\) -> DatabaseResponse:',
        r'def query_database_sync(\n    query: str, scope: str, token: Optional[str] = None\n) -> SubagentResult:',
        content
    )
    
    # Add the docstring update
    new_content = re.sub(
        r'"""[^"]*Synchronously query the [^"]*database[^"]*\.',
        r'"""\n    Synchronously query the database based on the specified scope.\n    \n    Returns:\n        Tuple containing the main database response and a list of selected document IDs (or None).',
        new_content
    )
    
    # Add the selected_doc_ids variable
    db_name_pattern = r'database_name = "([^"]+)"'
    match = re.search(db_name_pattern, new_content)
    db_name = match.group(1) if match else "unknown_database"
    
    # Add initialization of selected_doc_ids
    new_content = re.sub(
        rf'database_name = "{db_name}"[^\n]*\n([^\n]*)',
        f'database_name = "{db_name}"\n    default_error_status = "❌ Error during query processing."\n    selected_doc_ids: Optional[List[str]] = None  # Initialize\n\\1',
        new_content
    )
    
    # Update variable names and return statements
    # 1. Change 'doc_ids' to 'selected_doc_ids'
    new_content = re.sub(
        r'doc_ids = select_relevant_documents\(',
        r'selected_doc_ids = select_relevant_documents(  # Assign to variable',
        new_content
    )
    
    # 2. Update references to doc_ids
    new_content = re.sub(
        r'LLM selected (\{[^}]+\}) relevant .* document IDs: \{doc_ids\}"',
        r'LLM selected \\1 relevant document IDs: {selected_doc_ids}"',
        new_content
    )
    
    # 3. Add database response typing and return tuples for early returns
    new_content = re.sub(
        r'if not catalog:\s*if scope == "metadata":\s*return \[\]\s*else:\s*return \{',
        r'if not catalog:\n            response: DatabaseResponse\n            if scope == "metadata":\n                response = []\n            else:\n                response = {\n',
        new_content
    )
    new_content = re.sub(
        r'("status_summary": "📄 No documents found in catalog.",\s*}\s*)',
        r'\1\n            return response, selected_doc_ids  # Return empty response and None IDs\n',
        new_content
    )
    
    # 4. Update for the empty doc_ids case
    new_content = re.sub(
        r'if not (selected_)?doc_ids:\s*if scope == "metadata":\s*return \[\]\s*else:\s*return \{',
        r'if not selected_doc_ids:\n            response: DatabaseResponse\n            if scope == "metadata":\n                response = []\n            else:\n                response = {\n',
        new_content
    )
    new_content = re.sub(
        r'("status_summary": "📄 No relevant documents selected by LLM.",\s*}\s*)',
        r'\1\n            return response, selected_doc_ids  # Return empty response and empty IDs list\n',
        new_content
    )
    
    # 5. Update return statements for metadata scope
    new_content = re.sub(
        r'(selected_items = \[.*\]\s*logger\.info.*\s*return selected_items)',
        r'\1, selected_doc_ids  # Return metadata and IDs',
        new_content
    )
    
    # 6. Update return statements for research scope
    new_content = re.sub(
        r'(research_result = synthesize_response_and_status\(.*\)\s*return research_result)',
        r'\1, selected_doc_ids  # Return research and IDs',
        new_content
    )
    
    # 7. Update error handling for ValueError
    new_content = re.sub(
        r'(logger\.error\(f"Invalid scope provided to .* subagent: \{scope\}"\)\s*raise ValueError\(f"Invalid scope: \{scope\}"\))',
        r'\1  # Let the error propagate',
        new_content
    )
    
    # 8. Update final error handling
    new_content = re.sub(
        r'error_msg = f"Error querying .* database \(scope: \{scope\}\): \{str\(e\)\}"(.*\s*)if scope == "metadata":\s*return \[\]\s*else:\s*return \{',
        r'error_msg = f"Error querying database (scope: {scope}): {str(e)}"\1        response: DatabaseResponse\n        if scope == "metadata":\n            response = []\n        else:\n            response = {\n',
        new_content
    )
    new_content = re.sub(
        r'("status_summary": default_error_status,\s*}\s*)',
        r'\1\n        # Return error response and potentially selected IDs if selection succeeded before error\n        return response, selected_doc_ids',
        new_content
    )
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated query_database_sync in {file_path}")

def main():
    files = find_subagent_files()
    print(f"Found {len(files)} subagent files to update")
    
    for file_path in files:
        print(f"\nProcessing {file_path}...")
        update_imports(file_path)
        update_sync_function(file_path)

if __name__ == "__main__":
    main()