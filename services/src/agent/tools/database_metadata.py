"""
Database Metadata Repository Module.

Provides access to database configurations stored in the iris_database_registry
table. Replaces hardcoded AVAILABLE_DATABASES dict with database-driven approach.

Functions:
    get_repository: Get singleton repository instance
    get_database_statement: Format all databases for prompts
    get_filtered_database_statement: Format specific databases for prompts
    get_available_databases: Get enriched database configurations

Classes:
    DatabaseMetadataRepository: Caching repository for database metadata
    DatabaseNotFoundError: Exception for unknown database lookups
"""

import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from config.config import Config
from ...connections.postgres import get_session

logger = logging.getLogger(__name__)


class DatabaseNotFoundError(Exception):
    """Exception raised when a database is not found in the registry."""


class DatabaseMetadataRepository:
    """
    Repository for accessing database metadata from iris_database_registry.

    Provides caching to avoid repeated database queries within a configurable TTL.
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize the repository.

        Args:
            cache_ttl_seconds: How long to cache database metadata (default 5 min).
        """
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = cache_ttl_seconds

    def _is_cache_valid(self) -> bool:
        """
        Check if the cache is still valid.

        Returns:
            True if cache exists and is within TTL, False otherwise.
        """
        if self._cache is None or self._cache_timestamp is None:
            return False
        return (time.time() - self._cache_timestamp) < self._cache_ttl

    def invalidate_cache(self) -> None:
        """Force cache refresh on next query."""
        self._cache = None
        self._cache_timestamp = None

    def _fetch_from_database(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all enabled databases from iris_database_registry.

        Returns:
            Dict mapping db_source to database configuration.

        Raises:
            RuntimeError: If database query fails.
        """
        try:
            with get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT
                            db_source,
                            db_name,
                            db_summary,
                            db_description,
                            research_config,
                            sample_questions,
                            ad_groups,
                            enabled
                        FROM iris_database_registry
                        WHERE enabled = true
                        ORDER BY db_source
                    """
                    )
                )

                rows = result.mappings().all()

                databases = {}
                for row in rows:
                    db_source = row["db_source"]
                    databases[db_source] = {
                        "name": row["db_name"],
                        "description": row["db_summary"],
                        "db_description": row["db_description"],
                        "research_config": row["research_config"] or {},
                        "sample_questions": row["sample_questions"] or [],
                        "ad_groups": row["ad_groups"],
                        "enabled": row["enabled"],
                    }

                logger.info(
                    "Loaded %d databases from iris_database_registry", len(databases)
                )
                return databases

        except Exception as exc:
            logger.error("Failed to fetch database metadata: %s", exc, exc_info=True)
            raise RuntimeError(f"Database metadata fetch failed: {exc}") from exc

    def get_all_databases(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled databases with full configuration.

        Args:
            use_cache: Whether to use cached data if available (default True).

        Returns:
            Dict mapping db_source to database configuration.
        """
        if use_cache and self._is_cache_valid():
            return self._cache

        self._cache = self._fetch_from_database()
        self._cache_timestamp = time.time()
        return self._cache

    def get_database_config(self, db_source: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific database.

        Args:
            db_source: The database identifier (e.g., 'internal_capm').

        Returns:
            Database configuration dict, or None if not found.
        """
        databases = self.get_all_databases()
        return databases.get(db_source)

    def get_research_config(self, db_source: str) -> Dict[str, Any]:
        """
        Get research_config JSONB for a specific database.

        Args:
            db_source: The database identifier.

        Returns:
            Research configuration dict from the registry.

        Raises:
            DatabaseNotFoundError: If database not found in registry.
        """
        db_config = self.get_database_config(db_source)
        if db_config is None:
            raise DatabaseNotFoundError(
                f"Database '{db_source}' not found in iris_database_registry"
            )
        return db_config.get("research_config", {})

    def get_database_names(self) -> List[str]:
        """
        Get list of all enabled database source identifiers.

        Returns:
            List of db_source strings.
        """
        databases = self.get_all_databases()
        return list(databases.keys())

    def is_database_enabled(self, db_source: str) -> bool:
        """
        Check if a specific database is enabled.

        Args:
            db_source: The database identifier.

        Returns:
            True if database exists and is enabled, False otherwise.
        """
        db_config = self.get_database_config(db_source)
        return db_config is not None and db_config.get("enabled", False)


_REPOSITORY_CACHE: Dict[str, DatabaseMetadataRepository] = {}


def get_repository() -> DatabaseMetadataRepository:
    """
    Get the singleton repository instance.

    Returns:
        DatabaseMetadataRepository instance.
    """
    if "instance" not in _REPOSITORY_CACHE:
        _REPOSITORY_CACHE["instance"] = DatabaseMetadataRepository()
    return _REPOSITORY_CACHE["instance"]


def _format_database_xml(db_name: str, db_info: Dict[str, Any]) -> str:
    """
    Format a single database entry as XML for prompts.

    Args:
        db_name: The database identifier.
        db_info: The database configuration dict.

    Returns:
        XML-formatted string for the database.
    """
    return f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
  <USAGE>{db_info.get('db_description', '')}</USAGE>
</DATABASE>
"""


def get_database_statement() -> str:
    """
    Return a formatted statement about available databases for use in agent prompts.

    Uses XML-style delimiters for better sectioning.

    Returns:
        Formatted statement describing available databases.
    """
    repo = get_repository()
    all_databases = repo.get_all_databases()

    internal_dbs = {k: v for k, v in all_databases.items() if k.startswith("internal_")}
    external_dbs = {k: v for k, v in all_databases.items() if k.startswith("external_")}

    statement = """<AVAILABLE_DATABASES>
The following databases are available for research:

"""

    statement += "<INTERNAL_DATABASES>\n"
    for db_name, db_info in internal_dbs.items():
        statement += _format_database_xml(db_name, db_info)
        statement += "\n"
    statement += "</INTERNAL_DATABASES>\n\n"

    statement += "<EXTERNAL_DATABASES>\n"
    for db_name, db_info in external_dbs.items():
        statement += _format_database_xml(db_name, db_info)
        statement += "\n"
    statement += "</EXTERNAL_DATABASES>\n"
    statement += "</AVAILABLE_DATABASES>"

    return statement


def get_filtered_database_statement(db_names: List[str]) -> str:
    """
    Return a formatted statement about specific databases for use in agent prompts.

    Only includes databases in the provided list.

    Args:
        db_names: List of database source identifiers to include.

    Returns:
        Formatted statement describing selected databases.
    """
    repo = get_repository()
    all_databases = repo.get_all_databases()

    filtered_dbs = {k: v for k, v in all_databases.items() if k in db_names}

    if not filtered_dbs:
        return (
            "<AVAILABLE_DATABASES>"
            "No databases selected for this query."
            "</AVAILABLE_DATABASES>"
        )

    internal_dbs = {k: v for k, v in filtered_dbs.items() if k.startswith("internal_")}
    external_dbs = {k: v for k, v in filtered_dbs.items() if k.startswith("external_")}

    statement = """<AVAILABLE_DATABASES>
The following databases have been selected for this research:

"""

    if internal_dbs:
        statement += "<INTERNAL_DATABASES>\n"
        for db_name, db_info in internal_dbs.items():
            statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
</DATABASE>
"""
        statement += "</INTERNAL_DATABASES>\n\n"

    if external_dbs:
        statement += "<EXTERNAL_DATABASES>\n"
        for db_name, db_info in external_dbs.items():
            statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
</DATABASE>
"""
        statement += "</EXTERNAL_DATABASES>\n"

    statement += "</AVAILABLE_DATABASES>"

    return statement


def get_available_databases() -> Dict[str, Dict[str, Any]]:
    """
    Return the dictionary of available databases from iris_database_registry.

    Enriches database configs with AD group and sample questions for API use.

    Returns:
        Dict mapping db_source to database configuration with ad_group and questions.
    """
    app_config = Config()

    repo = get_repository()
    all_databases = repo.get_all_databases()

    ad_group_to_db_mapping = app_config.get_ad_group_to_db_mapping()

    db_to_ad_group: Dict[str, str] = {}
    for ad_group, db_list in ad_group_to_db_mapping.items():
        for db_name in db_list:
            db_to_ad_group[db_name] = ad_group.strip()

    logger.info("Database to AD group mapping: %s", db_to_ad_group)

    enriched_databases = {}
    for db_name, db_info in all_databases.items():
        db_info_api = db_info.copy()

        ad_groups = db_info.get("ad_groups")
        default_ad_group = ad_groups[0] if ad_groups else None
        db_info_api["ad_group"] = db_to_ad_group.get(db_name, default_ad_group)

        db_info_api["questions"] = db_info.get("sample_questions", [])

        enriched_databases[db_name] = db_info_api

    return enriched_databases
