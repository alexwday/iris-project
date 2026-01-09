"""
Prompt Loader Module.

Loads agent and global prompts from PostgreSQL database.
Provides composition of global prompts into agent system prompts.

Functions:
    get_prompt: Get a prompt from the database
    get_global_prompt: Get a global prompt by name
    compose_system_prompt: Compose a system prompt with globals
    get_composed_prompt: Get a fully composed prompt
"""

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from ..connections.postgres import get_session
from .fiscal_context import get_fiscal_statement

try:
    from ..agent.tools.database_metadata import (
        get_database_statement,
        get_filtered_database_statement,
    )

    _DATABASE_METADATA_AVAILABLE = True
except ImportError:
    _DATABASE_METADATA_AVAILABLE = False

logger = logging.getLogger(__name__)

GLOBAL_PROMPT_ORDER = ["project", "fiscal", "database", "restrictions"]

_prompt_cache: Dict[str, Dict] = {}


def get_prompt(layer: str, name: str, model: str = "iris") -> Optional[Dict]:
    """
    Get a prompt from the database with caching.

    Args:
        layer: Prompt layer (agent, subagent, global).
        name: Prompt name.
        model: Model identifier.

    Returns:
        Dict with prompt data or None if not found.
    """
    cache_key = f"{model}/{layer}/{name}"

    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key]

    try:
        with get_session() as session:
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
            return prompt_data

    except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
        logger.error("Error loading prompt %s: %s", cache_key, exc)
        return None


def get_global_prompt(name: str) -> str:
    """
    Get a global prompt by name.

    Special handling for dynamic prompts:
    - 'fiscal': Generated dynamically based on current date
    - 'database': Generated from iris_database_registry

    Args:
        name: Global prompt name (project, restrictions, fiscal, database).

    Returns:
        The global prompt content.
    """
    if name == "fiscal":
        return get_fiscal_statement()

    if name == "database":
        if not _DATABASE_METADATA_AVAILABLE:
            logger.warning("database_metadata module not available")
            return ""
        return get_database_statement()

    prompt = get_prompt("global", name)
    if prompt:
        return prompt.get("system_prompt", "")
    return ""


def compose_system_prompt(
    base_prompt: str,
    uses_global: List[str],
    context_placeholder: str = "{{CONTEXT_START}}",
) -> str:
    """
    Compose a system prompt by inserting global prompts.

    The base prompt should contain {{CONTEXT_START}} which gets replaced
    with all the global context statements.

    Args:
        base_prompt: The agent's base system prompt.
        uses_global: List of global prompt names to include.
        context_placeholder: Placeholder to replace (default: {{CONTEXT_START}}).

    Returns:
        Composed system prompt with globals inserted.
    """
    if not uses_global:
        return base_prompt.replace(context_placeholder, "")

    ordered_globals = [name for name in GLOBAL_PROMPT_ORDER if name in uses_global]
    ordered_globals.extend(name for name in uses_global if name not in ordered_globals)

    context_parts = []
    for name in ordered_globals:
        content = get_global_prompt(name)
        if content:
            context_parts.append(content)

    context_block = "\n\n".join(context_parts)

    if context_placeholder in base_prompt:
        return base_prompt.replace(context_placeholder, context_block)
    return context_block + "\n\n" + base_prompt


def _build_filtered_context(uses_global: List[str], filtered_stmt: str) -> str:
    """Build context block with filtered database statement."""
    context_parts = []
    for global_name in GLOBAL_PROMPT_ORDER:
        if global_name not in uses_global:
            continue
        if global_name == "database":
            context_parts.append(filtered_stmt)
        else:
            content = get_global_prompt(global_name)
            if content:
                context_parts.append(content)
    return "\n\n".join(context_parts)


def get_composed_prompt(
    layer: str,
    name: str,
    model: str = "iris",
    filtered_database: bool = False,
    db_names: Optional[List[str]] = None,
) -> Tuple[str, Optional[List[Dict]], Optional[str]]:
    """
    Get a fully composed prompt with global contexts inserted.

    Args:
        layer: Prompt layer (agent, subagent).
        name: Prompt name.
        model: Model identifier (default: iris).
        filtered_database: If True, use filtered database statement.
        db_names: List of database names to filter to (for planner).

    Returns:
        Tuple of (composed_system_prompt, tools_list, user_prompt_template).
        The user_prompt_template may contain placeholders like {{conversation}},
        {{research_statement}}, etc. that the caller should replace.

    Raises:
        ValueError: If prompt is not found.
    """
    prompt = get_prompt(layer, name, model)
    if not prompt:
        raise ValueError(f"Prompt not found: {model}/{layer}/{name}")

    base_prompt = prompt.get("system_prompt", "")
    uses_global = prompt.get("uses_global", [])
    tool_definition = prompt.get("tool_definition")
    user_prompt = prompt.get("user_prompt")

    composed = _compose_with_database_handling(
        base_prompt, uses_global, filtered_database, db_names
    )

    tools = [tool_definition] if tool_definition else None

    return composed, tools, user_prompt


def _compose_with_database_handling(
    base_prompt: str,
    uses_global: List[str],
    filtered_database: bool,
    db_names: Optional[List[str]],
) -> str:
    """Compose prompt, handling filtered database if requested."""
    if not filtered_database or "database" not in uses_global:
        return compose_system_prompt(base_prompt, uses_global)

    if not _DATABASE_METADATA_AVAILABLE:
        return compose_system_prompt(base_prompt, uses_global)

    filtered_stmt = get_filtered_database_statement(db_names)
    context_block = _build_filtered_context(uses_global, filtered_stmt)
    return base_prompt.replace("{{CONTEXT_START}}", context_block)
