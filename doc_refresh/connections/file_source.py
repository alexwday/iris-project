"""
File Source Module for Document Refresh Pipeline.

Provides pluggable file source abstraction supporting both local filesystem
and NAS (Network Attached Storage) via SMB protocol.

The file source mode is controlled by the FILE_SOURCE_MODE environment variable:
- "local": Uses local filesystem (default for development)
- "nas": Uses NAS via SMB connection (for RBC environment)

Classes:
    FileSource: Abstract base class for file sources
    LocalFileSource: Local filesystem implementation
    NASFileSource: NAS implementation using pysmb

Functions:
    get_file_source: Factory function to get appropriate file source
"""

import hashlib
import io
import logging
import os
import shutil
import socket
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.env_config import Config

logger = logging.getLogger(__name__)

# Try to import pysmb for NAS support
try:
    from smb.SMBConnection import SMBConnection
    from smb import smb_structs

    smb_structs.SUPPORT_SMB2 = True
    _PYSMB_AVAILABLE = True
except ImportError:
    _PYSMB_AVAILABLE = False
    logger.debug("pysmb not available - NAS support disabled")


class FileSource(ABC):
    """
    Abstract base class for file sources.

    Provides a common interface for accessing files from different sources
    (local filesystem, NAS, cloud storage, etc.).
    """

    @abstractmethod
    def list_files(
        self, folder_path: str, extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        List files in a folder with metadata.

        Args:
            folder_path: Path to the folder to list.
            extensions: Optional list of file extensions to filter (e.g., ['.pdf', '.docx']).

        Returns:
            List of dicts with 'path', 'name', 'size', 'modified_time' keys.
        """
        pass

    @abstractmethod
    def copy_to_local(self, remote_path: str, local_dir: str) -> str:
        """
        Copy a file to a local directory.

        Args:
            remote_path: Path to the file on the source.
            local_dir: Local directory to copy to.

        Returns:
            Local path to the copied file.
        """
        pass

    @abstractmethod
    def path_exists(self, path: str) -> bool:
        """
        Check if a path exists on the source.

        Args:
            path: Path to check.

        Returns:
            True if path exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_file_hash(self, path: str) -> str:
        """
        Calculate MD5 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            MD5 hash string.
        """
        pass

    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """
        Get file size in bytes.

        Args:
            path: Path to the file.

        Returns:
            File size in bytes.
        """
        pass


class LocalFileSource(FileSource):
    """
    Local filesystem implementation of FileSource.

    Uses standard Python pathlib/os operations for file access.
    """

    def __init__(self, base_path: Optional[str] = None) -> None:
        """
        Initialize local file source.

        Args:
            base_path: Optional base path to prepend to all paths.
        """
        self.base_path = Path(base_path) if base_path else None
        logger.info("Initialized LocalFileSource (base_path=%s)", base_path)

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base_path if set."""
        if self.base_path:
            return self.base_path / path
        return Path(path)

    def list_files(
        self, folder_path: str, extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """List files recursively in a local folder."""
        resolved = self._resolve_path(folder_path)
        if not resolved.exists():
            logger.warning("Folder does not exist: %s", resolved)
            return []

        files = []
        for item in resolved.rglob("*"):
            if not item.is_file():
                continue

            # Filter by extension if specified
            if extensions:
                if item.suffix.lower() not in [ext.lower() for ext in extensions]:
                    continue

            stat = item.stat()
            files.append(
                {
                    "path": str(item),
                    "relative_path": str(item.relative_to(resolved)),
                    "name": item.name,
                    "size": stat.st_size,
                    "modified_time": stat.st_mtime,
                }
            )

        logger.info("Found %d files in %s", len(files), resolved)
        return files

    def copy_to_local(self, remote_path: str, local_dir: str) -> str:
        """Copy a local file to another local directory."""
        source = self._resolve_path(remote_path)
        dest = Path(local_dir) / source.name
        shutil.copy2(source, dest)
        logger.debug("Copied %s to %s", source, dest)
        return str(dest)

    def path_exists(self, path: str) -> bool:
        """Check if a local path exists."""
        resolved = self._resolve_path(path)
        return resolved.exists()

    def get_file_hash(self, path: str) -> str:
        """Calculate MD5 hash of a local file."""
        resolved = self._resolve_path(path)
        hash_md5 = hashlib.md5()
        with open(resolved, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_file_size(self, path: str) -> int:
        """Get size of a local file."""
        resolved = self._resolve_path(path)
        return resolved.stat().st_size


class NASFileSource(FileSource):
    """
    NAS (Network Attached Storage) implementation of FileSource.

    Uses pysmb library for SMB/CIFS protocol access.
    """

    def __init__(self) -> None:
        """
        Initialize NAS file source with connection parameters from environment.

        Raises:
            RuntimeError: If pysmb is not available.
            ValueError: If NAS configuration is incomplete.
        """
        if not _PYSMB_AVAILABLE:
            raise RuntimeError(
                "pysmb library not available. Install with: pip install pysmb"
            )

        if not all([Config.NAS_IP, Config.NAS_SHARE, Config.NAS_USER]):
            raise ValueError(
                "Incomplete NAS configuration. Set NAS_IP, NAS_SHARE, NAS_USER, NAS_PASSWORD."
            )

        self.ip = Config.NAS_IP
        self.share = Config.NAS_SHARE
        self.user = Config.NAS_USER
        self.password = Config.NAS_PASSWORD
        self.port = Config.NAS_PORT
        self.client_hostname = socket.gethostname()

        logger.info(
            "Initialized NASFileSource (ip=%s, share=%s, port=%d)",
            self.ip,
            self.share,
            self.port,
        )

    def _create_connection(self) -> "SMBConnection":
        """Create and return an authenticated SMB connection."""
        conn = SMBConnection(
            self.user,
            self.password,
            self.client_hostname,
            self.ip,
            use_ntlm_v2=True,
            is_direct_tcp=(self.port == 445),
        )
        connected = conn.connect(self.ip, self.port, timeout=60)
        if not connected:
            raise ConnectionError(f"Failed to connect to NAS at {self.ip}:{self.port}")
        logger.debug("Connected to NAS: %s:%d", self.ip, self.port)
        return conn

    def list_files(
        self, folder_path: str, extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """List files recursively in a NAS folder."""
        conn = None
        files = []

        try:
            conn = self._create_connection()
            files = self._list_files_recursive(conn, folder_path, extensions)
            logger.info("Found %d files in NAS path %s/%s", len(files), self.share, folder_path)
        except Exception as exc:
            logger.error("Error listing NAS files in %s: %s", folder_path, exc)
        finally:
            if conn:
                conn.close()

        return files

    def _list_files_recursive(
        self,
        conn: "SMBConnection",
        path: str,
        extensions: Optional[List[str]],
        base_path: Optional[str] = None,
    ) -> List[Dict]:
        """Recursively list files in NAS directory."""
        files = []
        if base_path is None:
            base_path = path

        # Normalize path separators
        path = path.replace("\\", "/").strip("/")

        try:
            entries = conn.listPath(self.share, path)
        except Exception as exc:
            logger.warning("Could not list path %s/%s: %s", self.share, path, exc)
            return files

        for entry in entries:
            # Skip . and ..
            if entry.filename in (".", ".."):
                continue

            entry_path = f"{path}/{entry.filename}" if path else entry.filename

            if entry.isDirectory:
                # Recurse into subdirectory
                files.extend(
                    self._list_files_recursive(conn, entry_path, extensions, base_path)
                )
            else:
                # Check extension filter
                if extensions:
                    ext = os.path.splitext(entry.filename)[1].lower()
                    if ext not in [e.lower() for e in extensions]:
                        continue

                # Calculate relative path
                relative_path = entry_path
                if base_path and entry_path.startswith(base_path):
                    relative_path = entry_path[len(base_path) :].lstrip("/")

                files.append(
                    {
                        "path": entry_path,
                        "relative_path": relative_path,
                        "name": entry.filename,
                        "size": entry.file_size,
                        "modified_time": entry.last_write_time,
                    }
                )

        return files

    def copy_to_local(self, remote_path: str, local_dir: str) -> str:
        """Download a file from NAS to local directory."""
        conn = None
        remote_path = remote_path.replace("\\", "/")
        filename = os.path.basename(remote_path)
        local_path = os.path.join(local_dir, filename)

        try:
            conn = self._create_connection()
            file_obj = io.BytesIO()

            # Retrieve file from NAS
            _, filesize = conn.retrieveFile(self.share, remote_path, file_obj)

            # Write to local file
            file_obj.seek(0)
            with open(local_path, "wb") as f:
                f.write(file_obj.read())

            logger.debug(
                "Downloaded %d bytes from NAS %s/%s to %s",
                filesize,
                self.share,
                remote_path,
                local_path,
            )
            return local_path

        except Exception as exc:
            logger.error(
                "Error downloading from NAS %s/%s: %s", self.share, remote_path, exc
            )
            raise
        finally:
            if conn:
                conn.close()

    def path_exists(self, path: str) -> bool:
        """Check if a path exists on NAS."""
        conn = None
        path = path.replace("\\", "/")

        try:
            conn = self._create_connection()
            conn.getAttributes(self.share, path)
            return True
        except Exception:
            return False
        finally:
            if conn:
                conn.close()

    def get_file_hash(self, path: str) -> str:
        """Calculate MD5 hash of a NAS file."""
        conn = None
        path = path.replace("\\", "/")

        try:
            conn = self._create_connection()
            file_obj = io.BytesIO()
            conn.retrieveFile(self.share, path, file_obj)
            file_obj.seek(0)

            hash_md5 = hashlib.md5()
            for chunk in iter(lambda: file_obj.read(8192), b""):
                hash_md5.update(chunk)
            return hash_md5.hexdigest()

        except Exception as exc:
            logger.error("Error hashing NAS file %s/%s: %s", self.share, path, exc)
            raise
        finally:
            if conn:
                conn.close()

    def get_file_size(self, path: str) -> int:
        """Get size of a NAS file."""
        conn = None
        path = path.replace("\\", "/")

        try:
            conn = self._create_connection()
            attrs = conn.getAttributes(self.share, path)
            return attrs.file_size
        except Exception as exc:
            logger.error(
                "Error getting size of NAS file %s/%s: %s", self.share, path, exc
            )
            raise
        finally:
            if conn:
                conn.close()


def get_file_source() -> FileSource:
    """
    Factory function to get appropriate file source based on configuration.

    Returns LocalFileSource when FILE_SOURCE_MODE=local (default).
    Returns NASFileSource when FILE_SOURCE_MODE=nas.

    Returns:
        Appropriate FileSource implementation.

    Raises:
        ValueError: If FILE_SOURCE_MODE is invalid.
    """
    mode = Config.FILE_SOURCE_MODE.lower()

    if mode == "local":
        base_path = Config.BASE_PATH if Config.BASE_PATH else None
        return LocalFileSource(base_path=base_path)

    elif mode == "nas":
        return NASFileSource()

    else:
        raise ValueError(
            f"Invalid FILE_SOURCE_MODE: {mode}. Must be 'local' or 'nas'."
        )
