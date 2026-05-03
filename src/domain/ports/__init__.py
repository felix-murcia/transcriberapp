"""
Domain ports (interfaces) for TranscriberApp hexagonal architecture.

Primary Ports (driven): Interfaces that the core domain exposes to the outside world.
Secondary Ports (driving): Interfaces that the core domain needs from the outside world.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple, Protocol
from dataclasses import dataclass

from ..entities import TranscriptionJob, AudioFile


# Secondary Ports (Driving) - External Services that Domain needs

class TranscriptionServicePort(Protocol):
    """Port for AI transcription services (Groq, Gemini, etc.)."""

    def transcribe_audio(self, audio_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file

        Returns:
            Tuple of (transcription_text, metadata)
        """
        ...

    def transcribe_audio_chunked(self, audio_chunks: List[str]) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe multiple audio chunks and combine results.

        Args:
            audio_chunks: List of paths to audio chunks

        Returns:
            Tuple of (combined_transcription, metadata)
        """
        ...


class AudioProcessingPort(Protocol):
    """Port for audio processing services (FFmpeg API)."""

    def validate_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Validate an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with validation results
        """
        ...

    def convert_audio(self, audio_path: str, output_format: str) -> bytes:
        """
        Convert audio file to specified format.

        Args:
            audio_path: Input audio file path
            output_format: Target format ('mp3', 'wav', etc.)

        Returns:
            Audio data as bytes
        """
        ...

    def clean_audio(self, audio_path: str) -> bytes:
        """
        Clean/normalize audio for better transcription.

        Args:
            audio_path: Input audio file path

        Returns:
            Cleaned audio data as bytes
        """
        ...

    def get_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """
        Extract metadata from audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with metadata (duration, sample_rate, etc.)
        """
        ...


class AISummarizerPort(Protocol):
    """Port for AI summarization services."""

    def summarize(self, text: str, mode: str) -> str:
        """
        Summarize text using AI agents based on the specified mode.

        Args:
            text: The text to summarize
            mode: The summarization mode

        Returns:
            str: The summarized output
        """
        ...

    def get_available_modes(self) -> List[str]:
        """
        Get list of available summarization modes.

        Returns:
            List of mode names
        """
        ...


class AuthServicePort(Protocol):
    """Port for authentication services (OAuth2 Server)."""

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate authentication token.

        Args:
            token: Authentication token

        Returns:
            User info dict if valid, None if invalid
        """
        ...

    def get_user_permissions(self, user_id: str) -> List[str]:
        """
        Get user permissions.

        Args:
            user_id: User identifier

        Returns:
            List of permission strings
        """
        ...


class EmailServicePort(Protocol):
    """Port for email services."""

    def send_transcription_result(
        self,
        email: str,
        job_id: str,
        filename: str,
        summary: str,
        transcription_url: Optional[str] = None
    ) -> bool:
        """
        Send transcription result via email.

        Args:
            email: Recipient email
            job_id: Job identifier
            filename: Original filename
            summary: Summary content
            transcription_url: Optional URL to full transcription

        Returns:
            True if sent successfully
        """
        ...


class FileStoragePort(Protocol):
    """Port for file storage operations."""

    def save_file(self, content: bytes, filename: str, directory: str) -> str:
        """
        Save a file to storage.

        Args:
            content: File content as bytes
            filename: Name of the file
            directory: Target directory

        Returns:
            str: Path where file was saved
        """
        ...

    def read_file(self, file_path: str) -> bytes:
        """
        Read a file from storage.

        Args:
            file_path: Path to the file

        Returns:
            bytes: File content
        """
        ...

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path to the file

        Returns:
            bool: True if successful
        """
        ...

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        List files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern

        Returns:
            list: List of file paths
        """
        ...


class JobRepositoryPort(Protocol):
    """Port for job persistence."""

    def save(self, job: TranscriptionJob) -> None:
        """
        Save a job.

        Args:
            job: Job to save
        """
        ...

    def get_by_id(self, job_id: str) -> Optional[TranscriptionJob]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        ...

    def update_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> None:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message
        """
        ...

    def get_jobs_by_status(self, status: str) -> List[TranscriptionJob]:
        """
        Get jobs by status.

        Args:
            status: Status to filter by

        Returns:
            List of jobs with the status
        """
        ...


class AudioReaderPort(Protocol):
    """Port for reading audio files."""

    def read_audio_file(self, file_path: str) -> AudioFile:
        """
        Read and analyze an audio file.

        Args:
            file_path: Path to audio file

        Returns:
            AudioFile object with metadata
        """
        ...


# Configuration and Settings Ports

@dataclass
class AppSettings:
    """Application settings value object."""
    groq_api_key: str
    groq_api_url: str
    groq_model: str

    gemini_api_key: str
    gemini_model: str

    ffmpeg_api_url: str
    oauth2_server_url: str

    uploads_dir: str
    outputs_dir: str
    transcripts_dir: str

    max_file_size_mb: int
    supported_formats: List[str]


class SettingsPort(Protocol):
    """Port for application settings."""

    def get_settings(self) -> AppSettings:
        """
        Get application settings.

        Returns:
            AppSettings object
        """
        ...