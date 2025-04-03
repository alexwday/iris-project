# internal_wiki/subagent.py
"""
Internal Wiki Subagent

This module handles queries to the Internal Wiki database, including catalog retrieval,
document selection, content retrieval, and response synthesis.

Functions:
    query_database: Query the Internal Wiki database
"""

import json
import logging
import time
import re
from typing import Dict, List, Any, Optional, Union, Generator, cast

from ....initial_setup.db_config import connect_to_db

from .catalog_selection_prompt import get_catalog_selection_prompt
from .content_synthesis_prompt import get_content_synthesis_prompt
from ....llm_connectors.rbc_openai import call_llm
from ....chat_model.model_settings import get_model_config

# Get module logger
logger = logging.getLogger(__name__)


def format_catalog_for_llm(catalog_records: List[Dict[str, Any]]) -> str:
    """
    Format the catalog records into a string that is optimized for LLM comprehension.
    
    Args:
        catalog_records (List[Dict[str, Any]]): List of catalog records from the database
        
    Returns:
        str: Formatted catalog text
    """
    formatted_catalog = ""
    
    for record in catalog_records:
        doc_id = record.get("id", "unknown")
        doc_name = record.get("document_name", "Untitled")
        doc_desc = record.get("document_description", "No description available")
        
        formatted_catalog += f"Document ID: {doc_id}\n"
        formatted_catalog += f"Document Name: {doc_name}\n"
        formatted_catalog += f"Document Description: {doc_desc}\n\n"
    
    return formatted_catalog.strip()


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
    
    Args:
        documents (List[Dict[str, Any]]): List of document records from the database
        
    Returns:
        str: Formatted documents text
    """
    formatted_docs = ""
    
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"
        
        # Process each section
        sections = doc.get("sections", [])
        for section in sections:
            section_name = section.get("section_name", "Untitled Section")
            section_content = section.get("section_content", "No content available")
            
            formatted_docs += f"## {section_name}\n\n"
            formatted_docs += f"{section_content}\n\n"
        
        formatted_docs += "---\n\n"
    
    return formatted_docs.strip()


def fetch_wiki_catalog(query: str) -> List[Dict[str, Any]]:
    """
    Fetch and filter the internal wiki catalog from the database.
    
    Args:
        query (str): The search query to help filter relevant documents
        
    Returns:
        List[Dict[str, Any]]: List of catalog records
    """
    logger.info(f"Fetching wiki catalog with query: {query}")
    
    # Connect to database
    conn = connect_to_db("local")
    catalog_records: List[Dict[str, Any]] = []
    
    if not conn:
        logger.error("Failed to connect to database")
        return catalog_records
    
    try:
        # Create SQL query to get catalog entries for internal_wiki
        # Note: In a production environment, you might want to add more sophisticated 
        # text search capabilities like full-text search or fuzzy matching
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, document_name, document_description 
                FROM apg_catalog 
                WHERE document_source = 'internal_wiki'
            """)
            
            for row in cur.fetchall():
                catalog_records.append({
                    "id": str(row[0]),  # Convert ID to string for consistency
                    "document_name": row[1],
                    "document_description": row[2]
                })
                
        logger.info(f"Retrieved {len(catalog_records)} catalog entries from database")
    except Exception as e:
        logger.error(f"Error fetching catalog from database: {str(e)}")
    finally:
        conn.close()
    
    return catalog_records


def fetch_document_content(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch the content of specified documents from the database.
    
    Args:
        doc_ids (List[str]): List of document IDs to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of document records with content
    """
    logger.info(f"Fetching content for documents: {doc_ids}")
    
    # Convert string IDs to integers if needed (our database uses integer IDs)
    # Also handle any non-numeric IDs gracefully
    numeric_ids = []
    for doc_id in doc_ids:
        try:
            numeric_ids.append(int(doc_id))
        except ValueError:
            logger.warning(f"Skipping non-numeric ID: {doc_id}")
    
    if not numeric_ids:
        logger.warning("No valid document IDs to fetch")
        return []
    
    # Connect to database
    conn = connect_to_db("local")
    result: List[Dict[str, Any]] = []
    
    if not conn:
        logger.error("Failed to connect to database")
        return result
    
    try:
        # First, get the document names for all requested IDs from the catalog
        doc_names = {}
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(numeric_ids))
            cur.execute(f"""
                SELECT id, document_name 
                FROM apg_catalog 
                WHERE id IN ({placeholders})
                AND document_source = 'internal_wiki'
            """, numeric_ids)
            
            for row in cur.fetchall():
                doc_names[row[0]] = row[1]
        
        # Then, for each document, get its content sections
        for doc_id, doc_name in doc_names.items():
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT section_id, section_name, section_content 
                    FROM apg_content 
                    WHERE document_source = 'internal_wiki'
                    AND document_name = %s
                    ORDER BY section_id
                """, (doc_name,))
                
                sections = []
                for row in cur.fetchall():
                    sections.append({
                        "section_name": row[1] if row[1] else f"Section {row[0]}",
                        "section_content": row[2]
                    })
                
                if sections:
                    result.append({
                        "document_name": doc_name,
                        "sections": sections
                    })
                
        logger.info(f"Retrieved content for {len(result)} documents from database")
    except Exception as e:
        logger.error(f"Error fetching document content from database: {str(e)}")
    finally:
        conn.close()
    
    return result


def get_completion(capability: str, prompt: str, max_tokens: int = 1000,
                  temperature: float = 0.7, token: Optional[str] = None, 
                  stream: bool = False) -> Union[str, Generator[str, None, None]]:
    """
    Helper function to get a completion from the LLM, either as full response or streaming chunks.
    
    Args:
        capability (str): Model capability ("small" or "large")
        prompt (str): The prompt to send to the model
        max_tokens (int, optional): Maximum tokens for completion. Defaults to 1000.
        temperature (float, optional): Temperature parameter. Defaults to 0.7.
        token (str, optional): OAuth token for API access. Defaults to None.
        stream (bool, optional): Whether to stream the response. Defaults to False.
        
    Returns:
        Union[str, Generator[str, None, None]]: The model's response as string or generator of chunks
    """
    # Type declaration that ensures mypy understands return type correctly
    response_value: Union[str, Generator[str, None, None]]
    # Get the model configuration based on capability and environment
    model_config = get_model_config(capability)
    model_name = model_config["name"]
    prompt_cost = model_config["prompt_token_cost"]
    completion_cost = model_config["completion_token_cost"]
    
    # Call the OpenAI API
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    
    # If streaming is requested, return chunks as they come
    if stream:
        # Define a generator to yield chunks
        def response_generator():
            response = call_llm(
                oauth_token=token or "placeholder_token",
                prompt_token_cost=prompt_cost,
                completion_token_cost=completion_cost,
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True  # Enable streaming
            )
            
            # Iterate through streaming response chunks
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
            
        response_value = response_generator()
        return response_value
    
    # For non-streaming mode, return the full response
    else:
        response = call_llm(
            oauth_token=token or "placeholder_token",
            prompt_token_cost=prompt_cost,
            completion_token_cost=completion_cost,
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False
        )
        
        # Extract the text content from the response
        response_value = response.choices[0].message.content.strip()
        return response_value


def select_relevant_documents(query: str, catalog: List[Dict[str, Any]], 
                              token: Optional[str] = None) -> List[str]:
    """
    Use an LLM to select the most relevant documents from the catalog based on the query.
    
    Args:
        query (str): The search query
        catalog (List[Dict[str, Any]]): List of catalog records
        token (str, optional): Authentication token for API access
        
    Returns:
        List[str]: List of selected document IDs
    """
    logger.info("Selecting relevant documents from catalog")
    
    # Format the catalog for the LLM
    formatted_catalog = format_catalog_for_llm(catalog)
    
    # Create the prompt for document selection
    selection_prompt = get_catalog_selection_prompt(query, formatted_catalog)
    
    # Call the LLM to select relevant documents - use non-streaming mode for this step
    try:
        # For document selection we always use non-streaming mode (stream=False)
        # to get a complete response for JSON parsing
        response = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=200,
            token=token,
            stream=False  # Explicitly use non-streaming
        )
        
        # Cast response to string for mypy
        response_str = cast(str, response)
        
        # Parse the response to extract document IDs
        try:
            selected_ids = json.loads(response_str)
            logger.info(f"Selected document IDs: {selected_ids}")
            return selected_ids
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON, attempting fallback extraction")
            # Fallback: Try to extract IDs using string manipulation
            import re
            matches = re.findall(r'"([^"]+)"', response_str)
            if matches:
                logger.warning(f"Extracted document IDs using fallback method: {matches}")
                return matches
            logger.error("Could not extract document IDs from response")
            return []
    
    except Exception as e:
        logger.error(f"Error in document selection: {str(e)}")
        return []


def synthesize_response(query: str, documents: List[Dict[str, Any]], 
                       token: Optional[str] = None,
                       stream: bool = False) -> Union[str, Generator[str, None, None]]:
    """
    Use an LLM to synthesize a response from the document content.
    
    Args:
        query (str): The search query
        documents (List[Dict[str, Any]]): List of document records with content
        token (str, optional): Authentication token for API access
        stream (bool, optional): Whether to stream the response. Defaults to False.
        
    Returns:
        Union[str, Generator[str, None, None]]: Either full response or generator of response chunks
    """
    logger.info("Synthesizing response from document content")
    
    if not documents:
        error_msg = "No relevant information found in the internal wiki. Please try refining your query or check other databases."
        if stream:
            # For streaming mode, return a generator that yields the error message
            def error_generator():
                yield error_msg
            return error_generator()
        else:
            return error_msg
    
    # Format the documents for the LLM
    formatted_documents = format_documents_for_llm(documents)
    
    # Create the prompt for response synthesis
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_documents)
    
    # Call the LLM to synthesize a response
    try:
        return get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=1500,
            temperature=0.3,  # Lower temperature for more focused synthesis
            token=token,
            stream=stream  # Pass through the stream parameter
        )
    
    except Exception as e:
        error_msg = f"Error synthesizing response from internal wiki documents: {str(e)}"
        logger.error(error_msg)
        
        if stream:
            # For streaming mode, return a generator that yields the error message
            def error_generator():
                yield error_msg
            return error_generator()
        else:
            return error_msg


def query_database(query: str, token: Optional[str] = None) -> Union[str, Generator[str, None, None]]:
    """
    Query the Internal Wiki database.
    
    This function implements the full pipeline for querying the internal wiki:
    1. Fetch and filter the wiki catalog
    2. Select relevant documents using an LLM
    3. Fetch the content of selected documents
    4. Synthesize a response from the document content
    
    Args:
        query (str): Search query for the database
        token (str, optional): Authentication token for API access
            
    Returns:
        Union[str, Generator[str, None, None]]: Query results from the wiki database,
        returned as a streaming generator for integration with model.py's streaming output
    """
    logger.info(f"Querying Internal Wiki database: {query}")
    
    # This outer function always returns a generator for streaming
    # model.py expectation is to get chunks it can yield
    def response_generator():
        try:
            # Start without a header, let the content speak for itself
            # No header to yield here
            
            # Step 1: Fetch and filter the catalog
            catalog = fetch_wiki_catalog(query)
            logger.info(f"Retrieved {len(catalog)} catalog entries")
            
            if not catalog:
                yield "No documents found in the Internal Wiki database. Please try a different query or another database."
                return
            
            # Step 2: Select relevant documents using LLM (non-streaming for tool calls)
            doc_ids = select_relevant_documents(query, catalog, token)
            logger.info(f"Selected {len(doc_ids)} relevant documents")
            
            if not doc_ids:
                yield "No relevant documents found in the Internal Wiki database. Please try refining your query or check other databases."
                return
            
            # Step 3: Fetch the content of selected documents
            documents = fetch_document_content(doc_ids)
            logger.info(f"Retrieved content for {len(documents)} documents")
            
            # Step 4: Synthesize a response from the document content (streaming)
            response_stream = synthesize_response(query, documents, token, stream=True)
            
            # Pass through all chunks from the synthesize_response generator
            for chunk in response_stream:
                yield chunk
                
        except Exception as e:
            error_msg = f"Error querying Internal Wiki database: {str(e)}"
            logger.error(error_msg)
            yield error_msg
    
    # Return the generator
    return response_generator()