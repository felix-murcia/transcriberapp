"""
Domain events for TranscriberApp.
Domain Events represent something that happened in the domain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..entities import TranscriptionJob


@dataclass
class DomainEvent:
    """Base class for domain events."""
    occurred_at: datetime

    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.now()


@dataclass
class JobCreatedEvent(DomainEvent):
    """Event fired when a transcription job is created."""
    job: TranscriptionJob


@dataclass
class JobStatusChangedEvent(DomainEvent):
    """Event fired when a job status changes."""
    job_id: str
    old_status: str
    new_status: str
    error_message: Optional[str] = None


@dataclass
class TranscriptionCompletedEvent(DomainEvent):
    """Event fired when transcription is completed."""
    job_id: str
    transcription_text: str
    audio_duration_seconds: Optional[float] = None


@dataclass
class SummarizationCompletedEvent(DomainEvent):
    """Event fired when summarization is completed."""
    job_id: str
    summary_text: str
    mode: str


@dataclass
class JobCompletedEvent(DomainEvent):
    """Event fired when entire job is completed."""
    job: TranscriptionJob


@dataclass
class AudioValidationFailedEvent(DomainEvent):
    """Event fired when audio validation fails."""
    file_path: str
    validation_errors: list
    validation_warnings: list