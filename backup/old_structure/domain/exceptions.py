"""
Domain exceptions for TranscriberApp.
"""

from typing import Optional


class DomainError(Exception):
    """Base domain exception."""
    pass


class AudioValidationError(DomainError):
    """Raised when audio file fails validation."""

    def __init__(self, message: str, validation_result: Optional[dict] = None):
        super().__init__(message)
        self.validation_result = validation_result


class JobNotFoundError(DomainError):
    """Raised when a job is not found."""
    pass


class TranscriptionError(DomainError):
    """Raised when transcription fails."""
    pass


class AuthenticationError(DomainError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(DomainError):
    """Raised when authorization fails."""
    pass
