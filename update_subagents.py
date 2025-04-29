#!/usr/bin/env python
"""
Process Monitor Patch Script

This script updates database subagents to properly handle token tracking.
It groups subagents into categories based on their structure:
1. Standard internal subagents (wiki, cheatsheets, etc.)
2. CAPM-like subagents (multi-step section selection)
3. External subagents (IASB, EY, KPMG, PWC)
"""

import os
import glob
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define subagent categories
STANDARD_INTERNAL = [
    "internal_wiki", "internal_cheatsheets", "internal_compliance", 
    "internal_esg", "internal_ext_reporting_and_disclosure",
    "internal_global_finance_standards", "internal_icfr", 
    "internal_management_reporting", "internal_memos", 
    "internal_par", "internal_process_and_controls"
]

CAPM_LIKE = ["internal_capm"]

EXTERNAL = ["external_iasb", "external_ey", "external_kpmg", "external_pwc"]

def update_standard_subagent(file_path):
    """Update standard internal subagents."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Get the database name from the file path
    db_name = os.path.basename(os.path.dirname(file_path))
    logger.info(f"Updating standard subagent: {db_name}")
    
    # Replace function signature
    content = re.sub(
        r"def query_database_sync\(\s*query:\s*str,\s*scope:\s*str,\s*token:\s*Optional\[str\]\s*=\s*None\s*\)",
        "def query_database_sync(query: str, scope: str, token: Optional[str] = None, process_monitor=None)",
        content
    )
    
    # Add token tracking variables
    tracker_code = f"""    logger.info(f"Querying {db_name} database: '{{query}}' with scope: {{scope}}")
    database_name = "{db_name}"
    default_error_status = "❌ Error during query processing."
    selected_doc_ids: Optional[List[str]] = None  # Initialize
    stage_name = f"db_query_{{database_name}}"
    total_tokens = 0
    total_cost = 0.0
    llm_usage_list = []  # Track all LLM call usage details
"""
    
    # Find position to insert the code
    try:
        docstring_match = re.search(r"def query_database_sync\(.*?\):\s*\"\"\".*?\"\"\"\s*", content, re.DOTALL)
        if docstring_match:
            insert_pos = docstring_match.end()
            content = content[:insert_pos] + tracker_code + content[insert_pos:]
    except Exception as e:
        logger.error(f"Error finding insertion point: {e}")
        return False
    
    # Add token tracking for document selection
    content = re.sub(
        r"(result = get_completion\(\s*capability=\"small\",\s*prompt=selection_prompt,.*?database_name=database_name.*?\))",
        r"\1\n        # Track token usage from LLM calls\n        if isinstance(result, tuple) and len(result) == 2:\n            selection_response, usage_details = result\n            llm_usage_list.append(usage_details)\n            total_tokens += usage_details.get('input_tokens', 0) + usage_details.get('output_tokens', 0)\n            total_cost += usage_details.get('cost', 0)\n            # Update process monitor if available\n            if process_monitor:\n                process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)\n            selection_response_str = selection_response\n        else:\n            # For backward compatibility\n            selection_response_str = result",
        content,
        flags=re.DOTALL
    )
    
    # Replace the old document selection result handling
    content = re.sub(
        r"response_str = get_completion\(.*?database_name=database_name.*?\)(\s*\n\s*# Check if get_completion returned an error string\s*if isinstance\(response_str,)",
        r"result = get_completion(capability=\"small\", prompt=selection_prompt, max_tokens=200, token=token, database_name=database_name)\n\n        # Track token usage from LLM calls\n        if isinstance(result, tuple) and len(result) == 2:\n            selection_response, usage_details = result\n            llm_usage_list.append(usage_details)\n            total_tokens += usage_details.get('input_tokens', 0) + usage_details.get('output_tokens', 0)\n            total_cost += usage_details.get('cost', 0)\n            # Update process monitor if available\n            if process_monitor:\n                process_monitor.add_llm_call_details_to_stage(stage_name, usage_details)\n            selection_response_str = selection_response\n        else:\n            # For backward compatibility\n            selection_response_str = result\1",
        content,
        flags=re.DOTALL
    )
    
    # Add process monitor tracking for research synthesis
    content = re.sub(
        r"(response_obj = get_completion\(\s*capability=\"large\",\s*prompt=synthesis_prompt,.*?database_name=database_name.*?\))",
        r"\1\n\n        # Track token usage from synthesis\n        if isinstance(response_obj, tuple) and len(response_obj) == 2:\n            synthesis_response, synthesis_usage = response_obj\n            llm_usage_list.append(synthesis_usage)\n            total_tokens += synthesis_usage.get('input_tokens', 0) + synthesis_usage.get('output_tokens', 0)\n            total_cost += synthesis_usage.get('cost', 0)\n            # Update process monitor if available\n            if process_monitor:\n                process_monitor.add_llm_call_details_to_stage(stage_name, synthesis_usage)\n            response_obj = synthesis_response",
        content,
        flags=re.DOTALL
    )
    
    # Add process monitor stage details at the end
    content = re.sub(
        r"(return research_result, selected_doc_ids\s*# Return research result and IDs)",
        r"# Add token usage to process monitor before returning\n            if process_monitor:\n                process_monitor.add_stage_details(stage_name, \n                    result_count=len(documents), \n                    document_ids=selected_doc_ids,\n                    status_summary=research_result.get('status_summary', ''),\n                    total_tokens=total_tokens,\n                    total_cost=total_cost\n                )\n            \n            \1",
        content,
        flags=re.DOTALL
    )
    
    # Add process monitor error tracking
    content = re.sub(
        r"(return response, selected_doc_ids\s*# Return error response and potentially selected IDs if selection succeeded before error)",
        r"# Add token usage to process monitor before returning error\n        if process_monitor and llm_usage_list:\n            process_monitor.add_stage_details(stage_name, \n                error=str(e),\n                document_ids=selected_doc_ids,\n                total_tokens=total_tokens,\n                total_cost=total_cost\n            )\n            \n        \1",
        content,
        flags=re.DOTALL
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

def update_external_subagent(file_path):
    """Update external subagents (IASB, EY, KPMG, PWC)."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Get the database name from the file path
    db_name = os.path.basename(os.path.dirname(file_path))
    logger.info(f"Updating external subagent: {db_name}")
    
    # Replace function signature
    content = re.sub(
        r"def query_database_sync\(\s*query:\s*str,\s*scope:\s*str,\s*token:\s*Optional\[str\]\s*=\s*None\s*\)",
        "def query_database_sync(query: str, scope: str, token: Optional[str] = None, process_monitor=None)",
        content
    )
    
    # Add token tracking variables
    tracker_code = f"""    logger.info(f"Querying {db_name} database: '{{query}}' with scope: {{scope}}")
    database_name = "{db_name}"
    default_error_status = "❌ Error during query processing."
    selected_chunk_ids: Optional[List[str]] = None
    stage_name = f"db_query_{{database_name}}"
    total_tokens = 0
    total_cost = 0.0
    llm_usage_list = []  # Track all LLM call usage details
"""
    
    # Find position to insert the code
    try:
        docstring_match = re.search(r"def query_database_sync\(.*?\):\s*\"\"\".*?\"\"\"\s*", content, re.DOTALL)
        if docstring_match:
            insert_pos = docstring_match.end()
            content = content[:insert_pos] + tracker_code + content[insert_pos:]
    except Exception as e:
        logger.error(f"Error finding insertion point: {e}")
        return False
    
    # Add process monitor tracking for synthesis
    content = re.sub(
        r"(response_obj = get_completion\(\s*capability=\"large\",\s*prompt=synthesis_prompt,.*?database_name=database_name.*?\))",
        r"\1\n\n        # Track token usage from synthesis\n        if isinstance(response_obj, tuple) and len(response_obj) == 2:\n            synthesis_response, synthesis_usage = response_obj\n            llm_usage_list.append(synthesis_usage)\n            total_tokens += synthesis_usage.get('input_tokens', 0) + synthesis_usage.get('output_tokens', 0)\n            total_cost += synthesis_usage.get('cost', 0)\n            # Update process monitor if available\n            if process_monitor:\n                process_monitor.add_llm_call_details_to_stage(stage_name, synthesis_usage)\n            response_obj = synthesis_response",
        content,
        flags=re.DOTALL
    )
    
    # Add process monitor stage details at the end
    content = re.sub(
        r"(return research_result, selected_chunk_ids)",
        r"# Add token usage to process monitor before returning\n            if process_monitor:\n                process_monitor.add_stage_details(stage_name, \n                    result_count=len(formatted_chunks) if 'formatted_chunks' in locals() else 0, \n                    chunk_ids=selected_chunk_ids,\n                    status_summary=research_result.get('status_summary', ''),\n                    total_tokens=total_tokens,\n                    total_cost=total_cost\n                )\n            \n            \1",
        content,
        flags=re.DOTALL
    )
    
    # Add process monitor error tracking
    content = re.sub(
        r"(return response, selected_chunk_ids\s*# Return error response with chunk IDs if applicable)",
        r"# Add token usage to process monitor before returning error\n        if process_monitor and llm_usage_list:\n            process_monitor.add_stage_details(stage_name, \n                error=str(e),\n                chunk_ids=selected_chunk_ids,\n                total_tokens=total_tokens,\n                total_cost=total_cost\n            )\n            \n        \1",
        content,
        flags=re.DOTALL
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

def update_capm_subagent(file_path):
    """Update CAPM-like subagents with multi-step section selection."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Get the database name from the file path
    db_name = os.path.basename(os.path.dirname(file_path))
    logger.info(f"Updating CAPM-like subagent: {db_name}")
    
    # Ensure process_monitor parameter is in the function signature
    if "def query_database_sync" in content and "process_monitor=None" not in content:
        content = re.sub(
            r"def query_database_sync\(\s*query:\s*str,\s*scope:\s*str,\s*token:\s*Optional\[str\]\s*=\s*None\s*\)",
            "def query_database_sync(query: str, scope: str, token: Optional[str] = None, process_monitor=None)",
            content
        )
        
        # Add token tracking variables after database_name and before actual code
        try:
            match = re.search(r"database_name = \"{}\"\s+default_error_status".format(db_name), content)
            if match:
                pos = match.end()
                stage_code = "\n    stage_name = f\"db_query_{database_name}\"\n    total_tokens = 0\n    total_cost = 0.0\n    llm_usage_list = []  # Track all LLM call usage details\n"
                content = content[:pos] + stage_code + content[pos:]
        except Exception as e:
            logger.error(f"Error finding insertion point for stage tracking: {e}")
        
        # Add token tracking for document selection
        content = re.sub(
            r"selected_doc_ids = select_relevant_documents\(.*?query, catalog, token, database_name=database_name.*?\)\s+logger\.info",
            r"result = get_completion(\n            capability=\"small\",\n            prompt=get_catalog_selection_prompt(query, format_catalog_for_llm(catalog)),\n            max_tokens=200,\n            token=token,\n            database_name=database_name,\n        )\n        \n        # Track token usage from document selection\n        if isinstance(result, tuple) and len(result) == 2:\n            selection_response, selection_usage = result\n            llm_usage_list.append(selection_usage)\n            total_tokens += selection_usage.get('input_tokens', 0) + selection_usage.get('output_tokens', 0)\n            total_cost += selection_usage.get('cost', 0)\n            # Log usage for debugging\n            logger.debug(f\"Document selection usage: {selection_usage}\")\n            \n            # Update process monitor if available\n            if process_monitor:\n                process_monitor.add_llm_call_details_to_stage(stage_name, selection_usage)\n                process_monitor.add_stage_details(stage_name, task=\"document_selection\")\n                \n            # Process the response to extract document IDs\n            selection_response_str = selection_response\n        else:\n            # For backward compatibility\n            selection_response_str = result\n            \n        # Extract document IDs from selection response\n        if isinstance(selection_response_str, str) and selection_response_str.startswith(\"Error:\"):\n            logger.error(f\"get_completion failed during document selection: {selection_response_str}\")\n            selected_doc_ids = []\n        else:\n            try:\n                selected_doc_ids = json.loads(selection_response_str)\n                if isinstance(selected_doc_ids, list) and all(\n                    isinstance(i, str) for i in selected_doc_ids\n                ):\n                    logger.info(f\"LLM selected document IDs: {selected_doc_ids}\")\n                else:\n                    logger.error(\n                        f\"LLM response was valid JSON but not a list of strings: {selection_response_str}\"\n                    )\n                    selected_doc_ids = []\n            except json.JSONDecodeError:\n                logger.error(\n                    \"Failed to parse LLM response as JSON, attempting fallback extraction\"\n                )\n                # More comprehensive regex to extract document IDs\n                matches = re.findall(r'[\"\']([^\"\']+)[\"\']', selection_response_str)\n                selected_doc_ids = [m.strip() for m in matches if m.strip()]\n                if selected_doc_ids:\n                    logger.warning(\n                        f\"Extracted document IDs using fallback regex: {selected_doc_ids}\"\n                    )\n                else:\n                    logger.error(\"Could not extract document IDs from response using fallback.\")\n        \n        logger.info",
            content,
            flags=re.DOTALL
        )
        
        # Add process monitor stage details at various return points
        content = re.sub(
            r"(if not selected_doc_ids:.*?return response, selected_doc_ids\s*# Return empty response and empty IDs list)",
            r"if not selected_doc_ids:\n            response: DatabaseResponse\n            if scope == \"metadata\":\n                response = []\n            else:\n                response = {\n                    \"detailed_research\": \"LLM did not select any relevant documents from the catalog based on the query.\",\n                    \"status_summary\": \"📄 No relevant documents selected by LLM.\",\n                }\n            \n            # Add token usage to process monitor before returning\n            if process_monitor:\n                process_monitor.add_stage_details(stage_name, \n                    result_count=0, \n                    document_ids=selected_doc_ids,\n                    total_tokens=total_tokens,\n                    total_cost=total_cost\n                )\n                \n            return response, selected_doc_ids  # Return empty response and empty IDs list",
            content,
            flags=re.DOTALL
        )
        
        # Add process monitor stage details for metadata scope return
        content = re.sub(
            r"(logger\.info\(\s*f\"Returning \{len\(selected_items\)\} selected.*?\".*?\)\s+return selected_items, selected_doc_ids\s*# Return metadata and IDs)",
            r"logger.info(\n                f\"Returning {len(selected_items)} selected CAPM metadata items.\"\n            )\n            \n            # Add token usage to process monitor before returning\n            if process_monitor:\n                process_monitor.add_stage_details(stage_name, \n                    result_count=len(selected_items), \n                    document_ids=selected_doc_ids,\n                    total_tokens=total_tokens,\n                    total_cost=total_cost\n                )\n                \n            return selected_items, selected_doc_ids  # Return metadata and IDs",
            content,
            flags=re.DOTALL
        )
        
        # Add process monitor stage details for research result
        content = re.sub(
            r"(return research_result, selected_doc_ids\s*# Return research result and IDs)",
            r"# Add token usage to process monitor before returning\n            if process_monitor:\n                process_monitor.add_stage_details(stage_name, \n                    result_count=len(documents_with_content), \n                    document_ids=selected_doc_ids,\n                    status_summary=research_result.get(\"status_summary\", \"\"),\n                    total_tokens=total_tokens,\n                    total_cost=total_cost\n                )\n            \n            return research_result, selected_doc_ids  # Return research result and IDs",
            content,
            flags=re.DOTALL
        )
        
        # Add process monitor error handling
        content = re.sub(
            r"(return response, selected_doc_ids\s*# Return error response and potentially selected IDs if selection succeeded before error)",
            r"# Add token usage to process monitor before returning\n        if process_monitor and llm_usage_list:\n            process_monitor.add_stage_details(stage_name, \n                error=str(e),\n                document_ids=selected_doc_ids,\n                total_tokens=total_tokens,\n                total_cost=total_cost\n            )\n            \n        return response, selected_doc_ids  # Return error response and potentially selected IDs if selection succeeded before error",
            content,
            flags=re.DOTALL
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return True
    
    return False

def main():
    """Main function to update all subagents."""
    # Get all subagent files
    base_dir = "iris/src/agents/database_subagents"
    subagent_files = glob.glob(f"{base_dir}/*/subagent.py")
    
    standard_count = 0
    capm_count = 0
    external_count = 0
    skipped_count = 0
    
    for file_path in subagent_files:
        db_name = os.path.basename(os.path.dirname(file_path))
        
        if db_name in STANDARD_INTERNAL:
            if update_standard_subagent(file_path):
                standard_count += 1
            else:
                skipped_count += 1
        elif db_name in CAPM_LIKE:
            if update_capm_subagent(file_path):
                capm_count += 1
            else:
                skipped_count += 1
        elif db_name in EXTERNAL:
            if update_external_subagent(file_path):
                external_count += 1
            else:
                skipped_count += 1
        else:
            logger.warning(f"Unknown subagent type: {db_name}")
            skipped_count += 1
    
    logger.info(f"Updated {standard_count} standard internal subagents")
    logger.info(f"Updated {capm_count} CAPM-like subagents")
    logger.info(f"Updated {external_count} external subagents")
    logger.info(f"Skipped {skipped_count} subagents")

if __name__ == "__main__":
    main()