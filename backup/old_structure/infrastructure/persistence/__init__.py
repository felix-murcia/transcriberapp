"""
Infrastructure layer - job status repository implementations.
Concrete implementations of job status tracking ports.
"""

import os
import json
from threading import Lock
from typing import Optional, Dict, Any
from pathlib import Path
from transcriber_app.domain.ports import JobStatusRepositoryPort


class FileBasedJobStatusRepository(JobStatusRepositoryPort):
    """File-based job status repository implementation for persistence across workers."""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # Use a persistent directory that works in both dev and prod
            storage_dir = os.getenv("JOB_STORAGE_DIR", "/tmp/transcriber_jobs")
        self.storage_dir = Path(storage_dir)
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, FileNotFoundError):
            # Fallback to a directory relative to the project
            import sys
            project_dir = Path(sys.path[0]) / "data" / "jobs"
            project_dir.mkdir(parents=True, exist_ok=True)
            self.storage_dir = project_dir
        self._lock = Lock()

    def _get_job_file(self, job_id: str) -> Path:
        """Get the file path for a job."""
        return self.storage_dir / f"{job_id}.json"

    def set_status(self, job_id: str, status: Dict[str, Any]) -> None:
        """Set job status to file."""
        job_file = self._get_job_file(job_id)
        with self._lock:
            try:
                with open(job_file, 'w') as f:
                    json.dump(status, f, indent=2)
            except Exception as e:
                print(f"Error saving job {job_id}: {e}")

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status from file."""
        job_file = self._get_job_file(job_id)
        with self._lock:
            try:
                if job_file.exists():
                    with open(job_file, 'r') as f:
                        return json.load(f)
            except Exception as e:
                print(f"Error loading job {job_id}: {e}")
        return None

    def clear_all(self) -> None:
        """Clear all job status files."""
        with self._lock:
            try:
                for job_file in self.storage_dir.glob("*.json"):
                    job_file.unlink()
            except Exception as e:
                print(f"Error clearing jobs: {e}")

    def delete_status(self, job_id: str) -> bool:
        """Delete a specific job status file."""
        job_file = self._get_job_file(job_id)
        with self._lock:
            try:
                if job_file.exists():
                    job_file.unlink()
                    return True
            except Exception as e:
                print(f"Error deleting job {job_id}: {e}")
        return False


class InMemoryJobStatusRepository(JobStatusRepositoryPort):
    """In-memory job status repository implementation."""

    def __init__(self):
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def set_status(self, job_id: str, status: Dict[str, Any]) -> None:
        """Set job status."""
        with self._lock:
            self._statuses[job_id] = status

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        with self._lock:
            return self._statuses.get(job_id)

    def clear_all(self) -> None:
        """Clear all job statuses."""
        with self._lock:
            self._statuses.clear()

    def delete_status(self, job_id: str) -> bool:
        """Delete a specific job status."""
        with self._lock:
            if job_id in self._statuses:
                del self._statuses[job_id]
                return True
            return False
