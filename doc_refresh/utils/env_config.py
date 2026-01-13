"""Centralized environment configuration for the doc_refresh pipeline."""

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
    """Return a boolean environment variable value."""
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
    """Return an integer environment variable value."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid integer %s=%s; default %s.", name, raw, default)
        return default


def parse_float_env_var(name: str, default: float = 0.0) -> float:
    """Return a float environment variable value."""
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

    # Environment mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    DEV_MODE: bool = parse_bool_env_var("IRIS_DEV_MODE")

    # Database configuration
    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    # OAuth configuration (RBC)
    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    # LLM configuration
    RBC_BASE_URL: str = os.getenv("AZURE_BASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BASE_URL = RBC_BASE_URL or os.getenv("OPENAI_BASE_URL") or None

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "gpt-4.1-mini")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "gpt-4.1")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "text-embedding-3-large")

    MODEL_SMALL_PROMPT_COST: float = parse_float_env_var(
        "IRIS_MODEL_SMALL_PROMPT_COST", 0.40
    )
    MODEL_SMALL_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_SMALL_COMPLETION_COST", 1.60
    )
    MODEL_LARGE_PROMPT_COST: float = parse_float_env_var(
        "IRIS_MODEL_LARGE_PROMPT_COST", 2.50
    )
    MODEL_LARGE_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_LARGE_COMPLETION_COST", 10.00
    )
    MODEL_EMBEDDING_PROMPT_COST: float = parse_float_env_var(
        "IRIS_MODEL_EMBEDDING_PROMPT_COST", 0.13
    )
    MODEL_EMBEDDING_COMPLETION_COST: float = parse_float_env_var(
        "IRIS_MODEL_EMBEDDING_COMPLETION_COST", 0.0
    )
    MODEL_EMBEDDING_COST: float = parse_float_env_var(
        "IRIS_MODEL_EMBEDDING_COST", 0.13
    )

    # Request configuration
    REQUEST_TIMEOUT: int = parse_int_env_var("REQUEST_TIMEOUT", 120)
    MAX_RETRY_ATTEMPTS: int = parse_int_env_var("MAX_RETRY_ATTEMPTS", 3)
    RETRY_DELAY_SECONDS: int = parse_int_env_var("RETRY_DELAY_SECONDS", 5)

    # Prompt/history configuration
    MAX_HISTORY_LENGTH: int = parse_int_env_var("IRIS_MAX_HISTORY_LENGTH")
    INCLUDE_SYSTEM_MESSAGES: bool = parse_bool_env_var("IRIS_INCLUDE_SYSTEM_MESSAGES")
    MAX_DATABASES_PER_QUERY: int = parse_int_env_var("IRIS_MAX_DATABASES_PER_QUERY")
    SHOW_USAGE_SUMMARY: bool = parse_bool_env_var("IRIS_SHOW_USAGE_SUMMARY")

    # Process monitoring / misc
    PROCESS_MONITOR_MODEL_NAME: str = os.getenv("IRIS_PROCESS_MONITOR_MODEL_NAME", "")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")
    TOKEN_PREVIEW_LENGTH: int = parse_int_env_var("IRIS_TOKEN_PREVIEW_LENGTH", 10)
    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "INFO")
    ALLOWED_ROLES: tuple[str, ...] = ("user", "assistant")
    BASE_PATH: str = os.getenv("BASE_PATH", "")
    DATABASE_NAMES: str = os.getenv("DATABASE_NAMES", "")

    # File source configuration
    FILE_SOURCE_MODE: str = os.getenv("FILE_SOURCE_MODE", "local")
    NAS_IP: str = os.getenv("NAS_IP", "")
    NAS_SHARE: str = os.getenv("NAS_SHARE", "")
    NAS_USER: str = os.getenv("NAS_USER", "")
    NAS_PASSWORD: str = os.getenv("NAS_PASSWORD", "")
    NAS_PORT: int = parse_int_env_var("NAS_PORT", 445)

    # Backup / refresh configuration
    BACKUP_ENABLED: bool = parse_bool_env_var("BACKUP_ENABLED")
    BACKUP_PATH: str = os.getenv("BACKUP_PATH", "")
    REFRESH_DRY_RUN: bool = parse_bool_env_var("REFRESH_DRY_RUN")
    REFRESH_FORCE: bool = parse_bool_env_var("REFRESH_FORCE")
    REFRESH_LOG_PATH: str = os.getenv("REFRESH_LOG_PATH", "")

    # SSL configuration
    USE_SSL: bool = parse_bool_env_var("USE_SSL", True)
    IS_RBC_ENV: bool = ENVIRONMENT == "rbc"

    @classmethod
    def get_database_names(cls) -> list[str]:
        """Return list of database names to process."""
        if not cls.DATABASE_NAMES:
            return []
        return [name.strip() for name in cls.DATABASE_NAMES.split(",") if name.strip()]

    @classmethod
    def validate_required_environment(cls) -> bool:
        """Validate that all required configuration values are set (main IRIS)."""
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
    def validate(cls) -> bool:
        """Validate doc_refresh specific environment requirements."""
        missing_fields = []

        if not cls.BASE_PATH:
            missing_fields.append("BASE_PATH")
        if not cls.DATABASE_NAMES:
            missing_fields.append("DATABASE_NAMES")

        if not cls.DB_HOST:
            missing_fields.append("VECTOR_POSTGRES_DB_HOST")
        if not cls.DB_PORT:
            missing_fields.append("VECTOR_POSTGRES_DB_PORT")
        if not cls.DB_NAME:
            missing_fields.append("VECTOR_POSTGRES_DB_NAME")
        if not cls.DB_USER:
            missing_fields.append("VECTOR_POSTGRES_DB_USERNAME")
        if cls.DB_PASSWORD in ("", None):
            missing_fields.append("VECTOR_POSTGRES_DB_PASSWORD")

        if cls.FILE_SOURCE_MODE.lower() == "nas":
            if not cls.NAS_IP:
                missing_fields.append("NAS_IP")
            if not cls.NAS_SHARE:
                missing_fields.append("NAS_SHARE")
            if not cls.NAS_USER:
                missing_fields.append("NAS_USER")
            if not cls.NAS_PASSWORD:
                missing_fields.append("NAS_PASSWORD")

        if not cls.RBC_BASE_URL and not cls.OPENAI_API_KEY:
            missing_fields.append("AZURE_BASE_URL or OPENAI_API_KEY")

        if cls.BACKUP_ENABLED and not cls.BACKUP_PATH:
            missing_fields.append("BACKUP_PATH (required when BACKUP_ENABLED=true)")

        if missing_fields:
            logger.error(
                "Missing required environment variables: %s", ", ".join(missing_fields)
            )
            return False

        logger.info("All required configuration values are set")
        return True

    @classmethod
    def get_database_params(cls) -> dict:
        """Return database connection parameters."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }

    @classmethod
    def get_model_settings(cls, capability: str) -> dict:
        """Return model configuration for a capability."""
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

    @classmethod
    def get_model_config(cls, capability: str) -> dict:
        """Alias for get_model_settings (doc_refresh compatibility)."""
        return cls.get_model_settings(capability)


config = Config()
