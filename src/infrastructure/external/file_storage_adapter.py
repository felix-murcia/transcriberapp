"""
File storage adapter for file operations.
Implements FileStoragePort using local filesystem.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

from domain.ports import FileStoragePort
from domain.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class LocalFileStorageAdapter(FileStoragePort):
    """Adapter for local file system storage."""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.getcwd())

    def save_file(self, content: bytes, filename: str, directory: str) -> str:
        """Save a file to the local filesystem."""
        target_dir = self.base_dir / directory
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename

        try:
            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"File saved: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            raise ExternalServiceError("file_storage", f"Save failed: {e}") from e

    def read_file(self, file_path: str) -> bytes:
        """Read a file from the local filesystem."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            logger.info(f"File read: {file_path}")
            return content

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise ExternalServiceError("file_storage", f"Read failed: {e}") from e

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from the local filesystem."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise ExternalServiceError("file_storage", f"Delete failed: {e}") from e

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        try:
            target_dir = self.base_dir / directory
            if not target_dir.exists():
                return []

            files = []
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    files.append(str(file_path))

            return files

        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            raise ExternalServiceError("file_storage", f"List failed: {e}") from e