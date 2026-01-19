"""
Config Compatibility Wrapper

This module provides a compatibility layer between IT's config expectations
and the existing env_config module. It wraps the original Config class and
adds additional methods/properties that IT's code requires without modifying
the src code.

Usage:
    from config.config import Config
    app_config = Config()
"""

import os
import logging
import builtins
from typing import Dict, List, Any

# Import the original config from services.src
from services.src.utils.env_config import config as original_config

logger = logging.getLogger(__name__)


class Config:
    """
    Compatibility wrapper that extends the original Config with IT-specific features.

    This class delegates most attribute access to the original config while adding
    new methods and properties required by IT's infrastructure code.
    """

    def __init__(self):
        """Initialize the compatibility wrapper."""
        self._original_config = original_config
        logger.debug("Config compatibility wrapper initialized")

    def __getattr__(self, name):
        """
        Delegate attribute access to the original config.

        This allows all existing config properties to work transparently.
        """
        return getattr(self._original_config, name)

    # =========================================================================
    # IT-Specific Properties (New additions for IT's infrastructure)
    # =========================================================================

    @property
    def app_id(self) -> str:
        """
        Application identifier for IT's reporting system.

        Returns:
            str: Application ID from environment or default "iris"
        """
        return os.getenv("IRIS_APP_ID", "iris")

    @property
    def token_validation_url(self) -> str:
        """
        URL for IT's OAuth token validation service.

        For local development, this can be left empty to skip authentication.

        Returns:
            str: Token validation service URL
        """
        return os.getenv("TOKEN_VALIDATION_URL", "")

    @property
    def pii_service_url(self) -> str:
        """
        URL for IT's PII detection service.

        For local development, this can be left empty to skip PII detection.

        Returns:
            str: PII detection service URL
        """
        return os.getenv("PII_SERVICE_URL", "")

    @property
    def pii_excludes(self) -> List[str]:
        """
        List of terms to exclude from PII detection.

        Returns:
            List[str]: Terms that should not be flagged as PII
        """
        excludes_str = os.getenv("PII_EXCLUDES", "")
        if excludes_str:
            return [term.strip() for term in excludes_str.split(",")]
        return []

    def get_ad_group_to_db_mapping(self) -> Dict[str, List[str]]:
        """
        Get Active Directory group to database access mapping.

        IT's infrastructure uses AD groups to control database access.
        For local development, this returns a permissive mapping that grants
        access to all databases.

        Returns:
            Dict[str, List[str]]: Mapping of AD groups to database IDs
        """
        # For local development: grant access to all databases
        # Import here to avoid circular dependency
        try:
            from services.src.agent.tools.database_metadata import (
                get_metadata_repository,
            )

            repo = get_metadata_repository()
            all_db_ids = list(repo.get_all_databases().keys())

            # Default mapping: "all_users" group has access to everything
            default_mapping = {
                "all_users": all_db_ids,
                "local_dev": all_db_ids,
            }

            # Allow override from environment for testing specific access controls
            # Format: AD_GROUP_MAPPING=group1:db1,db2,db3;group2:db4,db5
            mapping_str = os.getenv("AD_GROUP_MAPPING", "")
            if mapping_str:
                custom_mapping = {}
                for group_mapping in mapping_str.split(";"):
                    if ":" in group_mapping:
                        group, dbs = group_mapping.split(":", 1)
                        custom_mapping[group.strip()] = [
                            db.strip() for db in dbs.split(",")
                        ]
                return custom_mapping

            return default_mapping

        except ImportError as e:
            logger.warning(f"Could not import database_metadata: {e}")
            return {"all_users": []}

    # =========================================================================
    # Pass-through methods from original config
    # =========================================================================

    def validate(self) -> bool:
        """Validate configuration (delegates to original config)."""
        return self._original_config.validate()

    def get_db_params(self) -> Dict[str, Any]:
        """Get database parameters (delegates to original config)."""
        return self._original_config.get_db_params()

    def get_ssl_cert_path(self, settings_dir: str) -> str:
        """Get SSL certificate path (delegates to original config)."""
        return self._original_config.get_ssl_cert_path(settings_dir)

    def get_model_config(self, capability: str) -> Dict[str, Any]:
        """Get model configuration (delegates to original config)."""
        return self._original_config.get_model_config(capability)


# Create a singleton instance for convenience
_config_instance = None


def get_config() -> Config:
    """
    Get or create the singleton Config instance.

    Returns:
        Config: The config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# ---------------------------------------------------------------------------
# Global compatibility shims for IT code bugs (outside services/src)
# ---------------------------------------------------------------------------

# Expose APP_ID via builtins so services.src.reporting.reporting can reference
# it without modifying IT's code (they access a bare APP_ID symbol).
builtins.APP_ID = get_config().app_id
