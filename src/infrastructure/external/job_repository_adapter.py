"""
Job repository adapter for job persistence.
Implements JobRepositoryPort using file-based storage.
"""

import os
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Optional, List, Dict, Any

from domain.ports import JobRepositoryPort
from domain.entities import TranscriptionJob
from domain.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class FileBasedJobRepository(JobRepositoryPort):
    """File-based job repository implementation."""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.getenv("JOB_STORAGE_DIR", "/tmp/transcriber_jobs")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _get_job_file(self, job_id: str) -> Path:
        """Get the file path for a job."""
        return self.storage_dir / f"{job_id}.json"

    def _job_to_dict(self, job: TranscriptionJob) -> dict:
        """Convert job entity to dictionary."""
        return {
            "job_id": job.job_id,
            "audio_filename": job.audio_filename,
            "audio_path": job.audio_path,
            "mode": job.mode,
            "email": job.email,
            "status": job.status,
            "transcription_text": job.transcription_text,
            "summary_output": job.summary_output,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "total_chunks": job.total_chunks,
            "processed_chunks": job.processed_chunks,
            "partial_transcriptions": job.partial_transcriptions
        }

    def _dict_to_job(self, data: dict) -> TranscriptionJob:
        """Convert dictionary to job entity."""
        from datetime import datetime

        return TranscriptionJob(
            job_id=data["job_id"],
            audio_filename=data["audio_filename"],
            audio_path=data.get("audio_path"),
            mode=data["mode"],
            email=data.get("email"),
            status=data["status"],
            transcription_text=data.get("transcription_text"),
            summary_output=data.get("summary_output"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            total_chunks=data.get("total_chunks"),
            processed_chunks=data.get("processed_chunks", 0),
            partial_transcriptions=data.get("partial_transcriptions", {})
        )

    def save(self, job: TranscriptionJob) -> None:
        """Save a job to file."""
        job_file = self._get_job_file(job.job_id)

        with self._lock:
            try:
                job_dict = self._job_to_dict(job)
                with open(job_file, 'w') as f:
                    json.dump(job_dict, f, indent=2, ensure_ascii=False)

                logger.info(f"Job saved: {job.job_id}")

            except Exception as e:
                logger.error(f"Error saving job {job.job_id}: {e}")
                raise ExternalServiceError("job_repository", f"Save failed: {e}") from e

    def get_by_id(self, job_id: str) -> Optional[TranscriptionJob]:
        """Get job by ID from file."""
        job_file = self._get_job_file(job_id)

        with self._lock:
            try:
                if job_file.exists():
                    with open(job_file, 'r') as f:
                        data = json.load(f)
                    return self._dict_to_job(data)

            except Exception as e:
                logger.error(f"Error loading job {job_id}: {e}")
                raise ExternalServiceError("job_repository", f"Load failed: {e}") from e

        return None

    def update_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Update job status."""
        job = self.get_by_id(job_id)
        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            self.save(job)

    def get_jobs_by_status(self, status: str) -> List[TranscriptionJob]:
        """Get jobs by status."""
        jobs = []

        with self._lock:
            try:
                for job_file in self.storage_dir.glob("*.json"):
                    try:
                        with open(job_file, 'r') as f:
                            data = json.load(f)
                        if data.get("status") == status:
                            jobs.append(self._dict_to_job(data))
                    except Exception as e:
                        logger.warning(f"Error reading job file {job_file}: {e}")

            except Exception as e:
                logger.error(f"Error listing jobs: {e}")
                raise ExternalServiceError("job_repository", f"List failed: {e}") from e

        return jobs