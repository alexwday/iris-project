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

from ..utils.env_config import config

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
        Calculate SHA-256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            SHA-256 hash string.
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

    @abstractmethod
    def list_subfolders(self, folder_path: str = "") -> List[str]:
        """
        List immediate subdirectories of a folder, skipping hidden directories.

        Args:
            folder_path: Path to the folder (empty string for base path root).

        Returns:
            List of subfolder names.
        """
        pass

    @abstractmethod
    def ensure_directory(self, path: str) -> None:
        """
        Create a directory and all parents if they don't exist.

        Args:
            path: Absolute path (local) or share-relative path (NAS) of the directory.
        """
        pass

    @abstractmethod
    def copy_from_local(self, local_path: str, remote_path: str) -> None:
        """
        Copy a local file to the destination.

        Args:
            local_path: Path to the source file on the local filesystem.
            remote_path: Destination path (absolute for local, share-relative for NAS).
        """
        pass

    @abstractmethod
    def write_data(self, data: bytes, remote_path: str) -> None:
        """
        Write raw bytes to the destination.

        Args:
            data: Bytes to write.
            remote_path: Destination path (absolute for local, share-relative for NAS).
        """
        pass

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """
        Delete a file from the source.

        Args:
            path: Absolute path (local) or share-relative path (NAS) to delete.
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

        ext_set = {ext.lower() for ext in extensions} if extensions else None

        files = []
        for item in resolved.rglob("*"):
            if not item.is_file():
                continue

            if ext_set and item.suffix.lower() not in ext_set:
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
        """Calculate SHA-256 hash of a local file."""
        resolved = self._resolve_path(path)
        hash_sha256 = hashlib.sha256()
        with open(resolved, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def get_file_size(self, path: str) -> int:
        """Get size of a local file."""
        resolved = self._resolve_path(path)
        return resolved.stat().st_size

    def list_subfolders(self, folder_path: str = "") -> List[str]:
        """List immediate subdirectories, skipping hidden dirs."""
        resolved = self._resolve_path(folder_path) if folder_path else self.base_path
        if resolved is None or not resolved.exists():
            return []
        return sorted(
            item.name
            for item in resolved.iterdir()
            if item.is_dir() and not item.name.startswith(".")
        )

    def ensure_directory(self, path: str) -> None:
        """Create a local directory and all parents."""
        Path(path).mkdir(parents=True, exist_ok=True)

    def copy_from_local(self, local_path: str, remote_path: str) -> None:
        """Copy a local file to another local path."""
        dest = Path(remote_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, str(dest))
        logger.debug("Copied %s to %s", local_path, remote_path)

    def write_data(self, data: bytes, remote_path: str) -> None:
        """Write raw bytes to a local file."""
        dest = Path(remote_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        logger.debug("Wrote %d bytes to %s", len(data), remote_path)

    def delete_file(self, path: str) -> None:
        """Delete a local file."""
        target = Path(path)
        if target.exists():
            target.unlink()
            logger.debug("Deleted local file: %s", path)


class NASFileSource(FileSource):
    """
    NAS (Network Attached Storage) implementation of FileSource.

    Uses pysmb library for SMB/CIFS protocol access. Maintains a
    persistent SMB connection that is reused across operations and
    automatically reconnects on failure.
    """

    def __init__(self, base_path: str = "") -> None:
        """
        Initialize NAS file source with connection parameters from environment.

        Args:
            base_path: Root folder within the share for document scanning.

        Raises:
            RuntimeError: If pysmb is not available.
            ValueError: If NAS configuration is incomplete.
        """
        if not _PYSMB_AVAILABLE:
            raise RuntimeError(
                "pysmb library not available. Install with: pip install pysmb"
            )

        if not all([config.NAS_IP, config.NAS_SHARE, config.NAS_USER]):
            raise ValueError(
                "Incomplete NAS configuration. Set NAS_IP, NAS_SHARE, NAS_USER, NAS_PASSWORD."
            )

        self.ip = config.NAS_IP
        self.share = config.NAS_SHARE
        self.user = config.NAS_USER
        self.password = config.NAS_PASSWORD
        self.port = config.NAS_PORT
        self.base_path = base_path.replace("\\", "/").strip("/") if base_path else ""
        self.client_hostname = socket.gethostname()
        self._conn: Optional["SMBConnection"] = None

        logger.info(
            "Initialized NASFileSource (ip=%s, share=%s, port=%d, base_path=%s)",
            self.ip,
            self.share,
            self.port,
            self.base_path or "/",
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

    def _get_connection(self) -> "SMBConnection":
        """Return the cached connection, creating or reconnecting as needed."""
        if self._conn is not None:
            try:
                self._conn.echo(b"ping")
                return self._conn
            except Exception:
                logger.debug("NAS connection stale, reconnecting")
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

        self._conn = self._create_connection()
        return self._conn

    def close(self) -> None:
        """Close the cached SMB connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _resolve_path(self, path: str) -> str:
        """Prepend base_path to a relative path for share-level operations."""
        path = path.replace("\\", "/").strip("/") if path else ""
        if self.base_path and path:
            return f"{self.base_path}/{path}"
        return self.base_path or path

    def list_files(
        self, folder_path: str, extensions: Optional[List[str]] = None
    ) -> List[Dict]:
        """List files recursively in a NAS folder."""
        full_path = self._resolve_path(folder_path)
        try:
            conn = self._get_connection()
            files = self._list_files_recursive(conn, full_path, extensions)
            logger.info("Found %d files in NAS path %s/%s", len(files), self.share, full_path)
            return files
        except Exception as exc:
            logger.error("Error listing NAS files in %s: %s", full_path, exc)
            raise

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
            logger.error("Could not list path %s/%s: %s", self.share, path, exc)
            raise

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
        remote_path = remote_path.replace("\\", "/")
        path_hash = hashlib.md5(remote_path.encode()).hexdigest()[:8]
        filename = os.path.basename(remote_path)
        name, ext = os.path.splitext(filename)
        local_path = os.path.join(local_dir, f"{name}_{path_hash}{ext}")

        try:
            conn = self._get_connection()
            file_obj = io.BytesIO()

            _, filesize = conn.retrieveFile(self.share, remote_path, file_obj)

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

    def path_exists(self, path: str) -> bool:
        """Check if a path exists on NAS."""
        path = path.replace("\\", "/")

        try:
            conn = self._get_connection()
            conn.getAttributes(self.share, path)
            return True
        except smb_structs.OperationFailure:
            return False
        except Exception as exc:
            logger.warning("NAS path_exists failed for %s/%s: %s", self.share, path, exc)
            raise

    def get_file_hash(self, path: str) -> str:
        """Calculate SHA-256 hash of a NAS file."""
        path = path.replace("\\", "/")

        try:
            conn = self._get_connection()
            file_obj = io.BytesIO()
            conn.retrieveFile(self.share, path, file_obj)
            file_obj.seek(0)

            hash_sha256 = hashlib.sha256()
            for chunk in iter(lambda: file_obj.read(8192), b""):
                hash_sha256.update(chunk)
            return hash_sha256.hexdigest()

        except Exception as exc:
            logger.error("Error hashing NAS file %s/%s: %s", self.share, path, exc)
            raise

    def get_file_size(self, path: str) -> int:
        """Get size of a NAS file."""
        path = path.replace("\\", "/")

        try:
            conn = self._get_connection()
            attrs = conn.getAttributes(self.share, path)
            return attrs.file_size
        except Exception as exc:
            logger.error(
                "Error getting size of NAS file %s/%s: %s", self.share, path, exc
            )
            raise

    def list_subfolders(self, folder_path: str = "") -> List[str]:
        """List immediate subdirectories on NAS, skipping hidden dirs."""
        path = self._resolve_path(folder_path)

        try:
            conn = self._get_connection()
            entries = conn.listPath(self.share, path or "/")
            return sorted(
                entry.filename
                for entry in entries
                if entry.isDirectory
                and entry.filename not in (".", "..")
                and not entry.filename.startswith(".")
            )
        except Exception as exc:
            logger.error(
                "Error listing NAS subfolders %s/%s: %s", self.share, path, exc
            )
            raise

    def ensure_directory(self, path: str) -> None:
        """Create a directory on NAS, walking path segments to create parents."""
        path = path.replace("\\", "/").strip("/")
        if not path:
            return

        conn = self._get_connection()
        segments = path.split("/")
        current = ""

        for segment in segments:
            current = f"{current}/{segment}" if current else segment
            try:
                conn.getAttributes(self.share, current)
            except Exception:
                try:
                    conn.createDirectory(self.share, current)
                    logger.debug("Created NAS directory: %s/%s", self.share, current)
                except Exception as exc:
                    logger.error(
                        "Failed to create NAS directory %s/%s: %s",
                        self.share,
                        current,
                        exc,
                    )
                    raise

    def copy_from_local(self, local_path: str, remote_path: str) -> None:
        """Copy a local file to the NAS share."""
        remote_path = remote_path.replace("\\", "/")
        parent = "/".join(remote_path.split("/")[:-1])
        if parent:
            self.ensure_directory(parent)

        try:
            conn = self._get_connection()
            with open(local_path, "rb") as f:
                conn.storeFile(self.share, remote_path, f)
            logger.debug(
                "Copied %s to NAS %s/%s", local_path, self.share, remote_path
            )
        except Exception as exc:
            logger.error(
                "Failed to copy to NAS %s/%s: %s", self.share, remote_path, exc
            )
            raise

    def write_data(self, data: bytes, remote_path: str) -> None:
        """Write raw bytes to the NAS share."""
        remote_path = remote_path.replace("\\", "/")
        parent = "/".join(remote_path.split("/")[:-1])
        if parent:
            self.ensure_directory(parent)

        try:
            conn = self._get_connection()
            conn.storeFile(self.share, remote_path, io.BytesIO(data))
            logger.debug(
                "Wrote %d bytes to NAS %s/%s", len(data), self.share, remote_path
            )
        except Exception as exc:
            logger.error(
                "Failed to write to NAS %s/%s: %s", self.share, remote_path, exc
            )
            raise

    def delete_file(self, path: str) -> None:
        """Delete a file from the NAS share."""
        remote_path = path.replace("\\", "/")
        try:
            conn = self._get_connection()
            conn.deleteFiles(self.share, remote_path)
            logger.debug("Deleted NAS file %s/%s", self.share, remote_path)
        except Exception as exc:
            logger.error(
                "Failed to delete NAS file %s/%s: %s",
                self.share,
                remote_path,
                exc,
            )
            raise


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
    mode = config.FILE_SOURCE_MODE.lower()

    if mode == "local":
        base_path = config.BASE_PATH if config.BASE_PATH else None
        return LocalFileSource(base_path=base_path)

    elif mode == "nas":
        return NASFileSource(base_path=config.BASE_PATH)

    else:
        raise ValueError(
            f"Invalid FILE_SOURCE_MODE: {mode}. Must be 'local' or 'nas'."
        )
