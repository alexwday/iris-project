"""
Prompt Loader Module.

Loads prompts from PostgreSQL with optional context injection.

Functions:
    load_all_prompts: Pre-load all prompts into cache (call at startup)
    get_prompt: Get a prompt from cache with optional context injection
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..connections.postgres import get_database_session
from .fiscal_context import generate_fiscal_context_statement

logger = logging.getLogger(__name__)

_prompt_cache: Dict[str, Dict[str, Any]] = {}


def load_all_prompts(model: str = "doc_refresh") -> int:
    """Load all prompts for a model into the cache.

    Call this at application startup to pre-warm the cache.

    Args:
        model: Model identifier (e.g., "iris", "doc_refresh").

    Returns:
        Number of prompts loaded.
    """
    try:
        with get_database_session() as session:
            result = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (layer, name)
                        layer, name, system_prompt, user_prompt,
                        tool_definition, description
                    FROM prompts
                    WHERE model = :model
                    ORDER BY layer, name, version DESC
                    """
                ),
                {"model": model},
            )
            rows = result.fetchall()

            count = 0
            for row in rows:
                layer, name, system_prompt, user_prompt, tool_definition, description = row
                cache_key = f"{model}/{layer}/{name}"
                _prompt_cache[cache_key] = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "tool_definition": tool_definition,
                    "description": description,
                }
                count += 1

            logger.info("Loaded %d prompts for model '%s' into cache", count, model)
            return count

    except SQLAlchemyError as exc:
        logger.error("Error loading prompts for model %s: %s", model, exc)
        return 0


def get_prompt(
    layer: str,
    name: str,
    model: str = "doc_refresh",
    inject_fiscal: bool = False,
    inject_database: bool = False,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any], str]:
    """Get a prompt from cache with optional context injection.

    Args:
        layer: Prompt layer (e.g., "agent", "subagent").
        name: Prompt name (e.g., "router", "clarifier").
        model: Model identifier.
        inject_fiscal: If True, replace {{FISCAL_CONTEXT}} placeholder.
        inject_database: If True, replace {{DATABASE_CONTEXT}} placeholder.
        available_databases: Database configs for context injection.

    Returns:
        Tuple of (system_prompt, tools_list, user_prompt).

    Raises:
        ValueError: If prompt not found.
    """
    cache_key = f"{model}/{layer}/{name}"

    # Try cache first; lazy-load if cache is empty for this model
    if cache_key not in _prompt_cache:
        if not any(k.startswith(f"{model}/") for k in _prompt_cache):
            load_all_prompts(model)

    if cache_key not in _prompt_cache:
        raise ValueError(f"Prompt not found: {cache_key}")

    prompt = _prompt_cache[cache_key].copy()

    system_prompt = prompt.get("system_prompt", "")
    tool_definition = prompt.get("tool_definition")
    user_prompt = prompt.get("user_prompt", "")

    # Inject context if requested
    system_prompt = _inject_context(
        system_prompt, inject_fiscal, inject_database, available_databases
    )

    tools = [tool_definition] if tool_definition else []

    return system_prompt, tools, user_prompt


def _inject_context(
    system_prompt: str,
    inject_fiscal: bool,
    inject_database: bool,
    available_databases: Optional[Dict[str, Any]],
) -> str:
    """Inject fiscal and database context into system prompt.

    Args:
        system_prompt: The raw system prompt text.
        inject_fiscal: If True, replace {{FISCAL_CONTEXT}}.
        inject_database: If True, replace {{DATABASE_CONTEXT}}.
        available_databases: Database configs for database context.

    Returns:
        System prompt with context injected.
    """
    if inject_fiscal and "{{FISCAL_CONTEXT}}" in system_prompt:
        system_prompt = system_prompt.replace(
            "{{FISCAL_CONTEXT}}", generate_fiscal_context_statement()
        )

    if inject_database and "{{DATABASE_CONTEXT}}" in system_prompt:
        db_statement = _format_database_context_block(available_databases)
        system_prompt = system_prompt.replace("{{DATABASE_CONTEXT}}", db_statement)

    return system_prompt


def _format_database_context_block(
    available_databases: Optional[Dict[str, Any]]
) -> str:
    """Build an XML-like string describing available databases.

    Args:
        available_databases: Database configs keyed by identifier.

    Returns:
        Structured description of databases for prompt injection.
    """
    # doc_refresh doesn't have database_metadata, so just use what's provided
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
