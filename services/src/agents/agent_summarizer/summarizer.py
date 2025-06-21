# services/src/agents/agent_summarizer/summarizer.py
"""
Summarizer Agent Module (Async Version)

This module is responsible for generating the final research summary based on
the aggregated detailed research findings from various databases.

Functions:
    generate_streaming_summary: Asynchronously generates a streaming summary.

Dependencies:
    - logging
    - OpenAI connector for LLM calls
    - Typing for annotations
"""

import logging
import json
import os
import yaml
from typing import Any, Dict, List, Optional, Union, Generator

from ...initial_setup.env_config import config
from ...llm_connectors.rbc_openai import call_llm
from ...global_prompts.project_statement import get_project_statement
from ...global_prompts.fiscal_statement import get_fiscal_statement
from ...global_prompts.restrictions_statement import get_restrictions_statement

# Get module logger
logger = logging.getLogger(__name__)


class SummarizerError(Exception):
    """Base exception class for summarizer-related errors."""

    pass


def load_agent_config():
    """
    Load agent configuration from YAML file and resolve dynamic context.
    NOTE: Summarizer excludes database_statement (unlike other agents)

    Returns:
        dict: Configuration dictionary with resolved system prompt and settings
    """
    try:
        # Build context statements dynamically (excluding database_statement)
        context_parts = [
            get_project_statement(),
            get_fiscal_statement(),
            get_restrictions_statement(),  # Note: NO database_statement for summarizer
        ]

        # Build the complete context block
        context_block = "\n\n".join(context_parts)

        # Read and parse the YAML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "summarizer_prompt.yaml")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract model configuration from YAML
        model_config = yaml_config.get("model", {})
        capability = model_config.get("capability", "large")  # Default fallback
        max_tokens = model_config.get("max_tokens", 4096)
        temperature = model_config.get("temperature", 0.1)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception("No system_prompt found in YAML configuration")

        # Replace the context placeholder
        system_prompt = system_prompt.replace(
            "{{CONTEXT_START}}", f"<CONTEXT>\n{context_block}\n</CONTEXT>"
        )

        return {
            "model_capability": capability,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system_prompt": system_prompt,
        }

    except Exception as e:
        logger.error(f"Error loading agent configuration: {str(e)}", exc_info=True)
        raise SummarizerError(f"Failed to load agent configuration: {str(e)}") from e


# Load configuration once at module level
try:
    _config = load_agent_config()
    MODEL_CAPABILITY = _config["model_capability"]
    MAX_TOKENS = _config["max_tokens"]
    TEMPERATURE = _config["temperature"]
    SYSTEM_PROMPT = _config["system_prompt"]


except Exception as e:
    logger.error(
        f"Failed to initialize summarizer agent from YAML: {str(e)}", exc_info=True
    )
    raise


# --- Main Synchronous Summarizer Function ---
def generate_streaming_summary(
    aggregated_detailed_research: Dict[
        str, str
    ],  # Input is now Dict[db_name, detailed_research_string]
    scope: str,  # Keep scope for potential future variations
    token: Optional[str],
    available_databases: Dict[
        str, Any
    ],  # Available database configurations (filtered by user selection)
    research_statement: Optional[str] = None,  # Added research statement for query focus
    original_query_plan: Optional[Dict] = None,
    reference_index: Optional[
        Dict[str, Dict[str, Any]]
    ] = None,  # Added reference index
) -> Generator[Any, None, None]:  # Yields str or dict
    """
    Generate the final response based on aggregated detailed research.

    Yields content chunks (str) and finally a dictionary containing usage details:
    {'usage_details': {'model': str, ...}}

    Currently focuses on 'research' scope, generating a streaming summary using an LLM.
    The 'metadata' scope handling is simplified as metadata is now handled
    differently in the main model flow.

    Args:
        aggregated_detailed_research (dict): Dictionary keyed by database name (str),
                                             containing the detailed research string for each.
        scope (str): The scope of the original request ('research' primarily).
        token (str): Authentication token for API access.
        original_query_plan (dict, optional): The original query plan (might be useful for context).
        reference_index (dict, optional): Master reference index mapping ref IDs to details.

    Returns:
    Yields:
        str: Content chunks of the summary.
        dict: The final item yielded is a dictionary {'usage_details': ...}.

    Raises:
        SummarizerError: If there is an error generating the response.
    """
    logger.debug(f"Generating final summary for scope: {scope}")
    final_usage_details = None  # Initialize

    # --- Research Scope ---
    if scope == "research":
        try:
            # Get model configuration dynamically
            model_config = config.get_model_config(MODEL_CAPABILITY)
            model_name = model_config["name"]
            prompt_token_cost = model_config["prompt_token_cost"]
            completion_token_cost = model_config["completion_token_cost"]
        except Exception as config_err:
            logger.error(
                f"Failed to get model configuration: {config_err}", exc_info=True
            )
            yield f"\n\n**Internal Error:** Failed to load summarizer configuration.\n"
            raise SummarizerError(f"Configuration error: {config_err}")

        try:
            # Prepare system message with summary prompt
            system_message = {"role": "system", "content": SYSTEM_PROMPT}

            # Prepare messages for the API call
            messages = [system_message]

            # Format the aggregated detailed research for the prompt
            research_context = "Aggregated Detailed Research Findings:\n\n"
            if not aggregated_detailed_research:
                research_context += (
                    "No detailed research findings were provided or generated.\n"
                )
            else:
                for db_name, research_text in aggregated_detailed_research.items():
                    db_display_name = available_databases.get(db_name, {}).get(
                        "name", db_name
                    )
                    research_context += f"=== Findings from: {db_display_name} ===\n"
                    research_context += f"{research_text}\n\n"

            context_message = {"role": "system", "content": research_context.strip()}
            messages.append(context_message)

            # Add original query plan details if available
            if original_query_plan and original_query_plan.get("queries"):
                plan_context = "Original Query Plan:\n"
                for i, q in enumerate(original_query_plan["queries"]):
                    db_identifier = q.get("database")
                    db_display_name = available_databases.get(db_identifier, {}).get(
                        "name", db_identifier
                    )
                    plan_context += f"{i+1}. {db_display_name}: {q.get('query')}\n"
                messages.append({"role": "system", "content": plan_context.strip()})

            # Add reference index information if available
            if reference_index:
                ref_context = "Available References:\n"

                for ref_id, ref_data in reference_index.items():
                    doc_name = ref_data.get("doc_name", "Unknown")
                    page = ref_data.get("page", 1)
                    ref_context += f"[REF:{ref_id}] = {doc_name} - Page {page}\n"

                messages.append({"role": "system", "content": ref_context.strip()})

            # User message requesting summary with research statement context
            user_content = "Please generate the comprehensive research summary based on the provided context and requirements. Synthesize the findings from all sources into a single, coherent response following the specified template and citation format."
            
            if research_statement:
                user_content = f"Research Statement: {research_statement}\n\n{user_content}\n\nIMPORTANT: Focus your response on directly addressing the research statement above. Prioritize information that answers the specific question asked and avoid including tangential research that doesn't support the core query."
            
            user_message = {
                "role": "user",
                "content": user_content,
            }
            messages.append(user_message)

            logger.debug(
                f"Generating streaming research summary using model: {model_name}"
            )
            logger.debug(
                f"Summarizing detailed research from {len(aggregated_detailed_research)} databases."
            )

            # --- Synchronous LLM Call ---
            # Directly call the synchronous call_llm function
            llm_stream = call_llm(
                oauth_token=token,
                model=model_name,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,  # Keep streaming enabled
                prompt_token_cost=prompt_token_cost,
                completion_token_cost=completion_token_cost,
                # No database_name needed here
            )

            # Process the stream, yielding content and capturing final usage details
            for item in llm_stream:
                if isinstance(item, dict) and "usage_details" in item:
                    final_usage_details = item  # Capture usage details
                    break  # Stop after getting usage
                elif (
                    hasattr(item, "choices")
                    and item.choices
                    and item.choices[0].delta
                    and item.choices[0].delta.content
                ):
                    yield item.choices[0].delta.content
                # else: logger.debug("Received non-content chunk in summary stream.")

            logger.debug("Summary stream finished.")
            # Yield final usage details
            if final_usage_details:
                yield final_usage_details
            else:
                logger.warning("Usage details not found in summary stream.")
                yield {"usage_details": {"error": "Usage data missing from stream"}}

        except Exception as e:
            logger.error(
                f"Error generating streaming research summary: {str(e)}", exc_info=True
            )
            # Yield error message before raising
            yield f"\n\n**Error generating research summary:** {str(e)}\n"
            # Re-raise to signal failure upstream
            raise SummarizerError(
                f"Failed to generate streaming summary: {str(e)}"
            ) from e

    # --- Metadata Scope (Simplified) ---
    elif scope == "metadata":
        logger.warning(
            "Summarizer called with 'metadata' scope, which is not actively handled here anymore."
        )
        yield "Metadata processing complete (no summary generated by this agent)."

    # --- Invalid Scope ---
    else:
        error_msg = f"Invalid scope '{scope}' provided to summarizer."
        logger.error(error_msg)
        yield f"\n\n**Internal Error:** {error_msg}\n"
        raise SummarizerError(error_msg)
