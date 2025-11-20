# services/src/initial_setup/env_config.py
"""
Environment Configuration Manager

This module provides centralized environment variable management for the IRIS project.
It loads configuration from environment variables with appropriate type conversions
and validation for the RBC environment.

All configuration values are loaded as class attributes on the Config class,
making them easily accessible throughout the application.

Usage:
    from ..initial_setup.env_config import config

    # Access configuration values
    api_url = config.RBC_BASE_URL
    db_host = config.DB_HOST

Dependencies:
    - os
    - logging
    - python-dotenv (optional, for .env file support)
"""

import os
import logging
from typing import Optional, Union

# Try to import python-dotenv if available
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv not installed, use system environment variables only

logger = logging.getLogger(__name__)


class Config:
    """
    Centralized configuration class that loads all settings from environment variables.
    All settings are RBC-specific as per requirements.
    """

    # Environment Configuration
    ENVIRONMENT: str = "rbc"  # Fixed to RBC environment only

    # API Endpoints
    RBC_BASE_URL: str = os.getenv(
        "AZURE_BASE_URL",
        "https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1",
    )

    # Database Configuration
    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "5432")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    # OAuth Configuration
    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    # SSL Configuration
    SSL_CERT_FILENAME: str = os.getenv("IRIS_SSL_CERT_FILENAME", "rbc-ca-bundle.cer")
    SSL_CHECK_CERT_EXPIRY: bool = (
        os.getenv("IRIS_SSL_CHECK_CERT_EXPIRY", "true").lower() == "true"
    )
    SSL_EXPIRY_WARNING_DAYS: int = int(os.getenv("IRIS_SSL_EXPIRY_WARNING_DAYS", "30"))

    # Request Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "180"))
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "2"))

    # Model Configuration
    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "gpt-4o-mini-2024-07-18")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "gpt-4o-2024-05-13")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "text-embedding-3-large")

    MODEL_SMALL_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_PROMPT_COST", "0.00016238")
    )
    MODEL_SMALL_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_COMPLETION_COST", "0.00065175")
    )
    MODEL_LARGE_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_PROMPT_COST", "0.00064952")
    )
    MODEL_LARGE_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_COMPLETION_COST", "0.00260748")
    )
    MODEL_EMBEDDING_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_EMBEDDING_PROMPT_COST", "0.0001")
    )
    MODEL_EMBEDDING_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_EMBEDDING_COMPLETION_COST", "0.0001")
    )

    # Conversation Configuration
    MAX_HISTORY_LENGTH: int = int(os.getenv("IRIS_MAX_HISTORY_LENGTH", "10"))
    INCLUDE_SYSTEM_MESSAGES: bool = (
        os.getenv("IRIS_INCLUDE_SYSTEM_MESSAGES", "false").lower() == "true"
    )

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "DEBUG")
    TOKEN_PREVIEW_LENGTH: int = int(os.getenv("IRIS_TOKEN_PREVIEW_LENGTH", "7"))
    SHOW_USAGE_SUMMARY: bool = (
        os.getenv("IRIS_SHOW_USAGE_SUMMARY", "true").lower() == "true"
    )

    # Process Monitoring
    PROCESS_MONITOR_MODEL_NAME: str = os.getenv(
        "IRIS_PROCESS_MONITOR_MODEL_NAME", "iris"
    )

    # S3 Configuration
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")

    # Static Constants (not from environment)
    ALLOWED_ROLES: list = ["user", "assistant"]  # Roles for conversation processing
    USE_SSL: bool = True  # Always true for RBC
    USE_OAUTH: bool = True  # Always true for RBC
    IS_RBC_ENV: bool = True  # Always true (RBC-only)

    # Convenience aliases for commonly used values
    BASE_URL: str = RBC_BASE_URL  # Alias for compatibility

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are set.

        Returns:
            bool: True if all required values are set, False otherwise
        """
        required_fields = [
            ("DB_HOST", cls.DB_HOST),
            ("DB_USER", cls.DB_USER),
            ("DB_PASSWORD", cls.DB_PASSWORD),
            ("OAUTH_URL", cls.OAUTH_URL),
            ("OAUTH_CLIENT_ID", cls.OAUTH_CLIENT_ID),
            ("OAUTH_CLIENT_SECRET", cls.OAUTH_CLIENT_SECRET),
        ]

        missing_fields = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing_fields.append(f"IRIS_{field_name}")

        if missing_fields:
            logger.error(
                f"Missing required environment variables: {', '.join(missing_fields)}"
            )
            return False

        logger.debug("All required configuration values are set")
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
    def get_ssl_cert_path(cls, settings_dir: str) -> str:
        """
        Get the full path to the SSL certificate file.

        Args:
            settings_dir: Directory where the SSL certificate is located

        Returns:
            str: Full path to the SSL certificate
        """
        import os

        return os.path.join(settings_dir, cls.SSL_CERT_FILENAME)

    @classmethod
    def get_model_config(cls, capability: str) -> dict:
        """
        Get model configuration for a specific capability.

        Args:
            capability: Model capability ('small', 'large', or 'embedding')

        Returns:
            dict: Model configuration with name and costs

        Raises:
            ValueError: If capability is not recognized
        """
        if capability == "small":
            return {
                "name": cls.MODEL_SMALL,
                "prompt_token_cost": cls.MODEL_SMALL_PROMPT_COST,
                "completion_token_cost": cls.MODEL_SMALL_COMPLETION_COST,
            }
        elif capability == "large":
            return {
                "name": cls.MODEL_LARGE,
                "prompt_token_cost": cls.MODEL_LARGE_PROMPT_COST,
                "completion_token_cost": cls.MODEL_LARGE_COMPLETION_COST,
            }
        elif capability == "embedding":
            return {
                "name": cls.MODEL_EMBEDDING,
                "prompt_token_cost": cls.MODEL_EMBEDDING_PROMPT_COST,
                "completion_token_cost": cls.MODEL_EMBEDDING_COMPLETION_COST,
            }
        else:
            raise ValueError(
                f"Unknown model capability: {capability}. Available: small, large, embedding"
            )


# Create a singleton instance
config = Config()
