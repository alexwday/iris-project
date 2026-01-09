"""
Environment Configuration Manager for Document Refresh Pipeline.

Centralized environment variable management. Loads configuration from
environment variables with type conversions and validation.

Supports both local and NAS file source modes via FILE_SOURCE_MODE.
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

    # Environment mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    DEV_MODE: bool = os.getenv("IRIS_DEV_MODE", "").lower() == "true"

    # File Source Configuration
    FILE_SOURCE_MODE: str = os.getenv("FILE_SOURCE_MODE", "local")  # "local" or "nas"

    # NAS Configuration (only used when FILE_SOURCE_MODE=nas)
    NAS_IP: str = os.getenv("NAS_IP", "")
    NAS_SHARE: str = os.getenv("NAS_SHARE", "")
    NAS_USER: str = os.getenv("NAS_USER", "")
    NAS_PASSWORD: str = os.getenv("NAS_PASSWORD", "")
    NAS_PORT: int = int(os.getenv("NAS_PORT", "445") or "445")

    # Input Configuration
    BASE_PATH: str = os.getenv("BASE_PATH", "")
    DATABASE_NAMES: str = os.getenv("DATABASE_NAMES", "")

    # Database Configuration
    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    # OAuth Configuration (for RBC environment)
    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    # LLM Configuration
    RBC_BASE_URL: str = os.getenv("AZURE_BASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "gpt-4.1-mini")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "gpt-4.1")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "text-embedding-3-large")

    MODEL_SMALL_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_PROMPT_COST", "0.40") or "0.40"
    )
    MODEL_SMALL_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_SMALL_COMPLETION_COST", "1.60") or "1.60"
    )
    MODEL_LARGE_PROMPT_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_PROMPT_COST", "2.50") or "2.50"
    )
    MODEL_LARGE_COMPLETION_COST: float = float(
        os.getenv("IRIS_MODEL_LARGE_COMPLETION_COST", "10.00") or "10.00"
    )
    MODEL_EMBEDDING_COST: float = float(
        os.getenv("IRIS_MODEL_EMBEDDING_COST", "0.13") or "0.13"
    )

    # Request Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120") or "120")
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3") or "3")
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "5") or "5")

    # Refresh Configuration
    REFRESH_LOG_PATH: str = os.getenv("REFRESH_LOG_PATH", "")
    REFRESH_DRY_RUN: bool = os.getenv("REFRESH_DRY_RUN", "").lower() == "true"
    REFRESH_FORCE: bool = os.getenv("REFRESH_FORCE", "").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "INFO")
    TOKEN_PREVIEW_LENGTH: int = int(os.getenv("IRIS_TOKEN_PREVIEW_LENGTH", "10") or "10")

    # SSL Configuration
    USE_SSL: bool = os.getenv("USE_SSL", "").lower() != "false"
    IS_RBC_ENV: bool = ENVIRONMENT == "rbc"

    @classmethod
    def get_database_names(cls) -> list[str]:
        """
        Get list of database names to process.

        Returns:
            List of database folder names.
        """
        if not cls.DATABASE_NAMES:
            return []
        return [name.strip() for name in cls.DATABASE_NAMES.split(",") if name.strip()]

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are set.

        Returns:
            bool: True if all required values are set, False otherwise.
        """
        missing_fields = []

        # Always required
        if not cls.BASE_PATH:
            missing_fields.append("BASE_PATH")
        if not cls.DATABASE_NAMES:
            missing_fields.append("DATABASE_NAMES")

        # Database always required
        if not cls.DB_HOST:
            missing_fields.append("VECTOR_POSTGRES_DB_HOST")

        # NAS mode requirements
        if cls.FILE_SOURCE_MODE == "nas":
            if not cls.NAS_IP:
                missing_fields.append("NAS_IP")
            if not cls.NAS_SHARE:
                missing_fields.append("NAS_SHARE")
            if not cls.NAS_USER:
                missing_fields.append("NAS_USER")
            if not cls.NAS_PASSWORD:
                missing_fields.append("NAS_PASSWORD")

        # LLM requirements (need either RBC or OpenAI)
        if not cls.RBC_BASE_URL and not cls.OPENAI_API_KEY:
            missing_fields.append("AZURE_BASE_URL or OPENAI_API_KEY")

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
            dict: Database connection parameters.
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

        Args:
            capability: Model capability type.

        Returns:
            dict: Model configuration with name and costs.

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
                cls.MODEL_EMBEDDING_COST,
                0.0,
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
