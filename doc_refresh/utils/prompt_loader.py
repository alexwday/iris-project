"""
Prompt Loader Module.

Loads prompts from PostgreSQL and injects context based on layer.

Functions:
    fetch_prompt_from_database: Get raw prompt from database (internal)
    fetch_prompt_with_context: Get prompt with context injected (main entry point)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..connections.postgres import get_database_session
from .fiscal_context import generate_fiscal_context_statement

logger = logging.getLogger(__name__)

_prompt_cache: Dict[str, Dict[str, Any]] = {}


def fetch_prompt_from_database(
    layer: str, name: str, model: str = "iris"
) -> Optional[Dict[str, Any]]:
    """Fetch a prompt from the database with caching.

    Args:
        layer (str): Prompt layer (agent, subagent, global).
        name (str): Prompt name.
        model (str): Model identifier.

    Returns:
        Optional[Dict[str, Any]]: Prompt fields if found, otherwise None.
    """
    cache_key = f"{model}/{layer}/{name}"

    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key].copy()

    try:
        with get_database_session() as session:
            result = session.execute(
                text(
                    """
                    SELECT system_prompt, user_prompt, tool_definition,
                           uses_global, description
                    FROM prompts
                    WHERE model = :model AND layer = :layer AND name = :name
                    ORDER BY version DESC
                    LIMIT 1
                """
                ),
                {"model": model, "layer": layer, "name": name},
            )
            row = result.fetchone()

            if not row:
                logger.warning("Prompt not found: %s", cache_key)
                return None

            prompt_data = {
                "system_prompt": row[0],
                "user_prompt": row[1],
                "tool_definition": row[2],
                "uses_global": row[3] or [],
                "description": row[4],
            }
            _prompt_cache[cache_key] = prompt_data
            return prompt_data.copy()

    except (
        SQLAlchemyError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        OSError,
    ) as exc:
        logger.error("Error loading prompt %s: %s", cache_key, exc)
        return None


def _format_database_context_block(
    available_databases: Optional[Dict[str, Any]]
) -> str:
    """Build an XML-like string describing available databases.

    Args:
        available_databases (Optional[Dict[str, Any]]): Database configs keyed by
            identifier. If None, a fallback loader is used.

    Returns:
        str: Structured description of databases for prompt injection.
    """
    if available_databases is None:
        try:
            from ..agent.tools.database_metadata import fetch_available_databases

            available_databases = fetch_available_databases()
        except ImportError:
            logger.warning("database_metadata module not available")
            return (
                "<AVAILABLE_DATABASES>\n"
                "Database information not available.\n"
                "</AVAILABLE_DATABASES>"
            )

    if not available_databases:
        return (
            "<AVAILABLE_DATABASES>\n"
            "No databases available.\n"
            "</AVAILABLE_DATABASES>"
        )

    lines: List[str] = ["<AVAILABLE_DATABASES>"]

    def _render_section(db_items: Dict[str, Any], tag: str) -> None:
        if not db_items:
            return
        lines.append(f"<{tag}>")
        for db_name, db_info in db_items.items():
            name = db_info.get("name", db_name)
            description = db_info.get("description", "")
            lines.extend(
                [
                    f'<DATABASE id="{db_name}">',
                    f"  <NAME>{name}</NAME>",
                    f"  <DESCRIPTION>{description}</DESCRIPTION>",
                    "</DATABASE>",
                ]
            )
        lines.append(f"</{tag}>")

    internal_dbs = {
        key: value
        for key, value in available_databases.items()
        if key.startswith("internal_")
    }
    external_dbs = {
        key: value
        for key, value in available_databases.items()
        if key.startswith("external_")
    }
    _render_section(internal_dbs, "INTERNAL_DATABASES")
    _render_section(external_dbs, "EXTERNAL_DATABASES")

    lines.append("</AVAILABLE_DATABASES>")
    return "\n".join(lines)


def fetch_prompt_with_context(
    layer: str,
    name: str,
    model: str = "iris",
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any], str]:
    """Load a prompt and inject context appropriate for the given layer.

    For agent layers the fiscal and database contexts are injected; subagents
    only receive fiscal context; global layers are passed through unchanged.

    Args:
        layer (str): Prompt layer (agent, subagent, global).
        name (str): Prompt name.
        model (str): Model identifier.
        available_databases (Optional[Dict[str, Any]]): Pre-filtered databases for
            agent prompts. When None, all available databases are loaded.

    Returns:
        Tuple[str, List[Any], str]: System prompt (with context), list of tool
        definitions (or an empty list), and the user prompt template.

    Raises:
        ValueError: If the requested prompt cannot be found.
    """
    prompt = fetch_prompt_from_database(layer, name, model)
    if not prompt:
        raise ValueError(f"Prompt not found: {model}/{layer}/{name}")

    system_prompt = prompt.get("system_prompt", "")
    tool_definition = prompt.get("tool_definition")
    user_prompt = prompt.get("user_prompt", "")

    inject_fiscal = layer in ("agent", "subagent")
    inject_database = layer == "agent"

    if inject_fiscal and "{{FISCAL_CONTEXT}}" in system_prompt:
        system_prompt = system_prompt.replace(
            "{{FISCAL_CONTEXT}}", generate_fiscal_context_statement()
        )

    if inject_database and "{{DATABASE_CONTEXT}}" in system_prompt:
        db_statement = _format_database_context_block(available_databases)
        system_prompt = system_prompt.replace("{{DATABASE_CONTEXT}}", db_statement)

    if not inject_fiscal and "{{FISCAL_CONTEXT}}" in system_prompt:
        logger.warning(
            "Prompt %s/%s has {{FISCAL_CONTEXT}} but layer doesn't inject it",
            layer,
            name,
        )
    if not inject_database and "{{DATABASE_CONTEXT}}" in system_prompt:
        logger.warning(
            "Prompt %s/%s has {{DATABASE_CONTEXT}} but layer doesn't inject it",
            layer,
            name,
        )

    tools = [tool_definition] if tool_definition else []

    return system_prompt, tools, user_prompt


def fetch_prompt_raw(
    layer: str,
    name: str,
    model: str = "doc_refresh",
) -> Tuple[str, Optional[Dict], str]:
    """Load a prompt without any context injection.

    For doc_refresh pipeline - no fiscal or database context needed.

    Returns:
        Tuple[str, Optional[Dict], str]: System prompt, tool definition dict (or None), user prompt.
    """
    prompt = fetch_prompt_from_database(layer, name, model)
    if not prompt:
        raise ValueError(f"Prompt not found: {model}/{layer}/{name}")

    return (
        prompt.get("system_prompt", ""),
        prompt.get("tool_definition"),
        prompt.get("user_prompt", ""),
    )
