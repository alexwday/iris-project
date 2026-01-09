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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from ..connections.file_source import FileSource, get_file_source
from ..connections.postgres import execute_query
from ..utils.env_config import Config
from ..utils.process_monitoring import get_process_monitor

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".pdf", ".docx"]


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
            (uses Config.get_database_names() if None).
        force: If True, mark all files for processing regardless of hash.

    Returns:
        ScanResult with files to process, remove, and statistics.
    """
    monitor = get_process_monitor()
    monitor.start_stage("stage_1_scan")

    result = ScanResult()

    try:
        # Get file source
        if file_source is None:
            file_source = get_file_source()
            logger.info("Using file source mode: %s", Config.FILE_SOURCE_MODE)

        # Get database names to process
        if database_names is None:
            database_names = Config.get_database_names()

        if not database_names:
            raise ValueError(
                "No database names configured. Set DATABASE_NAMES environment variable."
            )

        logger.info("Scanning %d database folders: %s", len(database_names), database_names)

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

        # Log summary
        logger.info(
            "Scan complete: %d to process, %d to remove, %d unchanged, %d errors",
            len(result.files_to_process),
            len(result.files_to_remove),
            result.files_unchanged,
            len(result.scan_errors),
        )

        monitor.add_stage_details(
            "stage_1_scan",
            files_to_process=len(result.files_to_process),
            files_to_remove=len(result.files_to_remove),
            files_unchanged=result.files_unchanged,
            databases_scanned=result.databases_scanned,
            errors=len(result.scan_errors),
        )

        monitor.end_stage("stage_1_scan", "completed")
        return result

    except Exception as exc:
        logger.error("Stage 1 scan failed: %s", exc)
        monitor.add_stage_details("stage_1_scan", error=str(exc))
        monitor.end_stage("stage_1_scan", "error")
        raise


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

    # Get existing files from database (keyed by file_name for 2-table design)
    db_files_list = get_database_files(db_name)
    db_files_map = {f["file_name"]: f for f in db_files_list}
    source_names: Set[str] = set()

    # Compare each file
    for file_info in files:
        relative_path = file_info["relative_path"]
        file_name = file_info["name"]
        source_names.add(file_name)

        try:
            # Calculate file hash
            file_hash = file_source.get_file_hash(
                f"{db_name}/{relative_path}" if Config.FILE_SOURCE_MODE == "local" else file_info["path"]
            )

            # Check if file exists in database (by file_name for 2-table design)
            db_file = db_files_map.get(file_name)

            if db_file is None:
                # New file
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
                # Force reprocess
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
                # File exists, no force flag - skip (hash not available in 2-table design)
                result.files_unchanged += 1

        except Exception as exc:
            error_msg = f"Error processing file {relative_path}: {exc}"
            logger.warning(error_msg)
            result.scan_errors.append(error_msg)

    # Find files to remove (in DB but not in source)
    for file_name, db_file in db_files_map.items():
        if file_name not in source_names:
            result.files_to_remove.append(
                {
                    "db_source": db_name,
                    "file_name": file_name,
                    "file_path": db_file.get("file_path"),
                    "document_id": db_file.get("document_id"),
                }
            )
            logger.debug("File to remove: %s", file_name)

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
        List of dicts with 'document_id', 'file_path', 'file_name' keys.
        Note: file_hash not available in 2-table design, use file_name for matching.
    """
    query = """
        SELECT id as document_id, file_path, document_name as file_name
        FROM iris_document_metadata
        WHERE db_source = %s
    """

    try:
        rows = execute_query(query, (db_source,), dict_cursor=True)
        logger.debug("Found %d existing files in DB for %s", len(rows), db_source)
        return rows
    except Exception as exc:
        logger.warning("Could not query database files for %s: %s", db_source, exc)
        return []
