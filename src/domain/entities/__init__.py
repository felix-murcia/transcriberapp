"""
Domain entities for TranscriberApp.
Entity: An object that is defined by its identity, not its attributes.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
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

    # Para procesamiento en caliente de chunks
    total_chunks: Optional[int] = None
    processed_chunks: int = 0
    partial_transcriptions: Optional[Dict[int, str]] = None  # index -> transcription_text

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.partial_transcriptions is None:
            self.partial_transcriptions = {}

    def add_partial_transcription(self, chunk_index: int, text: str) -> None:
        """Add partial transcription for a chunk."""
        self.partial_transcriptions[chunk_index] = text
        self.processed_chunks += 1

    def get_combined_transcription(self) -> str:
        """Combine all partial transcriptions in order."""
        if not self.partial_transcriptions:
            return ""

        combined = []
        for i in range(len(self.partial_transcriptions)):
            if i in self.partial_transcriptions:
                combined.append(self.partial_transcriptions[i])

        return " ".join(combined)


@dataclass
class AudioFile:
    """Value object representing an audio file."""
    path: str
    filename: str
    size_bytes: int
    extension: str
    is_valid: bool = True
    validation_issues: Optional[List[str]] = None
    validation_warnings: Optional[List[str]] = None

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
    processing_time_seconds: Optional[float] = None