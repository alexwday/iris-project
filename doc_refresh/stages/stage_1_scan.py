"""
Stage 1: Scan - Compare Input Folders Against PostgreSQL.

This stage scans input folders and compares files against the database
to determine what work needs to be done:
- Files to process (new or updated)
- Files to remove (deleted from source but still in DB)

The stage uses file hashes to detect changes, avoiding unnecessary
reprocessing of unchanged files.

Functions:
    run_stage: Execute the scan stage
    scan_folder: Scan a single database folder
    compare_with_database: Compare files against database records
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from ..connections.file_source import FileSource, get_file_source
from ..connections.postgres import get_database_session
from ..utils.env_config import config
from ..utils.xlsx_extractor import get_xlsx_sheet_names, sanitize_sheet_name

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".xlsx"]


@dataclass
class FileInfo:
    """Information about a file to process."""

    file_path: str
    relative_path: str
    file_name: str
    file_hash: str
    file_size: int
    db_source: str
    modified_time: float
    action: str = "new"  # "new" or "update"
    sheet_name: Optional[str] = None


@dataclass
class ScanResult:
    """Result of the scan stage."""

    files_to_process: List[FileInfo] = field(default_factory=list)
    files_to_remove: List[Dict] = field(default_factory=list)
    files_unchanged: int = 0
    scan_errors: List[str] = field(default_factory=list)
    databases_scanned: List[str] = field(default_factory=list)


def run_stage(
    file_source: Optional[FileSource] = None,
    database_names: Optional[List[str]] = None,
    force: bool = False,
) -> ScanResult:
    """
    Execute the scan stage.

    Scans configured database folders and compares against PostgreSQL
    to determine which files need processing.

    Args:
        file_source: Optional FileSource instance (uses default if None).
        database_names: Optional list of database names to process
            (uses config.get_database_names() if None).
        force: If True, mark all files for processing regardless of hash.

    Returns:
        ScanResult with files to process, remove, and statistics.
    """
    result = ScanResult()

    try:
        # Get file source
        if file_source is None:
            file_source = get_file_source()
            logger.info("Using file source mode: %s", config.FILE_SOURCE_MODE)

        auto_discover_mode = database_names is None and not config.get_database_names()

        if database_names is None:
            database_names = config.discover_database_names(file_source)

        if not database_names and not auto_discover_mode:
            raise ValueError(
                "No database folders found. Set DATABASE_NAMES or ensure "
                "BASE_PATH contains subdirectories."
            )

        if database_names:
            logger.info(
                "Scanning %d database folders: %s",
                len(database_names),
                database_names,
            )
        else:
            logger.info(
                "No database folders discovered. "
                "Checking for stale database records to remove."
            )

        # Scan each database folder
        for db_name in database_names:
            try:
                folder_result = scan_folder(file_source, db_name, force)

                result.files_to_process.extend(folder_result.files_to_process)
                result.files_to_remove.extend(folder_result.files_to_remove)
                result.files_unchanged += folder_result.files_unchanged
                result.scan_errors.extend(folder_result.scan_errors)
                result.databases_scanned.append(db_name)

            except Exception as exc:
                error_msg = f"Error scanning folder {db_name}: {exc}"
                logger.error(error_msg)
                result.scan_errors.append(error_msg)

        if auto_discover_mode:
            removed_db_sources = get_removed_database_sources(database_names)
            if removed_db_sources:
                logger.info(
                    "Detected %d removed database folders in source: %s",
                    len(removed_db_sources),
                    removed_db_sources,
                )

            for db_name in removed_db_sources:
                db_files = get_database_files(db_name)
                for db_file in db_files:
                    result.files_to_remove.append(
                        {
                            "db_source": db_name,
                            "file_path": db_file["file_path"],
                            "file_name": db_file.get("file_name"),
                            "document_id": db_file.get("document_id"),
                        }
                    )
                if db_files:
                    logger.info(
                        "Marked %d stale files for removal in missing folder %s",
                        len(db_files),
                        db_name,
                    )

        # Log summary
        logger.info(
            "Scan complete: %d to process, %d to remove, %d unchanged, %d errors",
            len(result.files_to_process),
            len(result.files_to_remove),
            result.files_unchanged,
            len(result.scan_errors),
        )

        return result

    except Exception as exc:
        logger.error("Stage 1 scan failed: %s", exc)
        raise


def _expand_xlsx_to_sheet_infos(
    file_info: Dict,
    file_hash: str,
    db_name: str,
    db_files_map: Dict[str, Dict],
    force: bool,
    temp_dir: str,
    file_source: FileSource,
) -> Tuple[List[FileInfo], Set[str], int]:
    """Expand one xlsx file into per-sheet FileInfo objects.

    Args:
        file_info: File dict from FileSource.list_files().
        file_hash: Pre-computed hash of the parent xlsx.
        db_name: Database source identifier.
        db_files_map: Map of relative_path -> DB record for this db_source.
        force: If True, mark all sheets for processing.
        temp_dir: Temporary directory for downloading files in NAS mode.
        file_source: FileSource instance for file access.

    Returns:
        Tuple of (sheet FileInfo list, synthetic source paths, unchanged count).
    """
    relative_path = file_info["relative_path"]
    xlsx_path = file_info["path"]
    xlsx_stem = Path(relative_path).stem
    xlsx_dir = str(Path(relative_path).parent)
    if xlsx_dir == ".":
        xlsx_dir = ""

    if config.FILE_SOURCE_MODE == "nas":
        local_xlsx = file_source.copy_to_local(xlsx_path, temp_dir)
    else:
        local_xlsx = xlsx_path

    try:
        sheet_names = get_xlsx_sheet_names(local_xlsx)
    except Exception as exc:
        logger.error(
            "Failed reading sheets from %s/%s: %s", db_name, relative_path, exc
        )
        return [], set(), 0

    if not sheet_names:
        logger.info("No non-empty sheets in %s/%s", db_name, relative_path)
        return [], set(), 0

    logger.info(
        "Expanding %s/%s into %d sheet documents",
        db_name,
        relative_path,
        len(sheet_names),
    )

    sheet_file_infos: List[FileInfo] = []
    sheet_paths: Set[str] = set()
    unchanged = 0

    for sheet_name in sheet_names:
        safe_name = sanitize_sheet_name(sheet_name)
        if xlsx_dir:
            sheet_relative = f"{xlsx_dir}/{xlsx_stem}/{safe_name}.xlsx"
        else:
            sheet_relative = f"{xlsx_stem}/{safe_name}.xlsx"
        sheet_file_name = f"{xlsx_stem} - {sheet_name}.xlsx"

        sheet_paths.add(sheet_relative)

        db_file = db_files_map.get(sheet_relative)

        if db_file is None:
            sheet_file_infos.append(
                FileInfo(
                    file_path=xlsx_path,
                    relative_path=sheet_relative,
                    file_name=sheet_file_name,
                    file_hash=file_hash,
                    file_size=file_info["size"],
                    db_source=db_name,
                    modified_time=file_info["modified_time"],
                    action="new",
                    sheet_name=sheet_name,
                )
            )
            logger.debug("New xlsx sheet: %s", sheet_relative)

        elif force:
            sheet_file_infos.append(
                FileInfo(
                    file_path=xlsx_path,
                    relative_path=sheet_relative,
                    file_name=sheet_file_name,
                    file_hash=file_hash,
                    file_size=file_info["size"],
                    db_source=db_name,
                    modified_time=file_info["modified_time"],
                    action="update",
                    sheet_name=sheet_name,
                )
            )
            logger.debug("Force reprocess xlsx sheet: %s", sheet_relative)

        else:
            db_hash = db_file.get("file_hash", "")
            if db_hash and file_hash == db_hash:
                unchanged += 1
            else:
                sheet_file_infos.append(
                    FileInfo(
                        file_path=xlsx_path,
                        relative_path=sheet_relative,
                        file_name=sheet_file_name,
                        file_hash=file_hash,
                        file_size=file_info["size"],
                        db_source=db_name,
                        modified_time=file_info["modified_time"],
                        action="update",
                        sheet_name=sheet_name,
                    )
                )
                logger.debug("Hash changed, xlsx sheet needs update: %s", sheet_relative)

    return sheet_file_infos, sheet_paths, unchanged


def scan_folder(
    file_source: FileSource,
    db_name: str,
    force: bool = False,
) -> ScanResult:
    """
    Scan a single database folder and compare with database.

    Args:
        file_source: FileSource instance for file access.
        db_name: Database name (folder name) to scan.
        force: If True, mark all files for processing.

    Returns:
        ScanResult for this folder.
    """
    result = ScanResult()
    result.databases_scanned.append(db_name)

    logger.info("Scanning folder: %s", db_name)

    # List files in the folder
    files = file_source.list_files(db_name, extensions=SUPPORTED_EXTENSIONS)
    logger.info("Found %d supported files in %s", len(files), db_name)

    if not files:
        # Check if there are files to remove from DB
        db_files = get_database_files(db_name)
        if db_files:
            logger.info(
                "No source files found but %d files exist in DB - marking for removal",
                len(db_files),
            )
            for db_file in db_files:
                result.files_to_remove.append(
                    {
                        "db_source": db_name,
                        "file_path": db_file["file_path"],
                        "document_id": db_file.get("document_id"),
                    }
                )
        return result

    db_files_list = get_database_files(db_name)
    db_files_map = {f["file_path"]: f for f in db_files_list}
    source_paths: Set[str] = set()

    with tempfile.TemporaryDirectory(prefix="scan_xlsx_") as temp_dir:
        for file_info in files:
            relative_path = file_info["relative_path"]
            file_name = file_info["name"]

            try:
                file_hash = file_source.get_file_hash(
                    f"{db_name}/{relative_path}" if config.FILE_SOURCE_MODE == "local" else file_info["path"]
                )

                is_xlsx = file_name.lower().endswith(".xlsx")

                if is_xlsx:
                    sheet_infos, sheet_paths, unchanged = _expand_xlsx_to_sheet_infos(
                        file_info=file_info,
                        file_hash=file_hash,
                        db_name=db_name,
                        db_files_map=db_files_map,
                        force=force,
                        temp_dir=temp_dir,
                        file_source=file_source,
                    )
                    result.files_to_process.extend(sheet_infos)
                    source_paths.update(sheet_paths)
                    result.files_unchanged += unchanged
                    continue

                source_paths.add(relative_path)

                db_file = db_files_map.get(relative_path)

                if db_file is None:
                    result.files_to_process.append(
                        FileInfo(
                            file_path=file_info["path"],
                            relative_path=relative_path,
                            file_name=file_name,
                            file_hash=file_hash,
                            file_size=file_info["size"],
                            db_source=db_name,
                            modified_time=file_info["modified_time"],
                            action="new",
                        )
                    )
                    logger.debug("New file: %s", file_name)

                elif force:
                    result.files_to_process.append(
                        FileInfo(
                            file_path=file_info["path"],
                            relative_path=relative_path,
                            file_name=file_name,
                            file_hash=file_hash,
                            file_size=file_info["size"],
                            db_source=db_name,
                            modified_time=file_info["modified_time"],
                            action="update",
                        )
                    )
                    logger.debug("Force reprocess: %s", file_name)

                else:
                    db_hash = db_file.get("file_hash", "")
                    if db_hash and file_hash == db_hash:
                        result.files_unchanged += 1
                    else:
                        result.files_to_process.append(
                            FileInfo(
                                file_path=file_info["path"],
                                relative_path=relative_path,
                                file_name=file_name,
                                file_hash=file_hash,
                                file_size=file_info["size"],
                                db_source=db_name,
                                modified_time=file_info["modified_time"],
                                action="update",
                            )
                        )
                        logger.debug("Hash changed, needs update: %s", file_name)

            except Exception as exc:
                error_msg = f"Error processing file {relative_path}: {exc}"
                logger.warning(error_msg)
                result.scan_errors.append(error_msg)

    for file_path, db_file in db_files_map.items():
        if file_path not in source_paths:
            result.files_to_remove.append(
                {
                    "db_source": db_name,
                    "file_path": file_path,
                    "file_name": db_file.get("file_name"),
                    "document_id": db_file.get("document_id"),
                }
            )
            logger.debug("File to remove: %s", file_path)

    logger.info(
        "Folder %s: %d new/updated, %d to remove, %d unchanged",
        db_name,
        len(result.files_to_process),
        len(result.files_to_remove),
        result.files_unchanged,
    )

    return result


def get_database_files(db_source: str) -> List[Dict]:
    """
    Get existing files from database for a specific db_source.

    Uses iris_document_metadata table (2-table design).

    Args:
        db_source: Database source identifier.

    Returns:
        List of dicts with 'document_id', 'file_path', 'file_name', 'file_hash' keys.
        Uses file_hash for change detection.
    """
    query = text(
        """
        SELECT id AS document_id, file_path, document_name AS file_name, file_hash
        FROM iris_document_metadata
        WHERE db_source = :db_source
        """
    )

    try:
        with get_database_session() as session:
            rows = session.execute(query, {"db_source": db_source}).fetchall()
            results = [
                {
                    "document_id": row._mapping.get("document_id"),
                    "file_path": row._mapping.get("file_path"),
                    "file_name": row._mapping.get("file_name"),
                    "file_hash": row._mapping.get("file_hash"),
                }
                for row in rows
            ]
        logger.debug("Found %d existing files in DB for %s", len(results), db_source)
        return results
    except ProgrammingError as exc:
        logger.warning(
            "Table not found querying database files for %s (first run?): %s",
            db_source,
            exc,
        )
        return []


def get_database_sources() -> List[str]:
    """
    Get all db_source values that currently exist in iris_document_metadata.

    Returns:
        Sorted list of distinct db_source values.
    """
    query = text(
        """
        SELECT DISTINCT db_source
        FROM iris_document_metadata
        """
    )

    try:
        with get_database_session() as session:
            rows = session.execute(query).fetchall()
            sources = sorted(
                row._mapping.get("db_source")
                for row in rows
                if row._mapping.get("db_source")
            )
        return sources
    except ProgrammingError as exc:
        logger.warning(
            "Table not found querying existing database sources (first run?): %s",
            exc,
        )
        return []


def get_removed_database_sources(discovered_sources: Optional[List[str]]) -> List[str]:
    """
    Find db_source values present in DB but missing from discovered source folders.

    Args:
        discovered_sources: Folder names discovered from file source.

    Returns:
        Sorted list of missing db_source values that should be removed.
    """
    discovered = set(discovered_sources or [])
    existing = set(get_database_sources())
    return sorted(existing - discovered)
