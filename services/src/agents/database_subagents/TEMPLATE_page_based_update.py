# Template for updating internal_x subagents to page-based research approach
# This template shows the key changes needed for each internal_x subagent

"""
SUMMARY OF CHANGES NEEDED FOR EACH INTERNAL_X SUBAGENT:

1. Update tool schema (replace SYNTHESIS_TOOL_SCHEMA)
2. Update format_documents_for_llm to sort by page_number
3. Add process_single_document function for parallel processing
4. Replace synthesize_response_and_status with new version
5. Update query_database_sync to return new structure
6. Update content_synthesis_prompt.py file
7. Remove build_structured_reference_index function if present

Below are the key code snippets to use:
"""

# 1. NEW TOOL SCHEMA (replace existing SYNTHESIS_TOOL_SCHEMA)
SYNTHESIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "extract_page_based_research",
        "description": "Extracts research findings from a document on a per-page basis, providing detailed research for each relevant page.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_summary": {
                    "type": "string",
                    "description": "Concise status summary indicating overall document relevance (e.g., '✅ Found relevant info on 3 pages.', '📄 No relevant info found.').",
                },
                "page_research": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "page_number": {
                                "type": "integer",
                                "description": "The page number containing relevant information."
                            },
                            "research_content": {
                                "type": "string",
                                "description": "Detailed research findings extracted from this specific page. Use markdown formatting."
                            }
                        },
                        "required": ["page_number", "research_content"]
                    },
                    "description": "Array of research findings organized by page number. Only include pages with relevant information."
                }
            },
            "required": ["status_summary", "page_research"]
        },
    },
}

# 2. NEW FORMAT_DOCUMENTS_FOR_LLM FUNCTION
def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
    Reconstructs documents from page records in correct order with clear page markers.
    """
    formatted_docs = ""
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"

        # Get page_sections and sort by page_number
        page_sections = doc.get("page_sections", [])
        if not page_sections:
            formatted_docs += "No content available.\n\n"
            continue

        # Sort pages by page_number for proper document reconstruction
        sorted_pages = sorted(page_sections, key=lambda x: x.get("page_number", 0))

        # Process each page
        for section in sorted_pages:
            page_number = section.get("page_number", 0)
            section_summary = section.get("section_summary", f"Page {page_number}")
            section_content = section.get("section_content", "No content available")

            # Create clear page header for LLM understanding
            formatted_docs += f"## {section_summary}\n\n"
            formatted_docs += f"**PAGE {page_number}**\n\n"
            formatted_docs += f"{section_content}\n\n"
            formatted_docs += "---\n\n"

    return formatted_docs.strip()

# 3. NEW PROCESS_SINGLE_DOCUMENT FUNCTION (add this new function)
def process_single_document(
    query: str,
    document: Dict[str, Any],
    token: Optional[str] = None,
    database_name: str = "internal_[SUBAGENT_NAME]",  # UPDATE THIS
    process_monitor=None,
    stage_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a single document and return page-based research findings.
    This function is called in parallel for each document.
    """
    doc_name = document.get("document_name", "Unknown Document")
    logger.info(f"Processing single [SUBAGENT_NAME] document: {doc_name}")
    
    # Get file link from document metadata
    file_link = ""
    if "file_link" in document:
        file_link = document.get("file_link", "")
    
    # Format single document for LLM
    formatted_doc = format_documents_for_llm([document])
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_doc)
    
    try:
        logger.info(f"Initiating [SUBAGENT_NAME] Single Document Synthesis API call for {doc_name}")
        synthesis_response_obj, synthesis_usage = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=1500,
            temperature=0.2,
            token=token,
            database_name=f"{database_name}_{doc_name}",
            tools=[SYNTHESIS_TOOL_SCHEMA],
            tool_choice={
                "type": "function",
                "function": {"name": SYNTHESIS_TOOL_SCHEMA["function"]["name"]},
            },
        )

        # Track token usage
        if synthesis_usage:
            logger.debug(f"Single document synthesis usage for {doc_name}: {synthesis_usage}")
            if process_monitor and stage_name:
                process_monitor.add_llm_call_details_to_stage(stage_name, synthesis_usage)

        # Check for errors
        if isinstance(synthesis_response_obj, str) and synthesis_response_obj.startswith("Error:"):
            logger.error(f"get_completion failed for {doc_name}: {synthesis_response_obj}")
            return {
                "document_name": doc_name,
                "file_link": file_link,
                "status_summary": f"❌ Error processing {doc_name}.",
                "page_research": [],
            }

        # Process Tool Call Response
        if (
            hasattr(synthesis_response_obj, "choices")
            and synthesis_response_obj.choices
            and hasattr(synthesis_response_obj.choices[0], "message")
            and synthesis_response_obj.choices[0].message
            and hasattr(synthesis_response_obj.choices[0].message, "tool_calls")
            and synthesis_response_obj.choices[0].message.tool_calls
        ):
            tool_call = synthesis_response_obj.choices[0].message.tool_calls[0]
            if tool_call.function.name == SYNTHESIS_TOOL_SCHEMA["function"]["name"]:
                arguments_str = tool_call.function.arguments
                try:
                    arguments = json.loads(arguments_str)
                    required_keys = ["status_summary", "page_research"]
                    if all(key in arguments for key in required_keys):
                        return {
                            "document_name": doc_name,
                            "file_link": file_link,
                            "status_summary": arguments.get("status_summary", ""),
                            "page_research": arguments.get("page_research", []),
                        }
                    else:
                        logger.error(f"Missing required keys in tool arguments for {doc_name}")
                        return {
                            "document_name": doc_name,
                            "file_link": file_link,
                            "status_summary": f"❌ Missing required keys for {doc_name}.",
                            "page_research": [],
                        }
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse tool arguments JSON for {doc_name}: {json_err}")
                    return {
                        "document_name": doc_name,
                        "file_link": file_link,
                        "status_summary": f"❌ JSON decode error for {doc_name}.",
                        "page_research": [],
                    }
            else:
                logger.error(f"Unexpected tool called for {doc_name}: {tool_call.function.name}")
                return {
                    "document_name": doc_name,
                    "file_link": file_link,
                    "status_summary": f"❌ Unexpected tool for {doc_name}.",
                    "page_research": [],
                }
        else:
            logger.error(f"No tool call received for {doc_name} synthesis")
            return {
                "document_name": doc_name,
                "file_link": file_link,
                "status_summary": f"❌ No tool call for {doc_name}.",
                "page_research": [],
            }

    except Exception as e:
        logger.error(f"Exception during synthesis for {doc_name}: {str(e)}", exc_info=True)
        return {
            "document_name": doc_name,
            "file_link": file_link,
            "status_summary": f"❌ Exception processing {doc_name}.",
            "page_research": [],
        }

# 4. NEW SYNTHESIZE_RESPONSE_AND_STATUS FUNCTION
def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]],
    file_links: List[FileLink],
    token: Optional[str] = None,
    database_name: str = "internal_[SUBAGENT_NAME]",  # UPDATE THIS
    process_monitor=None,
    stage_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process each document in parallel, then return structured page-based research.
    Returns a dictionary with document names as keys, containing page-based research.
    """
    logger.info(f"Synthesizing response for {len(documents)} [SUBAGENT_NAME] documents using parallel processing")
    
    if not documents:
        logger.warning(f"No documents provided for {database_name} synthesis.")
        return {}

    # Create file link mapping
    file_link_map = {}
    for link_info in file_links:
        doc_name = link_info.get("document_name", "")
        file_link = link_info.get("file_link", "")
        if doc_name:
            file_link_map[doc_name] = file_link

    # Add file links to documents before processing
    for doc in documents:
        doc_name = doc.get("document_name", "")
        if doc_name in file_link_map:
            doc["file_link"] = file_link_map[doc_name]

    # Process documents in parallel using ThreadPoolExecutor
    document_results = []
    with ThreadPoolExecutor(max_workers=min(len(documents), 5)) as executor:
        # Submit all document processing jobs
        future_to_doc = {
            executor.submit(
                process_single_document,
                query,
                doc,
                token,
                database_name,
                process_monitor,
                stage_name,
            ): doc
            for doc in documents
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                result = future.result()
                document_results.append(result)
                logger.info(f"Completed processing for document: {result.get('document_name')}")
            except Exception as e:
                doc_name = doc.get("document_name", "Unknown")
                logger.error(f"Exception processing document {doc_name}: {str(e)}")
                document_results.append({
                    "document_name": doc_name,
                    "file_link": file_link_map.get(doc_name, ""),
                    "status_summary": f"❌ Exception processing {doc_name}.",
                    "page_research": [],
                })

    # Build structured output: document -> page -> research
    structured_output = {}
    
    for result in document_results:
        doc_name = result.get("document_name", "Unknown Document")
        file_link = result.get("file_link", "")
        page_research = result.get("page_research", [])
        
        # Only include documents with actual research findings
        if page_research and not result["status_summary"].startswith("❌"):
            doc_output = {}
            
            for page_item in page_research:
                page_number = page_item.get("page_number", 0)
                research_content = page_item.get("research_content", "")
                
                # Create page key (e.g., "page_3")
                page_key = f"page_{page_number}"
                
                doc_output[page_key] = {
                    "research_content": research_content,
                    "file_link": file_link,
                    "page_number": page_number
                }
            
            if doc_output:  # Only add document if it has page research
                structured_output[doc_name] = doc_output

    logger.info(f"Structured output contains research from {len(structured_output)} documents")
    return structured_output

# 5. UPDATED QUERY_DATABASE_SYNC - Research scope section
# Replace the "elif scope == 'research':" section with:

        elif scope == "research":
            # Collect file links from catalog before fetching content
            file_links = []
            for item in catalog:
                if item.get("id") in selected_doc_ids:
                    file_link_value = item.get("file_link", "")
                    doc_name_value = item.get("document_name", "Unknown")
                    file_links.append(
                        {
                            "file_link": file_link_value,
                            "document_name": doc_name_value,
                        }
                    )

            # Fetch content and synthesize using parallel processing
            documents = fetch_document_content(selected_doc_ids)
            logger.info(
                f"Retrieved content for {len(documents)} [SUBAGENT_NAME] documents for research."
            )

            # Get research synthesis using new page-based parallel processing
            # This now returns structured output: {doc_name: {page_x: {research_content, file_link}}}
            research_result = synthesize_response_and_status(
                query, documents, file_links, token, database_name, process_monitor, stage_name
            )

            # For backward compatibility, create a response in the expected format
            # The new structure will be passed through reference_index for downstream processing
            
            # Create status summary based on results
            if research_result:
                doc_count = len(research_result)
                total_pages = sum(len(doc_data) for doc_data in research_result.values())
                status_summary = f"✅ Found relevant information in {doc_count} document(s) across {total_pages} page(s)."
            else:
                status_summary = "📄 No relevant information found in [SUBAGENT_NAME] documents."

            # Create a simplified detailed_research for backward compatibility
            detailed_research = f"# [SUBAGENT_NAME] Research Results\n\n*Query: {query}*\n\n"
            if research_result:
                detailed_research += f"Found relevant information in {len(research_result)} document(s).\n\n"
                for doc_name, doc_data in research_result.items():
                    page_count = len(doc_data)
                    detailed_research += f"- **{doc_name}**: {page_count} relevant page(s)\n"
            else:
                detailed_research += "No relevant information found in the selected documents.\n"

            # Build the response in the expected format
            response = {
                "detailed_research": detailed_research.strip(),
                "status_summary": status_summary,
            }

            # The structured research_result will be passed as reference_index
            # This maintains backward compatibility while providing the new structure
            reference_index = research_result

            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name,
                    result_count=len(documents),
                    document_ids=selected_doc_ids,
                    status_summary=status_summary,
                )

            logger.info(f"Returning research results with {len(research_result)} documents")

            # Return with new structure in reference_index position
            return (
                response,
                selected_doc_ids,
                file_links,
                None,  # page_section_refs no longer needed
                None,  # section_content_map no longer needed
                reference_index,  # This now contains the structured research output
            )

# 6. REMEMBER TO UPDATE THE content_synthesis_prompt.py FILE AS WELL!
# Key changes for content_synthesis_prompt.py:
# - Update SUBAGENT_OBJECTIVE to focus on page-based extraction
# - Update SUBAGENT_RESPONSE_FORMAT to use extract_page_based_research tool
# - Update instructions to process pages individually
# - Change tool name from synthesize_research_findings to extract_page_based_research