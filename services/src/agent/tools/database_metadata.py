"""Cached access to database metadata from iris_database_registry."""

import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import text

from config.config import Config
from ...connections.postgres import get_database_session

logger = logging.getLogger(__name__)


class DatabaseNotFoundError(Exception):
    """Exception raised when a database is not found in the registry."""


class DatabaseMetadataCache:
    """Repository for database metadata with a configurable cache TTL."""

    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize the repository.

        Args:
            cache_ttl_seconds: Seconds to retain cached metadata (default 5 minutes).
        """
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = cache_ttl_seconds

    def _is_cache_valid(self) -> bool:
        """Check whether cached metadata is still within the TTL.

        Returns:
            bool: True when cached metadata exists and has not expired.
        """
        if self._cache is None or self._cache_timestamp is None:
            return False
        return (time.time() - self._cache_timestamp) < self._cache_ttl

    def invalidate_cache(self) -> None:
        """Force cache refresh on next query."""
        self._cache = None
        self._cache_timestamp = None

    def _fetch_from_database(self) -> Dict[str, Dict[str, Any]]:
        """Fetch enabled databases from iris_database_registry.

        Returns:
            Mapping of db_source to configuration details.

        Raises:
            RuntimeError: If the database query fails.
        """
        try:
            with get_database_session() as session:
                rows = (
                    session.execute(
                        text(
                            """
                            SELECT
                                db_source,
                                db_name,
                                db_summary,
                                db_description,
                                batch_size,
                                max_selected_files,
                                top_chunks_in_catalog_selection,
                                top_chunks_in_metadata_research,
                                page_threshold_for_full_content,
                                enable_db_wide_deep_research,
                                max_parallel_files,
                                max_chunks_per_file,
                                max_pages_for_full_context,
                                max_primary_section_page_count,
                                max_subsection_page_count,
                                max_neighbour_chunks,
                                max_gap_fill_pages,
                                metadata_context_fields,
                                sample_questions,
                                ad_groups,
                                enabled
                            FROM iris_database_registry
                            WHERE enabled = true
                            ORDER BY db_source
                        """
                        )
                    )
                    .mappings()
                    .all()
                )

            databases = {
                row["db_source"]: {
                    "name": row["db_name"],
                    "description": row["db_summary"],
                    "db_description": row["db_description"],
                    # Individual research config fields
                    "batch_size": row["batch_size"],
                    "max_selected_files": row["max_selected_files"],
                    "top_chunks_in_catalog_selection": row["top_chunks_in_catalog_selection"],
                    "top_chunks_in_metadata_research": row["top_chunks_in_metadata_research"],
                    "page_threshold_for_full_content": row["page_threshold_for_full_content"],
                    "enable_db_wide_deep_research": row["enable_db_wide_deep_research"],
                    "max_parallel_files": row["max_parallel_files"],
                    "max_chunks_per_file": row["max_chunks_per_file"],
                    "max_pages_for_full_context": row["max_pages_for_full_context"],
                    "max_primary_section_page_count": row["max_primary_section_page_count"],
                    "max_subsection_page_count": row["max_subsection_page_count"],
                    "max_neighbour_chunks": row["max_neighbour_chunks"],
                    "max_gap_fill_pages": row["max_gap_fill_pages"],
                    "metadata_context_fields": row["metadata_context_fields"] or ["document_summary"],
                    "sample_questions": row["sample_questions"] or [],
                    "ad_groups": row["ad_groups"] or [],
                    "enabled": row["enabled"],
                }
                for row in rows
            }

            logger.info(
                "Loaded %d databases from iris_database_registry", len(databases)
            )
            return databases
        except Exception as exc:
            logger.error("Failed to fetch database metadata: %s", exc, exc_info=True)
            raise RuntimeError(f"Database metadata fetch failed: {exc}") from exc

    def get_all_databases(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """Return enabled databases with full configuration.

        Args:
            use_cache: Whether to return cached data when valid.

        Returns:
            Dict mapping db_source to database configuration.
        """
        if use_cache and self._is_cache_valid():
            return self._cache

        self._cache = self._fetch_from_database()
        self._cache_timestamp = time.time()
        return self._cache

    def get_database_config(self, db_source: str) -> Optional[Dict[str, Any]]:
        """Return configuration for a specific database.

        Args:
            db_source: Database identifier (for example, 'internal_capm').

        Returns:
            Database configuration, or None if not found.
        """
        databases = self.get_all_databases()
        return databases.get(db_source)

    def get_research_config(self, db_source: str) -> Dict[str, Any]:
        """Return research configuration for a specific database.

        Args:
            db_source: Database identifier.

        Returns:
            Research configuration dict assembled from individual registry fields.

        Raises:
            DatabaseNotFoundError: If database is not found.
        """
        db_config = self.get_database_config(db_source)
        if db_config is None:
            raise DatabaseNotFoundError(
                f"Database '{db_source}' not found in iris_database_registry"
            )
        # Return individual fields as a dict for backward compatibility
        return {
            "batch_size": db_config["batch_size"],
            "max_selected_files": db_config["max_selected_files"],
            "top_chunks_in_catalog_selection": db_config["top_chunks_in_catalog_selection"],
            "top_chunks_in_metadata_research": db_config["top_chunks_in_metadata_research"],
            "page_threshold_for_full_content": db_config["page_threshold_for_full_content"],
            "enable_db_wide_deep_research": db_config["enable_db_wide_deep_research"],
            "max_parallel_files": db_config["max_parallel_files"],
            "max_chunks_per_file": db_config["max_chunks_per_file"],
            "max_pages_for_full_context": db_config["max_pages_for_full_context"],
            "max_primary_section_page_count": db_config["max_primary_section_page_count"],
            "max_subsection_page_count": db_config["max_subsection_page_count"],
            "max_neighbour_chunks": db_config["max_neighbour_chunks"],
            "max_gap_fill_pages": db_config["max_gap_fill_pages"],
            "metadata_context_fields": db_config["metadata_context_fields"],
        }

    def is_database_enabled(self, db_source: str) -> bool:
        """Check whether a database exists and is enabled.

        Args:
            db_source: Database identifier.

        Returns:
            bool: True if the database exists and is enabled.
        """
        db_config = self.get_database_config(db_source)
        return db_config is not None and db_config.get("enabled", False)


_REPOSITORY_CACHE: Dict[str, DatabaseMetadataCache] = {}


def get_metadata_repository() -> DatabaseMetadataCache:
    """Return the singleton repository instance.

    Returns:
        DatabaseMetadataCache instance.
    """
    if "instance" not in _REPOSITORY_CACHE:
        _REPOSITORY_CACHE["instance"] = DatabaseMetadataCache()
    return _REPOSITORY_CACHE["instance"]


def fetch_available_databases() -> Dict[str, Dict[str, Any]]:
    """Return available databases enriched for API consumers.

    Combines registry metadata with AD group mapping and sample questions.

    Returns:
        Dict mapping db_source to database configuration with ad_group and questions.
    """
    app_config = Config()

    db_to_ad_group: Dict[str, str] = {
        db_name: ad_group.strip()
        for ad_group, db_list in app_config.get_ad_group_to_db_mapping().items()
        for db_name in db_list
    }

    enriched_databases: Dict[str, Dict[str, Any]] = {}
    for db_name, db_info in get_metadata_repository().get_all_databases().items():
        ad_groups = db_info.get("ad_groups") or []
        if isinstance(ad_groups, str):
            ad_groups = [ad_groups]

        default_ad_group = ad_groups[0] if ad_groups else None

        enriched_databases[db_name] = {
            **db_info,
            "ad_group": db_to_ad_group.get(db_name, default_ad_group),
            "questions": db_info.get("sample_questions") or [],
        }

    return enriched_databases
