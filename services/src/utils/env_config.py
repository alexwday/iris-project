"""
Environment Configuration Manager

Centralized environment variable management for the IRIS project.
Loads configuration from environment variables with type conversions
and validation.

Functions:
    None (module provides Config class and config singleton)

Classes:
    Config: Centralized configuration with all settings as class attributes
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
    """
    Centralized configuration from environment variables.

    All values loaded at import time. Use validate() to check required fields.
    """

    ENVIRONMENT: str = "rbc"

    RBC_BASE_URL: str = os.getenv("AZURE_BASE_URL", "")

    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    DEV_MODE: bool = os.getenv("IRIS_DEV_MODE", "").lower() == "true"

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "0") or "0")
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "0") or "0")
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "0") or "0")

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "")

    MODEL_SMALL_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_PROMPT_COST", "0") or "0"
    )
    MODEL_SMALL_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_COMPLETION_COST", "0") or "0"
    )
    MODEL_LARGE_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_PROMPT_COST", "0") or "0"
    )
    MODEL_LARGE_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_COMPLETION_COST", "0") or "0"
    )
    MODEL_EMBEDDING_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_EMBEDDING_PROMPT_COST", "0") or "0"
    )
    MODEL_EMBEDDING_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_EMBEDDING_COMPLETION_COST", "0") or "0"
    )

    MAX_HISTORY_LENGTH: int = int(os.getenv("IRIS_MAX_HISTORY_LENGTH", "0") or "0")
    INCLUDE_SYSTEM_MESSAGES: bool = (
        os.getenv("IRIS_INCLUDE_SYSTEM_MESSAGES", "").lower() == "true"
    )

    MAX_DATABASES_PER_QUERY: int = int(
        os.getenv("IRIS_MAX_DATABASES_PER_QUERY", "0") or "0"
    )

    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "")
    TOKEN_PREVIEW_LENGTH: int = int(os.getenv("IRIS_TOKEN_PREVIEW_LENGTH", "0") or "0")
    SHOW_USAGE_SUMMARY: bool = (
        os.getenv("IRIS_SHOW_USAGE_SUMMARY", "").lower() == "true"
    )

    PROCESS_MONITOR_MODEL_NAME: str = os.getenv("IRIS_PROCESS_MONITOR_MODEL_NAME", "")

    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")

    ALLOWED_ROLES: list = ["user", "assistant"]
    USE_SSL: bool = True
    USE_OAUTH: bool = True
    IS_RBC_ENV: bool = True

    BASE_URL: str = RBC_BASE_URL

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are set.

        Returns:
            bool: True if all required values are set, False otherwise
        """
        required_str_fields = [
            ("AZURE_BASE_URL", cls.RBC_BASE_URL),
            ("VECTOR_POSTGRES_DB_HOST", cls.DB_HOST),
            ("VECTOR_POSTGRES_DB_PORT", cls.DB_PORT),
            ("VECTOR_POSTGRES_DB_NAME", cls.DB_NAME),
            ("VECTOR_POSTGRES_DB_USERNAME", cls.DB_USER),
            ("VECTOR_POSTGRES_DB_PASSWORD", cls.DB_PASSWORD),
            ("OAUTH_URL", cls.OAUTH_URL),
            ("CLIENT_ID", cls.OAUTH_CLIENT_ID),
            ("CLIENT_SECRET", cls.OAUTH_CLIENT_SECRET),
            ("IRIS_MODEL_SMALL", cls.MODEL_SMALL),
            ("IRIS_MODEL_LARGE", cls.MODEL_LARGE),
            ("IRIS_MODEL_EMBEDDING", cls.MODEL_EMBEDDING),
            ("IRIS_LOG_LEVEL", cls.LOG_LEVEL),
            ("IRIS_PROCESS_MONITOR_MODEL_NAME", cls.PROCESS_MONITOR_MODEL_NAME),
        ]

        required_int_fields = [
            ("REQUEST_TIMEOUT", cls.REQUEST_TIMEOUT),
            ("MAX_RETRY_ATTEMPTS", cls.MAX_RETRY_ATTEMPTS),
            ("RETRY_DELAY_SECONDS", cls.RETRY_DELAY_SECONDS),
            ("IRIS_MAX_HISTORY_LENGTH", cls.MAX_HISTORY_LENGTH),
            ("IRIS_MAX_DATABASES_PER_QUERY", cls.MAX_DATABASES_PER_QUERY),
            ("IRIS_TOKEN_PREVIEW_LENGTH", cls.TOKEN_PREVIEW_LENGTH),
        ]

        missing_fields = []
        for field_name, field_value in required_str_fields:
            if not field_value:
                missing_fields.append(field_name)

        for field_name, field_value in required_int_fields:
            if field_value == 0:
                missing_fields.append(field_name)

        if missing_fields:
            logger.error(
                "Missing required environment variables: %s", ", ".join(missing_fields)
            )
            return False

        logger.info("All required configuration values are set")
        return True

    @classmethod
    def get_db_params(cls) -> dict:
        """
        Get database connection parameters as a dictionary.

        Returns:
            dict: Database connection parameters
        """
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }

    @classmethod
    def get_model_config(cls, capability: str) -> dict:
        """
        Get model configuration for a capability ('small', 'large', or 'embedding').

        Raises:
            ValueError: If capability is not recognized.
        """
        configs = {
            "small": (
                cls.MODEL_SMALL,
                cls.MODEL_SMALL_PROMPT_COST,
                cls.MODEL_SMALL_COMPLETION_COST,
            ),
            "large": (
                cls.MODEL_LARGE,
                cls.MODEL_LARGE_PROMPT_COST,
                cls.MODEL_LARGE_COMPLETION_COST,
            ),
            "embedding": (
                cls.MODEL_EMBEDDING,
                cls.MODEL_EMBEDDING_PROMPT_COST,
                cls.MODEL_EMBEDDING_COMPLETION_COST,
            ),
        }
        if capability not in configs:
            raise ValueError(
                f"Unknown capability: {capability}. Use: small, large, embedding"
            )
        name, prompt_cost, completion_cost = configs[capability]
        return {
            "name": name,
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
        }


config = Config()
