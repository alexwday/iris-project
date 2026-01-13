"""Centralized environment configuration for the IRIS project."""

import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

_TRUTHY_VALUES = {"1", "true", "yes", "y", "on"}
_FALSY_VALUES = {"0", "false", "no", "n", "off"}


def parse_bool_env_var(name: str, default: bool = False) -> bool:
    """Return a boolean environment variable value.

    Args:
        name: Environment variable name.
        default: Value to use if parsing fails or the variable is unset.

    Returns:
        bool: Parsed boolean value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUTHY_VALUES:
        return True
    if value in _FALSY_VALUES:
        return False
    logger.warning("Invalid boolean %s=%s; default %s.", name, raw, default)
    return default


def parse_int_env_var(name: str, default: int = 0) -> int:
    """Return an integer environment variable value.

    Args:
        name: Environment variable name.
        default: Value to use if parsing fails or the variable is unset.

    Returns:
        int: Parsed integer value.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid integer %s=%s; default %s.", name, raw, default)
        return default


def parse_float_env_var(name: str, default: float = 0.0) -> float:
    """Return a float environment variable value.

    Args:
        name: Environment variable name.
        default: Value to use if parsing fails or the variable is unset.

    Returns:
        float: Parsed float value.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid float %s=%s; default %s.", name, raw, default)
        return default


class Config:
    """Centralized configuration from environment variables."""

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

    DEV_MODE: bool = parse_bool_env_var("IRIS_DEV_MODE")

    REQUEST_TIMEOUT: int = parse_int_env_var("REQUEST_TIMEOUT")
    MAX_RETRY_ATTEMPTS: int = parse_int_env_var("MAX_RETRY_ATTEMPTS")
    RETRY_DELAY_SECONDS: int = parse_int_env_var("RETRY_DELAY_SECONDS")

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "")

    MODEL_SMALL_PROMPT_COST: float = parse_float_env_var("IRIS_MODEL_SMALL_PROMPT_COST")
    MODEL_SMALL_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_SMALL_COMPLETION_COST"
    )
    MODEL_LARGE_PROMPT_COST: float = parse_float_env_var("IRIS_MODEL_LARGE_PROMPT_COST")
    MODEL_LARGE_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_LARGE_COMPLETION_COST"
    )
    MODEL_EMBEDDING_PROMPT_COST: float = parse_float_env_var(
        "IRIS_MODEL_EMBEDDING_PROMPT_COST"
    )
    MODEL_EMBEDDING_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_EMBEDDING_COMPLETION_COST"
    )

    MAX_HISTORY_LENGTH: int = parse_int_env_var("IRIS_MAX_HISTORY_LENGTH")
    INCLUDE_SYSTEM_MESSAGES: bool = parse_bool_env_var("IRIS_INCLUDE_SYSTEM_MESSAGES")
    MAX_DATABASES_PER_QUERY: int = parse_int_env_var("IRIS_MAX_DATABASES_PER_QUERY")

    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "")
    TOKEN_PREVIEW_LENGTH: int = parse_int_env_var("IRIS_TOKEN_PREVIEW_LENGTH")
    SHOW_USAGE_SUMMARY: bool = parse_bool_env_var("IRIS_SHOW_USAGE_SUMMARY")

    PROCESS_MONITOR_MODEL_NAME: str = os.getenv("IRIS_PROCESS_MONITOR_MODEL_NAME", "")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")

    ALLOWED_ROLES: tuple[str, ...] = ("user", "assistant")
    BASE_URL: str = RBC_BASE_URL

    @classmethod
    def validate_required_environment(cls) -> bool:
        """Validate that all required configuration values are set.

        Returns:
            bool: True if all required values are set, False otherwise.
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

        missing_fields = [name for name, value in required_str_fields if not value]
        missing_fields.extend(name for name, value in required_int_fields if value == 0)

        if missing_fields:
            logger.error(
                "Missing required environment variables: %s", ", ".join(missing_fields)
            )
            return False

        logger.info("All required configuration values are set")
        return True

    @classmethod
    def get_database_params(cls) -> dict:
        """Return database connection parameters.

        Returns:
            dict[str, str]: Database connection parameters.
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
        """Return model configuration for a capability.

        Args:
            capability (str): One of `small`, `large`, or `embedding`.

        Raises:
            ValueError: If capability is not recognized.

        Returns:
            dict[str, float | str]: Model name and token cost details.
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
