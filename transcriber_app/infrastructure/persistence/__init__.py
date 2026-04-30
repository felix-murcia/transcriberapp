"""
Infrastructure layer - job status repository implementations.
Concrete implementations of job status tracking ports.
"""

from threading import Lock
from typing import Optional, Dict, Any
from transcriber_app.domain.ports import JobStatusRepositoryPort


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
