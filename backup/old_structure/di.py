"""
Dependency Injection - Composition Root for Hexagonal Architecture.

This module provides factory functions for all dependencies in the application.
It follows the Dependency Inversion Principle by wiring domain ports (abstractions)
with their concrete infrastructure implementations.

Usage:
- Web API: Import and use factories directly
- CLI: Import and use factories
- Tests: Mock ports and inject via TranscriptionService constructor

This separation ensures the domain remains independent of infrastructure details.
"""

from transcriber_app.domain.ports import (
    AudioFileReaderPort,
    AudioValidatorPort,
    AudioTranscriberPort,
    AISummarizerPort,
    OutputFormatterPort,
    JobStatusRepositoryPort,
    JobQueuePort,
    SessionManagerPort,
)
from transcriber_app.domain.services import TranscriptionService
from transcriber_app.application.use_cases import (
    ProcessAudioUseCase,
    ProcessTextUseCase,
    GetJobStatusUseCase,
    StreamChatResponseUseCase,
)


def get_audio_file_reader() -> AudioFileReaderPort:
    from transcriber_app.infrastructure.file_processing import LocalAudioFileReader
    return LocalAudioFileReader()


def get_audio_validator() -> AudioValidatorPort:
    from transcriber_app.infrastructure.validation import FFmpegAudioValidator
    return FFmpegAudioValidator()


def get_audio_transcriber() -> AudioTranscriberPort:
    from transcriber_app.infrastructure.transcription import GroqAudioTranscriber
    return GroqAudioTranscriber()


def get_ai_summarizer() -> AISummarizerPort:
    from transcriber_app.infrastructure.ai import GeminiAISummarizer
    return GeminiAISummarizer(model_name="gemini")


def get_output_formatter() -> OutputFormatterPort:
    from transcriber_app.infrastructure.storage import LocalOutputFormatter
    return LocalOutputFormatter()


def get_job_status_repository() -> JobStatusRepositoryPort:
    from transcriber_app.infrastructure.persistence import FileBasedJobStatusRepository
    return FileBasedJobStatusRepository()


def get_job_queue() -> JobQueuePort:
    # For CLI, no background tasks, so use a simple adapter
    from transcriber_app.infrastructure.queue import SynchronousJobQueueAdapter
    return SynchronousJobQueueAdapter()


def get_session_manager() -> SessionManagerPort:
    # Session manager is optional - some endpoints may not require auth
    return None


def get_transcription_service(save_files: bool = True) -> TranscriptionService:
    """Factory for creating a transcription service with all dependencies."""
    return TranscriptionService(
        file_reader=get_audio_file_reader(),
        validator=get_audio_validator(),
        transcriber=get_audio_transcriber(),
        summarizer=get_ai_summarizer(),
        formatter=get_output_formatter(),
        job_repo=get_job_status_repository(),
        save_files=save_files,
    )


def get_process_audio_use_case(save_files: bool = True) -> ProcessAudioUseCase:
    """Factory for ProcessAudioUseCase."""
    service = get_transcription_service(save_files=save_files)
    return ProcessAudioUseCase(service)


def get_process_text_use_case(save_files: bool = True) -> ProcessTextUseCase:
    """Factory for ProcessTextUseCase."""
    service = get_transcription_service(save_files=save_files)
    return ProcessTextUseCase(service)


def get_get_job_status_use_case() -> GetJobStatusUseCase:
    """Factory for GetJobStatusUseCase."""
    repo = get_job_status_repository()
    return GetJobStatusUseCase(repo)


def get_stream_chat_response_use_case() -> StreamChatResponseUseCase:
    """Factory for StreamChatResponseUseCase."""
    summarizer = get_ai_summarizer()
    return StreamChatResponseUseCase(summarizer)