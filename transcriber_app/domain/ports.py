"""
Domain ports (interfaces) for TranscriberApp hexagonal architecture.

Primary Ports (driven): Interfaces that the core domain exposes to the outside world.
These define what the application can do, without specifying how.

Secondary Ports (driving): Interfaces that the core domain needs from the outside world.
These are abstractions of external services that will be implemented by infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from transcriber_app.domain.entities import AudioFile


class AudioTranscriberPort(ABC):
    """Port for audio transcription services."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file

        Returns:
            tuple: (transcription_text, metadata)
        """
        pass


class AISummarizerPort(ABC):
    """Port for AI summarization services."""

    @abstractmethod
    def summarize(self, text: str, mode: str) -> str:
        """
        Summarize text using AI agents based on the specified mode.

        Args:
            text: The text to summarize
            mode: The summarization mode (default, tecnico, refinamiento, etc.)

        Returns:
            str: The summarized output
        """
        pass

    @abstractmethod
    def get_agent(self, mode: str) -> Any:
        """Get the appropriate agent for the given mode."""
        pass


class AudioValidatorPort(ABC):
    """Port for audio validation services."""

    @abstractmethod
    def validate(self, audio_path: str) -> Dict[str, Any]:
        """
        Validate an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            dict: Validation result with 'valid', 'issues', 'warnings' keys
        """
        pass


class AudioFileReaderPort(ABC):
    """Port for reading audio files."""

    @abstractmethod
    def load(self, audio_path: str) -> AudioFile:
        """
        Load an audio file and return metadata.

        Args:
            audio_path: Path to the audio file

        Returns:
            AudioFile: Audio file metadata
        """
        pass


class OutputFormatterPort(ABC):
    """Port for formatting and saving output."""

    @abstractmethod
    def save_transcription(self, job_id: str, audio_name: str, text: str) -> str:
        """
        Save raw transcription text.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            text: Transcribed text

        Returns:
            str: Path where transcription was saved
        """
        pass

    @abstractmethod
    def save_output(self, job_id: str, audio_name: str, content: str, mode: str) -> str:
        """
        Save formatted output.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            content: Formatted content to save
            mode: The summarization mode used

        Returns:
            str: Path where output was saved
        """
        pass

    @abstractmethod
    def save_metrics(self, job_id: str, audio_name: str, summary: str, mode: str) -> Dict[str, Any]:
        """
        Save processing metrics.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            summary: Summary output
            mode: The summarization mode used

        Returns:
            dict: Saved metrics
        """
        pass


class JobStatusRepositoryPort(ABC):
    """Port for tracking job status."""

    @abstractmethod
    def set_status(self, job_id: str, status: Dict[str, Any]) -> None:
        """
        Set the status of a job.

        Args:
            job_id: Unique job identifier
            status: Status dictionary
        """
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job.

        Args:
            job_id: Unique job identifier

        Returns:
            dict: Status dictionary or None if not found
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Clear all job statuses."""
        pass


class JobQueuePort(ABC):
    """Port for background job queue."""

    @abstractmethod
    def add_task(self, func, *args, **kwargs) -> None:
        """
        Add a task to the background queue.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        pass


class FileStoragePort(ABC):
    """Port for file storage operations."""

    @abstractmethod
    def save_file(self, content: bytes, filename: str, directory: str) -> str:
        """
        Save a file.

        Args:
            content: File content as bytes
            filename: Name of the file
            directory: Target directory

        Returns:
            str: Path where file was saved
        """
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """
        Read a file.

        Args:
            file_path: Path to the file

        Returns:
            bytes: File content
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to the file

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        List files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern

        Returns:
            list: List of file paths
        """
        pass


class SessionManagerPort(ABC):
    """Port for session management."""

    @abstractmethod
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """
        Create a new session.

        Args:
            user_id: User identifier
            session_data: Session data

        Returns:
            str: Session token
        """
        pass

    @abstractmethod
    def validate_session(self, session_token: str) -> bool:
        """
        Validate a session token.

        Args:
            session_token: Session token to validate

        Returns:
            bool: True if valid
        """
        pass

    @abstractmethod
    def get_session_data(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            session_token: Session token

        Returns:
            dict: Session data or None
        """
        pass

    @abstractmethod
    def delete_session(self, session_token: str) -> bool:
        """
        Delete a session.

        Args:
            session_token: Session token

        Returns:
            bool: True if successful
        """
        pass
