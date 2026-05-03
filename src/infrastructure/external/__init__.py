"""
External service adapters for TranscriberApp.
Concrete implementations of domain ports for external services.
"""

# Import adapters
from .groq_adapter import GroqTranscriptionAdapter
from .ffmpeg_adapter import RemoteFFmpegAdapter
from .gemini_adapter import GeminiSummarizerAdapter
from .oauth2_adapter import OAuth2Adapter
from .email_adapter import SMTPEmailAdapter, MockEmailAdapter
from .file_storage_adapter import LocalFileStorageAdapter
from .job_repository_adapter import FileBasedJobRepository
from .settings_adapter import EnvironmentSettingsAdapter

# Re-export for convenience
__all__ = [
    "GroqTranscriptionAdapter",
    "RemoteFFmpegAdapter",
    "GeminiSummarizerAdapter",
    "OAuth2Adapter",
    "SMTPEmailAdapter",
    "MockEmailAdapter",
    "LocalFileStorageAdapter",
    "FileBasedJobRepository",
    "EnvironmentSettingsAdapter",
]