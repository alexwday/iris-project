"""
Restore document data from CSV backup files.

Reads iris_document_metadata.csv and iris_document_chunks.csv from a backup
directory and inserts them into PostgreSQL. Preserves original UUIDs and
embeddings so all foreign key relationships remain intact.

Usage:
    python -m doc_refresh.restore <backup_dir> [--db-sources source1,source2]

Examples:
    # Restore all data from a backup directory
    python -m doc_refresh.restore /mnt/nas/backups/backup_20260210_143000

    # Restore only specific databases
    python -m doc_refresh.restore /mnt/nas/backups/backup_20260210_143000 \
        --db-sources internal_sab_99,internal_pafe,internal_intragroup_memos

    # Copy from NAS first, then restore
    python -m doc_refresh.restore /nas/path/backup_20260210_143000 --nas
"""

import argparse
import logging
import sys

from .utils.backup import run_restore
from .utils.env_config import config
from .utils.logging_format import configure_root_logger
from .utils.rbc_security import configure_rbc_security_certs

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Restore document data from CSV backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "backup_dir",
        type=str,
        help="Path to backup directory containing iris_document_metadata.csv "
        "and iris_document_chunks.csv",
    )

    parser.add_argument(
        "--db-sources",
        type=str,
        default=None,
        help="Comma-separated list of db_source values to restore "
        "(default: all sources in backup)",
    )

    parser.add_argument(
        "--nas",
        action="store_true",
        default=(config.FILE_SOURCE_MODE == "nas"),
        help="Read backup files via NAS FileSource (copies to local temp first). "
        "Defaults to true when FILE_SOURCE_MODE=nas.",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def main() -> int:
    """Restore document data from CSV backup.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_root_logger(log_level)

    configure_rbc_security_certs()

    db_sources = None
    if args.db_sources:
        db_sources = [s.strip() for s in args.db_sources.split(",")]

    file_source = None
    if args.nas:
        from .connections.file_source import get_file_source
        file_source = get_file_source()

    logger.info("=" * 60)
    logger.info("Document Restore from Backup")
    logger.info("=" * 60)
    logger.info("  Backup dir: %s", args.backup_dir)
    logger.info("  DB sources: %s", db_sources or "ALL")
    logger.info("  NAS mode: %s", args.nas)

    success, metadata_count, chunks_count = run_restore(
        backup_dir=args.backup_dir,
        db_sources=db_sources,
        file_source=file_source,
    )

    if success:
        logger.info("Restore successful: %d documents, %d chunks", metadata_count, chunks_count)
        return 0

    logger.error("Restore failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
