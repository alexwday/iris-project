"""
Environment Configuration - Centralized settings from environment variables.

This module provides the single source of truth for all IRIS configuration values.
It reads from environment variables at import time and exposes them through the
Config class. Used by every component in the system: agents, database connections,
LLM clients, and process monitoring.

All configuration is loaded once at module import. The Config class provides both
direct attribute access (Config.DB_HOST) and helper methods for grouped settings
(get_database_params, get_model_settings). Validation can be triggered explicitly
via validate_required_environment() during application startup.
"""

import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables at import time."""

    BASE_URL: str = os.getenv("AZURE_BASE_URL") or "https://api.openai.com/v1"

    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "")

    MODEL_SMALL_PROMPT_COST: float = float(os.getenv("IRIS_MODEL_SMALL_PROMPT_COST") or 0)
    MODEL_SMALL_COMPLETION_COST: float = float(os.getenv("IRIS_MODEL_SMALL_COMPLETION_COST") or 0)
    MODEL_LARGE_PROMPT_COST: float = float(os.getenv("IRIS_MODEL_LARGE_PROMPT_COST") or 0)
    MODEL_LARGE_COMPLETION_COST: float = float(os.getenv("IRIS_MODEL_LARGE_COMPLETION_COST") or 0)
    MODEL_EMBEDDING_PROMPT_COST: float = float(os.getenv("IRIS_MODEL_EMBEDDING_PROMPT_COST") or 0)
    MODEL_EMBEDDING_COMPLETION_COST: float = float(os.getenv("IRIS_MODEL_EMBEDDING_COMPLETION_COST") or 0)

    MAX_HISTORY_LENGTH: int = int(os.getenv("IRIS_MAX_HISTORY_LENGTH") or 10)
    MAX_DATABASES_PER_QUERY: int = int(os.getenv("IRIS_MAX_DATABASES_PER_QUERY") or 5)

    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "")

    PROCESS_MONITOR_MODEL_NAME: str = os.getenv("IRIS_PROCESS_MONITOR_MODEL_NAME", "")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")

    @classmethod
    def validate_required_environment(cls) -> bool:
        """Check that all required environment variables are set.

        Returns:
            True if all required values are present, False otherwise.
        """
        required = {
            "VECTOR_POSTGRES_DB_HOST": cls.DB_HOST,
            "VECTOR_POSTGRES_DB_PORT": cls.DB_PORT,
            "VECTOR_POSTGRES_DB_NAME": cls.DB_NAME,
            "VECTOR_POSTGRES_DB_USERNAME": cls.DB_USER,
            "IRIS_MODEL_SMALL": cls.MODEL_SMALL,
            "IRIS_MODEL_LARGE": cls.MODEL_LARGE,
            "IRIS_MODEL_EMBEDDING": cls.MODEL_EMBEDDING,
            "IRIS_LOG_LEVEL": cls.LOG_LEVEL,
            "IRIS_PROCESS_MONITOR_MODEL_NAME": cls.PROCESS_MONITOR_MODEL_NAME,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            logger.error("Missing required environment variables: %s", ", ".join(missing))
            return False
        logger.info("All required configuration values are set")
        return True

    @classmethod
    def get_database_params(cls) -> dict:
        """Build connection parameters dict for PostgreSQL.

        Returns:
            Dict with host, port, dbname, user, password keys.
        """
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }

    @classmethod
    def get_model_settings(cls, capability: str) -> dict:
        """Get model name and cost configuration for a capability tier.

        Args:
            capability: One of "small", "large", or "embedding".

        Returns:
            Dict with name, prompt_token_cost, completion_token_cost keys.

        Raises:
            ValueError: If capability is not a recognized tier.
        """
        configs = {
            "small": (cls.MODEL_SMALL, cls.MODEL_SMALL_PROMPT_COST, cls.MODEL_SMALL_COMPLETION_COST),
            "large": (cls.MODEL_LARGE, cls.MODEL_LARGE_PROMPT_COST, cls.MODEL_LARGE_COMPLETION_COST),
            "embedding": (cls.MODEL_EMBEDDING, cls.MODEL_EMBEDDING_PROMPT_COST, cls.MODEL_EMBEDDING_COMPLETION_COST),
        }
        if capability not in configs:
            raise ValueError(f"Unknown capability: {capability}. Use: small, large, embedding")
        name, prompt_cost, completion_cost = configs[capability]
        return {"name": name, "prompt_token_cost": prompt_cost, "completion_token_cost": completion_cost}


config = Config()
