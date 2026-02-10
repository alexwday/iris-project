"""
Prompt Loader - Database-backed prompt management with context injection.

This module provides prompt loading and caching for all IRIS agents. It fetches
versioned prompts from PostgreSQL at startup, caches them in memory, and supports
runtime context injection for fiscal dates and database availability. Used by
router, clarifier, planner, summarizer, and all subagents during initialization.

Prompts are lazy-loaded on first access if not pre-warmed via load_all_prompts().
Context placeholders ({{FISCAL_CONTEXT}}, {{DATABASE_CONTEXT}}) are replaced at
retrieval time based on injection flags.

INDEXING CONVENTION (applies across IRIS pipeline):
- Database selection (planner): 0-indexed (LLM tool call convention for arrays)
- Document lists (metadata): 1-indexed (human-readable prompts shown to LLM)
- User-facing references: 1-indexed (intuitive for end users, e.g., [REF:1])

The database context block uses 0-indexed database selection for planner prompts.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..connections.postgres import get_database_session
from .fiscal_context import generate_fiscal_context_statement

logger = logging.getLogger(__name__)

_prompt_cache: Dict[str, Dict[str, Any]] = {}


def get_ordered_database_keys(available_databases: Dict[str, Any]) -> List[str]:
    """Return database keys in consistent order: internal (sorted), external (sorted), other (sorted).

    Args:
        available_databases: Database configurations keyed by db_source.

    Returns:
        List of database keys in stable order for index assignment.
    """
    internal_keys = sorted(k for k in available_databases if k.startswith("internal_"))
    external_keys = sorted(k for k in available_databases if k.startswith("external_"))
    other_keys = sorted(
        k for k in available_databases
        if not k.startswith("internal_") and not k.startswith("external_")
    )
    return internal_keys + external_keys + other_keys


def load_all_prompts(model: str = "iris") -> Tuple[int, List[str]]:
    """Pre-warm the prompt cache by loading all prompts for a model namespace.

    Args:
        model: Model namespace to load (e.g., "iris", "doc_refresh").

    Returns:
        Tuple of (count of prompts loaded, list of "layer/name" identifiers).
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
            loaded_prompts = []
            for row in rows:
                layer, name, system_prompt, user_prompt, tool_definition, description = row
                cache_key = f"{model}/{layer}/{name}"
                _prompt_cache[cache_key] = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "tool_definition": tool_definition,
                    "description": description,
                }
                loaded_prompts.append(f"{layer}/{name}")
                count += 1

            logger.info("Loaded %d prompts for model '%s' into cache", count, model)
            return count, loaded_prompts

    except SQLAlchemyError as exc:
        logger.error("Error loading prompts for model %s: %s", model, exc)
        return 0, []


def get_prompt(
    layer: str,
    name: str,
    model: str = "iris",
    inject_fiscal: bool = False,
    inject_database: bool = False,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any], str]:
    """Retrieve a cached prompt with optional fiscal and database context injection.

    Args:
        layer: Prompt layer (e.g., "agent", "subagent").
        name: Prompt identifier (e.g., "router", "clarifier").
        model: Model namespace for prompt lookup.
        inject_fiscal: Replace {{FISCAL_CONTEXT}} with current fiscal period.
        inject_database: Replace {{DATABASE_CONTEXT}} with available databases.
        available_databases: Database configs to inject; fetched if None.

    Returns:
        Tuple of (system_prompt, tools_list, user_prompt).

    Raises:
        ValueError: If the requested prompt is not found in cache.
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
    user_prompt = _inject_context(
        user_prompt, inject_fiscal, inject_database, available_databases
    )

    tools = [tool_definition] if tool_definition else []

    return system_prompt, tools, user_prompt


def _inject_context(
    prompt_text: str,
    inject_fiscal: bool,
    inject_database: bool,
    available_databases: Optional[Dict[str, Any]],
) -> str:
    """Replace {{FISCAL_CONTEXT}}, {{DATABASE_CONTEXT}}, and {{MAX_DATABASES}} placeholders."""
    if inject_fiscal and "{{FISCAL_CONTEXT}}" in prompt_text:
        prompt_text = prompt_text.replace(
            "{{FISCAL_CONTEXT}}", generate_fiscal_context_statement()
        )

    if inject_database and "{{DATABASE_CONTEXT}}" in prompt_text:
        db_statement = _format_database_context_block(available_databases)
        prompt_text = prompt_text.replace("{{DATABASE_CONTEXT}}", db_statement)

    if "{{MAX_DATABASES}}" in prompt_text:
        from .env_config import config

        prompt_text = prompt_text.replace(
            "{{MAX_DATABASES}}", str(config.MAX_DATABASES_PER_QUERY)
        )

    return prompt_text


def _format_database_context_block(
    available_databases: Optional[Dict[str, Any]]
) -> str:
    """Build XML block describing available databases with index attributes."""
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

    ordered_keys = get_ordered_database_keys(available_databases)
    key_to_index = {key: idx for idx, key in enumerate(ordered_keys)}

    lines: List[str] = ["<AVAILABLE_DATABASES>"]

    def _render_section(db_keys: List[str], tag: str) -> None:
        """Append XML elements for a group of databases under the given tag."""
        if not db_keys:
            return
        lines.append(f"<{tag}>")
        for db_key in db_keys:
            db_info = available_databases[db_key]
            idx = key_to_index[db_key]
            name = db_info.get("name", db_key)
            description = db_info.get("db_description") or db_info.get("description", "")
            lines.extend(
                [
                    f'<DATABASE index="{idx}" id="{db_key}">',
                    f"  <NAME>{name}</NAME>",
                    f"  <DESCRIPTION>{description}</DESCRIPTION>",
                    "</DATABASE>",
                ]
            )
        lines.append(f"</{tag}>")

    internal_keys = [k for k in ordered_keys if k.startswith("internal_")]
    external_keys = [k for k in ordered_keys if k.startswith("external_")]
    other_keys = [
        k for k in ordered_keys
        if not k.startswith("internal_") and not k.startswith("external_")
    ]
    _render_section(internal_keys, "INTERNAL_DATABASES")
    _render_section(external_keys, "EXTERNAL_DATABASES")
    _render_section(other_keys, "OTHER_DATABASES")

    lines.append("</AVAILABLE_DATABASES>")
    return "\n".join(lines)
