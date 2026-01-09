"""
Prompt Loader Module for Document Refresh Pipeline.

Simplified prompt loading from PostgreSQL database.
Used to load processing prompts for document structure detection,
summarization, and other LLM-based tasks.

Functions:
    get_prompt: Get a prompt from the database
    clear_cache: Clear the prompt cache
"""

import logging
from typing import Any, Dict, Optional

import psycopg2

from .env_config import Config

logger = logging.getLogger(__name__)

_prompt_cache: Dict[str, Dict[str, Any]] = {}


def get_prompt(
    layer: str, name: str, model: str = "doc_refresh"
) -> Optional[Dict[str, Any]]:
    """
    Get a prompt from the database with caching.

    Args:
        layer: Prompt layer (e.g., 'stage', 'substage').
        name: Prompt name (e.g., 'structure_detection', 'section_summary').
        model: Model identifier (default: 'doc_refresh').

    Returns:
        Dict with prompt data including 'system_prompt', 'user_prompt',
        'description', or None if not found.
    """
    cache_key = f"{model}/{layer}/{name}"

    if cache_key in _prompt_cache:
        logger.debug("Prompt cache hit: %s", cache_key)
        return _prompt_cache[cache_key]

    try:
        db_params = Config.get_db_params()
        with psycopg2.connect(**db_params) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT system_prompt, user_prompt, description
                    FROM prompts
                    WHERE model = %s AND layer = %s AND name = %s
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (model, layer, name),
                )
                row = cursor.fetchone()

                if not row:
                    logger.warning("Prompt not found: %s", cache_key)
                    return None

                prompt_data = {
                    "system_prompt": row[0],
                    "user_prompt": row[1],
                    "description": row[2],
                }
                _prompt_cache[cache_key] = prompt_data
                logger.debug("Prompt loaded and cached: %s", cache_key)
                return prompt_data

    except psycopg2.Error as exc:
        logger.error("Database error loading prompt %s: %s", cache_key, exc)
        return None
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Error processing prompt %s: %s", cache_key, exc)
        return None


def get_system_prompt(layer: str, name: str, model: str = "doc_refresh") -> str:
    """
    Get just the system prompt string from the database.

    Args:
        layer: Prompt layer.
        name: Prompt name.
        model: Model identifier.

    Returns:
        System prompt string, or empty string if not found.
    """
    prompt = get_prompt(layer, name, model)
    if prompt:
        return prompt.get("system_prompt", "")
    return ""


def get_user_prompt(layer: str, name: str, model: str = "doc_refresh") -> str:
    """
    Get just the user prompt template from the database.

    Args:
        layer: Prompt layer.
        name: Prompt name.
        model: Model identifier.

    Returns:
        User prompt template string, or empty string if not found.
    """
    prompt = get_prompt(layer, name, model)
    if prompt:
        return prompt.get("user_prompt", "")
    return ""


def clear_cache() -> None:
    """Clear the prompt cache."""
    _prompt_cache.clear()
    logger.info("Prompt cache cleared")
