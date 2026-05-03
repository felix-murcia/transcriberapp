"""
Domain value objects for TranscriberApp.
Value Object: An object that is defined by its attributes, not its identity.
Immutable and self-validating.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class Language(Enum):
    """Supported transcription languages."""
    SPANISH = "es"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"


class JobStatus(Enum):
    """Job processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class TranscriptionMode(Enum):
    """Available transcription/summarization modes."""
    DEFAULT = "default"
    TECNICO = "tecnico"
    REFINAMIENTO = "refinamiento"
    EJECUTIVO = "ejecutivo"
    BULLET = "bullet"


class AudioFormat(Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    WEBM = "webm"
    WAV = "wav"
    M4A = "m4a"
    OGG = "ogg"


@dataclass(frozen=True)
class Email:
    """Value object for email addresses."""
    value: str

    def __post_init__(self):
        if not self.value or "@" not in self.value:
            raise ValueError(f"Invalid email address: {self.value}")

        # Basic email validation
        local, domain = self.value.split("@", 1)
        if not local or not domain or "." not in domain:
            raise ValueError(f"Invalid email format: {self.value}")

    @property
    def local_part(self) -> str:
        """Get the local part of the email."""
        return self.value.split("@")[0]

    @property
    def domain_part(self) -> str:
        """Get the domain part of the email."""
        return self.value.split("@")[1]


@dataclass(frozen=True)
class AudioMetadata:
    """Value object for audio file metadata."""
    duration_seconds: float
    sample_rate: int
    channels: int
    bitrate: Optional[int] = None
    codec: Optional[str] = None

    def __post_init__(self):
        if self.duration_seconds <= 0:
            raise ValueError("Duration must be positive")
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.channels < 1:
            raise ValueError("Must have at least 1 channel")


@dataclass(frozen=True)
class ProcessingMetrics:
    """Value object for processing performance metrics."""
    transcription_time_seconds: float
    summarization_time_seconds: float
    total_file_size_bytes: int
    audio_duration_seconds: Optional[float] = None

    def __post_init__(self):
        if self.transcription_time_seconds < 0:
            raise ValueError("Transcription time cannot be negative")
        if self.summarization_time_seconds < 0:
            raise ValueError("Summarization time cannot be negative")
        if self.total_file_size_bytes < 0:
            raise ValueError("File size cannot be negative")