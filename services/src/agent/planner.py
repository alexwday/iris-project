"""
Planner Agent Module.

Handles creation of database research query plans based on research statements
from the clarifier. Determines which databases to query using LLM tool calling
with dynamic database options.

Includes document metadata similarity search to provide context for database
selection decisions.

Functions:
    generate_database_selection_plan: Create a plan of database queries

Classes:
    PlannerError: Exception for planner-related errors
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from ..connections.llm import execute_llm_call
from ..connections.postgres import get_database_session
from ..utils.env_config import config
from ..utils.prompt_loader import fetch_prompt_with_context

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.0
PLANNER_TOOL_NAME = "select_databases"
MAX_CONTEXT_DOCUMENTS = 5
METADATA_SEARCH_TOP_K = 5
EMBEDDING_DIMENSIONS = 3072

logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Exception raised for planner-related errors."""


# --- Document Metadata Search Functions ---


def _generate_query_embedding_vector(
    query: str, token: Optional[str] = None
) -> Tuple[Optional[List[float]], Optional[Dict[str, Any]]]:
    """Generate an embedding for the query string.

    Args:
        query (str): Query text to embed.
        token (Optional[str]): OAuth token for API authentication.

    Returns:
        Tuple[Optional[List[float]], Optional[Dict[str, Any]]]: Embedding vector and
            optional usage details.
    """
    logger.info("Generating embedding for query: '%s...'", query[:100])
    usage_details = None

    try:
        model_config = config.get_model_settings("embedding")
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config.get("completion_token_cost", 0.0)

        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
            "model": model_name,
            "input": [query],
            "dimensions": EMBEDDING_DIMENSIONS,
            "database_name": "document_metadata_search",
            "is_embedding": True,
        }

        result = execute_llm_call(**call_params)

        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug("Embedding usage details: %s", usage_details)
        else:
            response = result
            logger.debug("execute_llm_call did not return usage_details")

        if (
            response
            and hasattr(response, "data")
            and response.data
            and hasattr(response.data[0], "embedding")
            and response.data[0].embedding
        ):
            logger.info("Embedding generated successfully.")
            return response.data[0].embedding, usage_details

        logger.error(
            "No embedding data received from API.",
            extra={"api_response": response},
        )
        return None, usage_details

    except Exception as e:
        logger.error("Failed to generate embedding: %s", e, exc_info=True)
        return None, usage_details


def _search_document_metadata_by_embedding(
    research_statement: str,
    token: Optional[str] = None,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[List[float]]]:
    """Search metadata embeddings to find relevant documents.

    Args:
        research_statement (str): Research statement to search for.
        token (Optional[str]): OAuth token for API authentication.
        available_databases (Optional[Dict[str, Any]]): Databases to filter by.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[List[float]]]:
            Matching documents, usage details, and the query embedding.
    """
    logger.info(
        "Searching document metadata for research statement: '%s...'",
        research_statement[:100],
    )
    usage_details = None

    try:
        query_embedding, usage_details = _generate_query_embedding_vector(
            research_statement, token
        )

        if query_embedding is None:
            logger.error("Could not generate embedding for research statement")
            return [], usage_details, None

        embedding_str = json.dumps(query_embedding, separators=(",", ":"))

        if not available_databases:
            logger.warning("No available_databases provided - cannot search metadata")
            return [], usage_details, query_embedding

        with get_database_session() as session:
            db_sources = sorted(available_databases.keys())
            in_placeholders = ", ".join([f":db_{i}" for i in range(len(db_sources))])
            # Use CAST instead of :: to avoid SQLAlchemy parameter parsing issues
            sql = text(
                f"""
                SELECT
                    db_source,
                    document_name,
                    document_summary,
                    document_type,
                    1 - (summary_embedding <=> CAST(:embedding AS halfvec))
                        AS similarity_score
                FROM iris_document_metadata
                WHERE summary_embedding IS NOT NULL
                    AND db_source IN ({in_placeholders})
                ORDER BY similarity_score DESC
                LIMIT :top_k
            """
            )
            params = {"embedding": embedding_str, "top_k": METADATA_SEARCH_TOP_K}
            for i, db_source in enumerate(db_sources):
                params[f"db_{i}"] = db_source

            result = session.execute(sql, params)
            results_raw = result.mappings().all()

            results = [
                {**dict(row), "rank": i + 1} for i, row in enumerate(results_raw)
            ]

            logger.info(
                "Found %d matching documents in iris_document_metadata", len(results)
            )

            return results, usage_details, query_embedding

    except (ValueError, TypeError, RuntimeError) as exc:
        logger.error("Error searching document metadata: %s", exc, exc_info=True)
        return [], usage_details, None


# --- Model Configuration ---


def _get_model_settings() -> Dict[str, Any]:
    """Get model settings from config based on capability tier.

    Returns:
        Dict[str, Any]: Model name and token costs.
    """
    model_config = config.get_model_settings(MODEL_CAPABILITY)
    return {
        "name": model_config["name"],
        "prompt_token_cost": model_config["prompt_token_cost"],
        "completion_token_cost": model_config.get("completion_token_cost", 0.0),
    }


def _inject_database_enum_into_tool(
    tool_definition: Dict[str, Any],
    available_databases: Dict[str, Any],
) -> Dict[str, Any]:
    """Inject dynamic database enum into tool definition.

    Args:
        tool_definition (Dict[str, Any]): Tool definition from the database.
        available_databases (Dict[str, Any]): Available database configurations.

    Returns:
        Dict[str, Any]: Tool definition with dynamic enum injected.

    Raises:
        PlannerError: If tool definition structure is invalid.
    """
    import copy

    tool = copy.deepcopy(tool_definition)
    max_databases = config.MAX_DATABASES_PER_QUERY
    db_keys = sorted(available_databases.keys())

    try:
        params = tool["function"]["parameters"]["properties"]["databases"]
        params["items"]["enum"] = db_keys
        params["maxItems"] = max_databases
    except (KeyError, TypeError) as exc:
        raise PlannerError(
            f"Invalid tool definition structure in database: {exc}"
        ) from exc

    return tool


def _format_document_metadata_context(
    document_metadata_context: Optional[List[Dict[str, Any]]],
) -> str:
    """Format document metadata context into a string for the user message.

    Args:
        document_metadata_context (Optional[List[Dict[str, Any]]]): Relevant documents.

    Returns:
        str: Formatted document context, or empty string if none.
    """
    if not document_metadata_context:
        return ""

    context_parts = ["<RELEVANT_DOCUMENTS_CONTEXT>"]
    context_parts.append(
        "The following documents were found to be relevant to this research:\n"
    )

    for i, doc in enumerate(document_metadata_context[:MAX_CONTEXT_DOCUMENTS], 1):
        context_parts.append(f"{i}. **{doc.get('db_source', 'Unknown Source')}**")
        context_parts.append(f"   Document: {doc.get('document_name', 'Unknown')}")
        summary = doc.get("document_summary", "No summary available")
        context_parts.append(f"   Summary: {summary}")
        context_parts.append(f"   Similarity: {doc.get('similarity_score', 0.0):.3f}\n")

    context_parts.append("</RELEVANT_DOCUMENTS_CONTEXT>")
    return "\n".join(context_parts)


def _build_planner_user_message(
    user_prompt_template: str,
    research_statement: str,
    document_metadata_context: Optional[List[Dict[str, Any]]],
) -> str:
    """Build the user message content for the planner LLM call.

    Args:
        user_prompt_template (str): Template from database with placeholders.
        research_statement (str): Research statement from the clarifier.
        document_metadata_context (Optional[List[Dict[str, Any]]]): Relevant documents.

    Returns:
        str: Formatted user message.

    Raises:
        PlannerError: If user_prompt_template is missing.
    """
    if not user_prompt_template:
        raise PlannerError(
            "user_prompt not found in database for agent/planner. "
            "Please ensure the prompt is configured in the prompts table."
        )

    doc_context = _format_document_metadata_context(document_metadata_context)

    user_content = user_prompt_template.replace(
        "{{research_statement}}", research_statement
    )
    user_content = user_content.replace("{{document_metadata_context}}", doc_context)

    return user_content


def _parse_planner_tool_response(response: Any) -> Dict[str, Any]:
    """Extract and validate tool call arguments from LLM response.

    Args:
        response (Any): LLM response object.

    Returns:
        Dict[str, Any]: Parsed tool call arguments.

    Raises:
        PlannerError: If response is invalid or tool call parsing fails.
    """
    if not response or not hasattr(response, "choices") or not response.choices:
        raise PlannerError("Invalid or empty response received from LLM")

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None) if message else None
    if not tool_calls:
        content_returned = (
            message.content if message and message.content else "No content"
        )
        logger.warning(
            "Expected tool call but received content: %s...",
            content_returned[:100],
        )
        raise PlannerError(
            "No tool call received in response, content returned instead."
        )

    tool_call = tool_calls[0]

    if tool_call.function.name != PLANNER_TOOL_NAME:
        raise PlannerError(f"Unexpected function call: {tool_call.function.name}")

    arguments = getattr(tool_call.function, "arguments", None)
    if isinstance(arguments, dict):
        return arguments

    if not isinstance(arguments, str):
        raise PlannerError(f"Invalid tool arguments type: {type(arguments)}")

    try:
        return json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise PlannerError(f"Invalid JSON in tool arguments: {arguments}") from exc


def _validate_selected_database_list(
    arguments: Dict[str, Any],
    available_databases: Dict[str, Any],
) -> List[str]:
    """Validate and extract selected databases from tool arguments.

    Args:
        arguments (Dict[str, Any]): Parsed tool call arguments.
        available_databases (Dict[str, Any]): Available database configurations.

    Returns:
        List[str]: Validated database names.

    Raises:
        PlannerError: If databases are missing, empty, or invalid.
    """
    selected_databases = arguments.get("databases", [])

    if not selected_databases:
        raise PlannerError("Missing or empty 'databases' in tool arguments")

    validated_databases = []
    for i, db_name in enumerate(selected_databases):
        if not isinstance(db_name, str):
            raise PlannerError(f"Database entry {i + 1} is not a string: {db_name}")
        if db_name not in available_databases:
            raise PlannerError(f"Selected database {i + 1} is unknown: {db_name}")
        validated_databases.append(db_name)

    return validated_databases


def _load_planner_prompt_components(
    available_databases: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]], str]:
    """Get prompt components for the planner.

    Args:
        available_databases (Dict[str, Any]): Available database configurations.

    Returns:
        Tuple[str, List[Dict[str, Any]], str]: System prompt, tool definitions, user
            prompt template.

    Raises:
        PlannerError: If tool definition is not found.
    """
    system_prompt, tools, user_prompt_template = fetch_prompt_with_context(
        "agent", "planner", available_databases=available_databases
    )

    if not tools:
        raise PlannerError(
            "tool_definition not found in database for agent/planner. "
            "Please ensure the prompt is configured in the prompts table."
        )

    tool_with_enum = _inject_database_enum_into_tool(tools[0], available_databases)

    return system_prompt, [tool_with_enum], user_prompt_template


def _execute_planner_llm_call(
    token: str,
    messages: List[Dict[str, str]],
    tool_definitions: List[Dict[str, Any]],
    model_settings: Dict[str, Any],
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Make the LLM call for database selection.

    Args:
        token (str): Authentication token for API access.
        messages (List[Dict[str, str]]): Messages for the LLM.
        tool_definitions (List[Dict[str, Any]]): Tool definitions for the planner.
        model_settings (Dict[str, Any]): Model configuration from env_config.

    Returns:
        Tuple[Any, Optional[Dict[str, Any]]]: Response object and usage details.
    """
    return execute_llm_call(
        oauth_token=token,
        model=model_settings["name"],
        messages=messages,
        max_tokens=MODEL_MAX_TOKENS,
        temperature=MODEL_TEMPERATURE,
        tools=tool_definitions,
        tool_choice={
            "type": "function",
            "function": {"name": PLANNER_TOOL_NAME},
        },
        stream=False,
        prompt_token_cost=model_settings["prompt_token_cost"],
        completion_token_cost=model_settings["completion_token_cost"],
    )


def generate_database_selection_plan(
    research_statement: str,
    token: str,
    available_databases: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Create a plan of selected databases based on a research statement.

    Performs document metadata similarity search, then uses LLM tool calling to select
    which databases should be queried.

    Args:
        research_statement (str): Research statement from the clarifier.
        token (str): Authentication token for API access.
        available_databases (Dict[str, Any]): Database configurations filtered by user.

    Returns:
        Tuple[Dict[str, Any], List[Dict[str, Any]]]: Database selection plan (with
            `databases` and `query_embedding`) and usage details.

    Raises:
        PlannerError: If there is an error creating the database selection plan.
    """
    usage_details_list = []

    try:
        if not available_databases:
            raise PlannerError("No databases provided for planner selection.")
        # Step 1: Search document metadata for relevant context
        logger.info("Searching document metadata for planner context...")
        metadata_results, embedding_usage, query_embedding = _search_document_metadata_by_embedding(
            research_statement, token, available_databases
        )
        if embedding_usage:
            usage_details_list.append(embedding_usage)

        if metadata_results:
            logger.info(
                "Found %d relevant documents in metadata", len(metadata_results)
            )
        else:
            logger.info("No relevant documents found in metadata")

        # Step 2: Build prompts and call LLM for database selection
        system_prompt, tool_definitions, user_prompt_template = _load_planner_prompt_components(
            available_databases
        )
        model_settings = _get_model_settings()
        user_content = _build_planner_user_message(
            user_prompt_template,
            research_statement,
            metadata_results,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response, llm_usage = _execute_planner_llm_call(
            token, messages, tool_definitions, model_settings
        )
        if llm_usage:
            usage_details_list.append(llm_usage)

        arguments = _parse_planner_tool_response(response)
        validated = _validate_selected_database_list(arguments, available_databases)

        logger.info(
            "Database selection plan created with %d databases: %s",
            len(validated),
            validated,
        )

        return {
            "databases": validated,
            "query_embedding": query_embedding,
        }, usage_details_list

    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        logger.error(
            "Error creating database selection plan: %s", str(exc), exc_info=True
        )
        raise PlannerError(f"Failed to create database selection plan: {exc}") from exc
