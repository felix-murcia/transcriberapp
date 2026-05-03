"""
Domain exceptions for TranscriberApp.
"""

from typing import Optional, Dict, Any


class DomainError(Exception):
    """Base domain exception."""
    pass


class AudioValidationError(DomainError):
    """Raised when audio file fails validation."""

    def __init__(self, message: str, validation_result: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.validation_result = validation_result


class JobNotFoundError(DomainError):
    """Raised when a job is not found."""

    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}")
        self.job_id = job_id


class TranscriptionError(DomainError):
    """Raised when transcription fails."""

    def __init__(self, message: str, job_id: Optional[str] = None):
        super().__init__(message)
        self.job_id = job_id


class SummarizationError(DomainError):
    """Raised when summarization fails."""

    def __init__(self, message: str, mode: Optional[str] = None):
        super().__init__(message)
        self.mode = mode


class AuthenticationError(DomainError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(DomainError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization failed", required_permissions: Optional[list] = None):
        super().__init__(message)
        self.required_permissions = required_permissions or []


class ExternalServiceError(DomainError):
    """Raised when external service fails."""

    def __init__(self, service_name: str, message: str):
        super().__init__(f"{service_name} error: {message}")
        self.service_name = service_name


class InvalidAudioFormatError(DomainError):
    """Raised when audio format is not supported."""

    def __init__(self, format: str, supported_formats: list):
        message = f"Unsupported audio format '{format}'. Supported: {', '.join(supported_formats)}"
        super().__init__(message)
        self.format = format
        self.supported_formats = supported_formats