"""Centralized environment configuration for the doc_refresh pipeline."""

import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


def _bool(name: str, default: bool = False) -> bool:
    """Parse boolean env var (expects 'true'/'false' or '1'/'0')."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1")


def _int(name: str, default: int = 0) -> int:
    """Parse integer env var."""
    raw = os.getenv(name)
    if not raw or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer %s=%s; using default %s", name, raw, default)
        return default


def _float(name: str, default: float = 0.0) -> float:
    """Parse float env var."""
    raw = os.getenv(name)
    if not raw or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float %s=%s; using default %s", name, raw, default)
        return default


class Config:
    """Centralized configuration from environment variables."""

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    DEV_MODE: bool = _bool("IRIS_DEV_MODE")

    DB_HOST: str = os.getenv("VECTOR_POSTGRES_DB_HOST", "")
    DB_PORT: str = os.getenv("VECTOR_POSTGRES_DB_PORT", "")
    DB_NAME: str = os.getenv("VECTOR_POSTGRES_DB_NAME", "")
    DB_USER: str = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "")
    DB_PASSWORD: str = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

    OAUTH_URL: str = os.getenv("OAUTH_URL", "")
    OAUTH_CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")

    RBC_BASE_URL: str = os.getenv("AZURE_BASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BASE_URL: str = RBC_BASE_URL or os.getenv("OPENAI_BASE_URL") or ""

    MODEL_SMALL: str = os.getenv("IRIS_MODEL_SMALL", "gpt-4.1-mini")
    MODEL_LARGE: str = os.getenv("IRIS_MODEL_LARGE", "gpt-4.1")
    MODEL_EMBEDDING: str = os.getenv("IRIS_MODEL_EMBEDDING", "text-embedding-3-large")

    MODEL_SMALL_PROMPT_COST: float = _float("IRIS_MODEL_SMALL_PROMPT_COST", 0.40)
    MODEL_SMALL_COMPLETION_COST: float = _float("IRIS_MODEL_SMALL_COMPLETION_COST", 1.60)
    MODEL_LARGE_PROMPT_COST: float = _float("IRIS_MODEL_LARGE_PROMPT_COST", 2.50)
    MODEL_LARGE_COMPLETION_COST: float = _float("IRIS_MODEL_LARGE_COMPLETION_COST", 10.00)
    MODEL_EMBEDDING_PROMPT_COST: float = _float("IRIS_MODEL_EMBEDDING_PROMPT_COST", 0.13)
    MODEL_EMBEDDING_COMPLETION_COST: float = _float("IRIS_MODEL_EMBEDDING_COMPLETION_COST", 0.0)
    MODEL_EMBEDDING_COST: float = _float("IRIS_MODEL_EMBEDDING_COST", 0.13)

    REQUEST_TIMEOUT: int = _int("REQUEST_TIMEOUT", 120)
    MAX_RETRY_ATTEMPTS: int = _int("MAX_RETRY_ATTEMPTS", 3)
    RETRY_DELAY_SECONDS: int = _int("RETRY_DELAY_SECONDS", 5)

    MAX_HISTORY_LENGTH: int = _int("IRIS_MAX_HISTORY_LENGTH")  # 0 = unlimited
    INCLUDE_SYSTEM_MESSAGES: bool = _bool("IRIS_INCLUDE_SYSTEM_MESSAGES")
    MAX_DATABASES_PER_QUERY: int = _int("IRIS_MAX_DATABASES_PER_QUERY")
    SHOW_USAGE_SUMMARY: bool = _bool("IRIS_SHOW_USAGE_SUMMARY")

    PROCESS_MONITOR_MODEL_NAME: str = os.getenv("IRIS_PROCESS_MONITOR_MODEL_NAME", "")
    S3_BASE_PATH: str = os.getenv("S3_BASE_PATH", "")
    TOKEN_PREVIEW_LENGTH: int = _int("IRIS_TOKEN_PREVIEW_LENGTH", 10)
    LOG_LEVEL: str = os.getenv("IRIS_LOG_LEVEL", "INFO")
    ALLOWED_ROLES: tuple[str, ...] = ("user", "assistant")
    BASE_PATH: str = os.getenv("BASE_PATH", "")
    DATABASE_NAMES: str = os.getenv("DATABASE_NAMES", "")

    FILE_SOURCE_MODE: str = os.getenv("FILE_SOURCE_MODE", "local")
    NAS_IP: str = os.getenv("NAS_IP", "")
    NAS_SHARE: str = os.getenv("NAS_SHARE", "")
    NAS_USER: str = os.getenv("NAS_USER", "")
    NAS_PASSWORD: str = os.getenv("NAS_PASSWORD", "")
    NAS_PORT: int = _int("NAS_PORT", 445)

    OUTPUT_PATH: str = os.getenv("OUTPUT_PATH", "")
    AUDIT_PATH: str = os.getenv("AUDIT_PATH", "")

    BACKUP_ENABLED: bool = _bool("BACKUP_ENABLED")
    BACKUP_PATH: str = os.getenv("BACKUP_PATH", "")
    REFRESH_DRY_RUN: bool = _bool("REFRESH_DRY_RUN")
    REFRESH_FORCE: bool = _bool("REFRESH_FORCE")
    REFRESH_LOG_PATH: str = os.getenv("REFRESH_LOG_PATH", "")

    USE_SSL: bool = _bool("USE_SSL", True)
    IS_RBC_ENV: bool = ENVIRONMENT == "rbc"

    @classmethod
    def get_database_names(cls) -> list[str]:
        """Return list of database names to process."""
        if not cls.DATABASE_NAMES:
            return []
        return [n.strip() for n in cls.DATABASE_NAMES.split(",") if n.strip()]

    @classmethod
    def discover_database_names(cls, file_source: "Any") -> "list[str]":
        """
        Discover database names from file source subfolders.

        When DATABASE_NAMES is set, uses it as a filter against discovered folders.
        When DATABASE_NAMES is empty, returns all discovered subfolders.

        Args:
            file_source: FileSource instance with list_subfolders() method.

        Returns:
            List of database names to process.
        """
        discovered = file_source.list_subfolders()
        configured = cls.get_database_names()

        if configured:
            filtered = [d for d in discovered if d in configured]
            logger.info(
                "Filtered discovered folders by DATABASE_NAMES: %d of %d match",
                len(filtered),
                len(discovered),
            )
            return filtered

        logger.info("Auto-discovered %d database folders: %s", len(discovered), discovered)
        return discovered

    @classmethod
    def validate(cls) -> bool:
        """Validate doc_refresh specific environment requirements."""
        missing = []

        if not cls.BASE_PATH:
            missing.append("BASE_PATH")
        if not cls.DB_HOST:
            missing.append("VECTOR_POSTGRES_DB_HOST")
        if not cls.DB_PORT:
            missing.append("VECTOR_POSTGRES_DB_PORT")
        if not cls.DB_NAME:
            missing.append("VECTOR_POSTGRES_DB_NAME")
        if not cls.DB_USER:
            missing.append("VECTOR_POSTGRES_DB_USERNAME")
        if not cls.DB_PASSWORD:
            missing.append("VECTOR_POSTGRES_DB_PASSWORD")

        if cls.FILE_SOURCE_MODE.lower() == "nas":
            if not cls.NAS_IP:
                missing.append("NAS_IP")
            if not cls.NAS_SHARE:
                missing.append("NAS_SHARE")
            if not cls.NAS_USER:
                missing.append("NAS_USER")
            if not cls.NAS_PASSWORD:
                missing.append("NAS_PASSWORD")

        if not cls.RBC_BASE_URL and not cls.OPENAI_API_KEY:
            missing.append("AZURE_BASE_URL or OPENAI_API_KEY")

        if not cls.OUTPUT_PATH:
            logger.warning("OUTPUT_PATH not set - PDF output copies will be skipped")

        if cls.AUDIT_PATH:
            logger.info("AUDIT_PATH set - LLM decision audit trail will be written to %s", cls.AUDIT_PATH)

        if cls.BACKUP_ENABLED and not cls.BACKUP_PATH:
            missing.append("BACKUP_PATH (required when BACKUP_ENABLED=true)")

        if missing:
            logger.error("Missing required environment variables: %s", ", ".join(missing))
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
        """Return model configuration for a capability (small/large/embedding)."""
        configs = {
            "small": (cls.MODEL_SMALL, cls.MODEL_SMALL_PROMPT_COST, cls.MODEL_SMALL_COMPLETION_COST),
            "large": (cls.MODEL_LARGE, cls.MODEL_LARGE_PROMPT_COST, cls.MODEL_LARGE_COMPLETION_COST),
            "embedding": (cls.MODEL_EMBEDDING, cls.MODEL_EMBEDDING_PROMPT_COST, cls.MODEL_EMBEDDING_COMPLETION_COST),
        }
        if capability not in configs:
            raise ValueError(f"Unknown capability: {capability}. Use: small, large, embedding")
        name, prompt_cost, completion_cost = configs[capability]
        return {"name": name, "prompt_token_cost": prompt_cost, "completion_token_cost": completion_cost}

    @classmethod
    def get_model_config(cls, capability: str) -> dict:
        """Alias for get_model_settings."""
        return cls.get_model_settings(capability)


config = Config()
