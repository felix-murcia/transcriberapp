"""
Tests for SOLID principles compliance.
Focus on Liskov Substitution Principle for port implementations.
"""

import pytest
from unittest.mock import Mock

from transcriber_app.domain.ports import (
    AudioTranscriberPort,
    AISummarizerPort,
    AudioValidatorPort,
)
from transcriber_app.domain.services import TranscriptionService
from transcriber_app.domain.entities import TranscriptionJob, AudioFile


class MockAudioTranscriber(AudioTranscriberPort):
    """Mock implementation of AudioTranscriberPort for testing."""

    def __init__(self, transcription_text="Mock transcription"):
        self.transcription_text = transcription_text

    def transcribe(self, audio_path: str):
        return self.transcription_text, {"engine": "mock"}


class MockAISummarizer(AISummarizerPort):
    """Mock implementation of AISummarizerPort for testing."""

    def __init__(self, summary_text="Mock summary"):
        self.summary_text = summary_text

    def summarize(self, text: str, mode: str) -> str:
        return self.summary_text

    def get_agent(self, mode: str):
        return Mock(run=lambda message, stream=False: self.summary_text)


class MockAudioValidator(AudioValidatorPort):
    """Mock implementation of AudioValidatorPort for testing."""

    def __init__(self, valid=True, issues=None, warnings=None):
        self.valid = valid
        self.issues = issues or []
        self.warnings = warnings or []

    def validate(self, audio_path: str):
        return {
            "valid": self.valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "metadata": {"duration_seconds": 10.0}
        }


def test_liskov_substitution_audio_transcriber():
    """Test that any AudioTranscriberPort implementation can be substituted."""
    # Use mock implementation
    mock_transcriber = MockAudioTranscriber("Test transcription")

    # Create service with mocks for other dependencies
    mock_validator = MockAudioValidator()
    mock_summarizer = MockAISummarizer("Test summary")

    service = TranscriptionService(
        file_reader=Mock(),
        validator=mock_validator,
        transcriber=mock_transcriber,
        summarizer=mock_summarizer,
        formatter=Mock(),
        job_repo=Mock(),
        save_files=False,
    )

    # Create a job
    job = TranscriptionJob(
        job_id="test-123",
        audio_filename="test.mp3",
        audio_path="/tmp/test.mp3",
        mode="default",
        email=None,
    )

    # Mock file_reader
    mock_audio_file = AudioFile(
        path="/tmp/test.mp3",
        filename="test.mp3",
        size_bytes=1024,
        extension="mp3",
    )
    service.file_reader.load.return_value = mock_audio_file

    # Mock formatter
    service.formatter.save_transcription.return_value = "/tmp/transcript.txt"
    service.formatter.save_output.return_value = "/tmp/output.md"
    service.formatter.save_metrics.return_value = {}

    # Execute
    result = service.process_audio(job)

    # Verify the mock transcriber was used
    assert result.transcription_text == "Test transcription"
    assert result.success is True


def test_liskov_substitution_ai_summarizer():
    """Test that any AISummarizerPort implementation can be substituted."""
    # Use mock implementation
    mock_summarizer = MockAISummarizer("Mock summary text")

    # Create service with mocks
    mock_validator = MockAudioValidator()
    mock_transcriber = MockAudioTranscriber("Transcription text")

    service = TranscriptionService(
        file_reader=Mock(),
        validator=mock_validator,
        transcriber=mock_transcriber,
        summarizer=mock_summarizer,
        formatter=Mock(),
        job_repo=Mock(),
        save_files=False,
    )

    # Create job
    job = TranscriptionJob(
        job_id="test-456",
        audio_filename="test.mp3",
        audio_path="/tmp/test.mp3",
        mode="tecnico",
        email=None,
    )

    # Mock dependencies
    mock_audio_file = AudioFile(
        path="/tmp/test.mp3",
        filename="test.mp3",
        size_bytes=1024,
        extension="mp3",
    )
    service.file_reader.load.return_value = mock_audio_file
    service.formatter.save_transcription.return_value = "/tmp/transcript.txt"
    service.formatter.save_output.return_value = "/tmp/output.md"
    service.formatter.save_metrics.return_value = {}

    # Execute
    result = service.process_audio(job)

    # Verify the mock summarizer was used
    assert result.summary_output == "Mock summary text"


def test_liskov_substitution_audio_validator():
    """Test that any AudioValidatorPort implementation can be substituted."""
    # Use mock implementation that marks audio as invalid
    mock_validator = MockAudioValidator(valid=False, issues=["Invalid format"])

    service = TranscriptionService(
        file_reader=Mock(),
        validator=mock_validator,
        transcriber=Mock(),
        summarizer=Mock(),
        formatter=Mock(),
        job_repo=Mock(),
        save_files=False,
    )

    # Create job
    job = TranscriptionJob(
        job_id="test-789",
        audio_filename="test.mp3",
        audio_path="/tmp/test.mp3",
        mode="default",
        email=None,
    )

    # Mock file reader
    mock_audio_file = AudioFile(
        path="/tmp/test.mp3",
        filename="test.mp3",
        size_bytes=1024,
        extension="mp3",
    )
    service.file_reader.load.return_value = mock_audio_file

    # Execute - should raise AudioValidationError
    with pytest.raises(Exception):  # AudioValidationError from domain
        service.process_audio(job)


def test_single_responsibility_transcription_service():
    """Test that TranscriptionService has single responsibility: orchestrate transcription."""
    # Mock all dependencies
    mock_file_reader = Mock()
    mock_validator = Mock()
    mock_transcriber = Mock()
    mock_summarizer = Mock()
    mock_formatter = Mock()
    mock_job_repo = Mock()

    service = TranscriptionService(
        file_reader=mock_file_reader,
        validator=mock_validator,
        transcriber=mock_transcriber,
        summarizer=mock_summarizer,
        formatter=mock_formatter,
        job_repo=mock_job_repo,
        save_files=True,
    )

    # Setup mocks
    mock_audio_file = AudioFile(path="/tmp/test.mp3", filename="test.mp3", size_bytes=1024, extension="mp3")
    mock_file_reader.load.return_value = mock_audio_file
    mock_validator.validate.return_value = {"valid": True, "issues": [], "warnings": []}
    mock_transcriber.transcribe.return_value = ("Transcription", {})
    mock_summarizer.summarize.return_value = "Summary"
    mock_formatter.save_transcription.return_value = "/tmp/transcript.txt"
    mock_formatter.save_output.return_value = "/tmp/output.md"
    mock_formatter.save_metrics.return_value = {}
    mock_job_repo.set_status = Mock()

    job = TranscriptionJob(job_id="test", audio_filename="test.mp3", audio_path="/tmp/test.mp3", mode="default", email=None)

    result = service.process_audio(job)

    # Verify orchestration: each dependency was called exactly once
    mock_file_reader.load.assert_called_once_with("/tmp/test.mp3")
    mock_validator.validate.assert_called_once()
    mock_transcriber.transcribe.assert_called_once_with("/tmp/test.mp3")
    mock_summarizer.summarize.assert_called_once_with("Transcription", "default")
    mock_formatter.save_transcription.assert_called_once()
    mock_formatter.save_output.assert_called_once()
    mock_formatter.save_metrics.assert_called_once()

    assert result.success is True