"""
Repository interfaces for domain layer.
These define the contracts for data persistence.
"""

from typing import Protocol, Optional, List
from ..entities import TranscriptionJob


class TranscriptionJobRepositoryPort(Protocol):
    """Repository interface for transcription jobs."""

    def save(self, job: TranscriptionJob) -> None:
        """Save a transcription job."""
        ...

    def find_by_id(self, job_id: str) -> Optional[TranscriptionJob]:
        """Find job by ID."""
        ...

    def find_by_status(self, status: str) -> List[TranscriptionJob]:
        """Find jobs by status."""
        ...

    def update(self, job: TranscriptionJob) -> None:
        """Update an existing job."""
        ...

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID."""
        ...


class AudioFileRepositoryPort(Protocol):
    """Repository interface for audio files metadata."""

    def save_metadata(self, audio_file) -> None:
        """Save audio file metadata."""
        ...

    def find_by_path(self, file_path: str) -> Optional[dict]:
        """Find audio metadata by file path."""
        ...