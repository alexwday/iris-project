# File Search Linking and 25-Document Limit Implementation Guide

## Overview
This guide documents the implementation of two key improvements to the IRIS file search system:
1. **Linking System**: Add clickable PDF links to file search results
2. **25-Document Limit**: Increase file search limit from 5 to 25 documents

## Implementation Status
- [x] Change 1: Add linking system for file search results
- [x] Change 2: Create new metadata YAML configuration
- [x] Change 3: Update load_catalog_selection_config function
- [x] Change 4: Update get_catalog_selection_prompt function
- [x] Change 5: Update select_relevant_documents function call
- [x] Change 6: Increase similarity search limit for metadata

---

## Change 1: Add Linking System for File Search Results

### File Location
`/Users/alexwday/Projects/iris-project/services/src/chat_model/model.py`

### Purpose
Enable clickable PDF links in file search results so users can directly open documents from the search results, similar to the existing functionality in research mode.

### Reason for Change
Currently, file search (metadata scope) returns plain text results without clickable links, even though all necessary data (file_name, file_link) is available. Users cannot easily access the documents found in their search.

### Original Code (Lines 1578-1605)
```python
                    yield f"\n\nCompleted metadata search across {len(selected_databases)} databases. Found {unique_item_count} unique relevant items:\n"
                    seen_documents: Dict[str, Dict[str, Any]] = {}
                    for db_name, items_list in metadata_results_by_db.items():
                        db_display_name = available_databases.get(db_name, {}).get(
                            "name", db_name
                        )
                        yield f"\n**{db_display_name}:**\n"
                        if items_list:
                            seen_documents.setdefault(db_name, set())
                            displayed_items = 0
                            for item in items_list:
                                if isinstance(item, dict) and "error" in item:
                                    yield f"- Error: {item['error']}\n"
                                    displayed_items += 1
                                else:
                                    doc_name = item.get("document_name", "Unknown")
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name)
                                    doc_desc = item.get(
                                        "document_description", "No description"
                                    )
                                    yield f"- **{doc_name}:** {doc_desc}\n"
                                    displayed_items += 1
                            if displayed_items == 0:
                                yield "- No unique items found.\n"
                        else:
                            yield "- No relevant items found.\n"
```

### New Code (Implemented)
```python
                    yield f"\n\nCompleted metadata search across {len(selected_databases)} databases. Found {unique_item_count} unique relevant items:\n"
                    seen_documents: Dict[str, Dict[str, Any]] = {}
                    for db_name, items_list in metadata_results_by_db.items():
                        db_display_name = available_databases.get(db_name, {}).get(
                            "name", db_name
                        )
                        yield f"\n**{db_display_name}:**\n"
                        if items_list:
                            seen_documents.setdefault(db_name, set())
                            displayed_items = 0
                            for item in items_list:
                                if isinstance(item, dict) and "error" in item:
                                    yield f"- Error: {item['error']}\n"
                                    displayed_items += 1
                                else:
                                    doc_name = item.get("document_name", "Unknown")
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name)
                                    doc_desc = item.get(
                                        "document_description", "No description"
                                    )
                                    # NEW: Generate clickable PDF link if file_name is available
                                    file_name = item.get("file_name", "")
                                    if file_name:
                                        # NEW: Construct S3 URL using config base path
                                        s3_url = f"{config.S3_BASE_PATH}/{file_name}"
                                        # NEW: Create clickable href with JavaScript PDF opener (page 1, no highlight)
                                        href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", 1, "")\'>{doc_name}</a>'
                                        yield f"- {href}: {doc_desc}\n"
                                    else:
                                        # FALLBACK: Keep original format if no file_name available
                                        yield f"- **{doc_name}:** {doc_desc}\n"
                                    displayed_items += 1
                            if displayed_items == 0:
                                yield "- No unique items found.\n"
                        else:
                            yield "- No relevant items found.\n"
```

---

## Change 2: Create New Metadata YAML Configuration

### File Location
`/Users/alexwday/Projects/iris-project/services/src/agents/database_subagents/catalog_search/catalog_selection_prompt_metadata.yaml`

### Purpose
Provide a separate configuration for file search (metadata scope) that allows selection of up to 25 documents instead of 5.

### Reason for Change
File search needs different selection criteria than research mode. Users expect comprehensive file listings, not just the top 5 most relevant documents.

### Implementation (Completed)
Created new file `catalog_selection_prompt_metadata.yaml` with:
- Line 25: Changed to "Select up to 25 most relevant documents for comprehensive results"
- Line 82: Changed to "Maximum 25 documents"
- Line 104: Changed to "Return a maximum of 25 document IDs"
- Modified relevance thresholds to be more inclusive for file search
- Updated examples to show larger result sets (15-20 documents)

---

## Change 3: Update load_catalog_selection_config Function

### File Location
`/Users/alexwday/Projects/iris-project/services/src/agents/database_subagents/catalog_search/subagent.py`

### Purpose
Enable loading different YAML configurations based on query scope (metadata vs research).

### Reason for Change
To support separate document limits and selection criteria for file search vs research modes.

### Original Code (Lines 234-260)
```python
def load_catalog_selection_config():
    """
    Load catalog selection configuration from YAML file.

    Returns:
        dict: Configuration with resolved system prompt and settings
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "catalog_selection_prompt.yaml")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception(
                "No system_prompt found in catalog selection YAML configuration"
            )

        # No context replacement needed for catalog selection (minimal context)
        return yaml_config

    except Exception as e:
        logger.error(f"Failed to load catalog selection YAML config: {str(e)}")
        raise
```

### New Code (Implemented)
```python
def load_catalog_selection_config(scope: str = "research"):
    """
    Load catalog selection configuration from YAML file.

    Args:
        scope: The query scope ('metadata' or 'research')

    Returns:
        dict: Configuration with resolved system prompt and settings
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # NEW: Use different YAML file for metadata scope
        if scope == "metadata":
            yaml_filename = "catalog_selection_prompt_metadata.yaml"
        else:
            yaml_filename = "catalog_selection_prompt.yaml"
        yaml_path = os.path.join(current_dir, yaml_filename)

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception(
                f"No system_prompt found in catalog selection YAML configuration ({yaml_filename})"
            )

        # No context replacement needed for catalog selection (minimal context)
        return yaml_config

    except Exception as e:
        logger.error(f"Failed to load catalog selection YAML config: {str(e)}")
        raise
```

---

## Change 4: Update get_catalog_selection_prompt Function

### File Location
`/Users/alexwday/Projects/iris-project/services/src/agents/database_subagents/catalog_search/subagent.py`

### Purpose
Pass the scope parameter through to load the appropriate YAML configuration.

### Reason for Change
The function needs to know which configuration to load based on whether it's handling a file search or research query.

### Original Code (Lines 292-310)
```python
def get_catalog_selection_prompt(query: str, formatted_catalog: str) -> str:
    """
    Generate a prompt for selecting relevant documents from an internal catalog using YAML config.

    Args:
        query (str): The research statement (query)
        formatted_catalog (str): The formatted catalog of internal documents

    Returns:
        str: The formatted prompt for the LLM
    """
    config = load_catalog_selection_config()
    system_prompt = config.get("system_prompt", "")

    # Replace template variables
    system_prompt = system_prompt.replace("{{query}}", query)
    system_prompt = system_prompt.replace("{{formatted_catalog}}", formatted_catalog)

    return system_prompt
```

### New Code (Implemented)
```python
def get_catalog_selection_prompt(query: str, formatted_catalog: str, scope: str = "research") -> str:
    """
    Generate a prompt for selecting relevant documents from an internal catalog using YAML config.

    Args:
        query (str): The research statement (query)
        formatted_catalog (str): The formatted catalog of internal documents
        scope (str): The query scope ('metadata' or 'research')

    Returns:
        str: The formatted prompt for the LLM
    """
    # NEW: Pass scope to load appropriate configuration
    config = load_catalog_selection_config(scope)
    system_prompt = config.get("system_prompt", "")

    # Replace template variables
    system_prompt = system_prompt.replace("{{query}}", query)
    system_prompt = system_prompt.replace("{{formatted_catalog}}", formatted_catalog)

    return system_prompt
```

---

## Change 5: Update select_relevant_documents Function Call

### File Location
`/Users/alexwday/Projects/iris-project/services/src/agents/database_subagents/catalog_search/subagent.py`

### Purpose
Pass the scope parameter to get_catalog_selection_prompt.

### Reason for Change
The prompt generation function needs the scope to select the appropriate configuration.

### Original Code (Lines 706-710)
```python
    logger.info(f"Selecting relevant documents from {database_name} catalog")
    formatted_catalog = format_catalog_for_llm(catalog, scope=scope)
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog
    )  # Assumes this prompt asks for JSON list
```

### New Code (Implemented)
```python
    logger.info(f"Selecting relevant documents from {database_name} catalog")
    formatted_catalog = format_catalog_for_llm(catalog, scope=scope)
    # NEW: Pass scope parameter to get appropriate prompt for metadata vs research
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog, scope
    )  # Pass scope to get appropriate prompt
```

---

## Change 6: Increase Similarity Search Limit for Metadata

### File Location
`/Users/alexwday/Projects/iris-project/services/src/agents/database_subagents/catalog_search/subagent.py`

### Purpose
Provide more candidate documents for the LLM to select from when performing file searches.

### Reason for Change
With a 25-document limit, the similarity search should return more candidates (30) to give the LLM sufficient choices.

### Original Code (Lines 1145-1152)
```python
        if research_statement:
            logger.info(f"Using similarity filtering with research statement for {document_source}")
            catalog = fetch_catalog_with_similarity_filter(
                document_source=document_source,
                research_statement=research_statement,
                token=token,
                top_k=10  # Limit to top 10 most similar documents
            )
```

### New Code (Implemented)
```python
        if research_statement:
            logger.info(f"Using similarity filtering with research statement for {document_source}")
            # NEW: Use higher limit for metadata scope to give LLM more choices
            similarity_top_k = 30 if scope == "metadata" else 10
            catalog = fetch_catalog_with_similarity_filter(
                document_source=document_source,
                research_statement=research_statement,
                token=token,
                top_k=similarity_top_k  # More documents for metadata mode
            )
```

---

## Testing Recommendations

1. **File Search Linking Test**
   - Perform a file search query
   - Verify that document names appear as clickable links
   - Click a link and confirm it opens the correct PDF

2. **25-Document Limit Test**
   - Run a broad file search query
   - Verify up to 25 documents are returned (not limited to 5)
   - Confirm research mode still returns maximum 5 documents

3. **Regression Testing**
   - Verify research mode functionality unchanged
   - Test error handling with missing file_name data
   - Confirm performance with larger result sets

## Implementation Notes
- All changes maintain backward compatibility
- Default parameters ensure existing code paths work unchanged
- Graceful degradation when file_name data is missing