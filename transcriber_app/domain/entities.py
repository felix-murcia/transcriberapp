"""
Domain entities for TranscriberApp.
Entity: An object that is defined by its identity, not its attributes.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class TranscriptionJob:
    """Entity representing a transcription job."""
    job_id: str
    audio_filename: str
    audio_path: Optional[str]
    mode: str
    email: Optional[str]
    status: str = "pending"
    transcription_text: Optional[str] = None
    summary_output: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AudioFile:
    """Value object representing an audio file."""
    path: str
    filename: str
    size_bytes: int
    extension: str
    is_valid: bool = True
    validation_issues: list = None
    validation_warnings: list = None

    def __post_init__(self):
        if self.validation_issues is None:
            self.validation_issues = []
        if self.validation_warnings is None:
            self.validation_warnings = []


@dataclass
class ProcessingResult:
    """Value object representing the result of audio processing."""
    job_id: str
    audio_name: str
    mode: str
    transcription_text: Optional[str] = None
    summary_output: Optional[str] = None
    output_file_path: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
