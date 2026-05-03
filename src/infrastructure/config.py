"""
Infrastructure configuration and dependency injection container.
Provides concrete implementations wired together.
"""

from functools import lru_cache

from .external import (
    GroqTranscriptionAdapter,
    RemoteFFmpegAdapter,
    GeminiSummarizerAdapter,
    SMTPEmailAdapter,
    LocalFileStorageAdapter,
    FileBasedJobRepository,
)

from application.use_cases import (
    ProcessAudioTranscriptionUseCase,
    ProcessChunkedTranscriptionUseCase,
    GetJobStatusUseCase,
    SummarizeExistingTranscriptionUseCase,
)


@lru_cache()
def get_transcription_service():
    """Get transcription service (Groq)."""
    return GroqTranscriptionAdapter()


@lru_cache()
def get_audio_processor():
    """Get audio processor (FFmpeg)."""
    return RemoteFFmpegAdapter()


@lru_cache()
def get_summarizer():
    """Get AI summarizer (Gemini)."""
    return GeminiSummarizerAdapter()


@lru_cache()
def get_email_service():
    """Get email service (SMTP)."""
    return SMTPEmailAdapter()


@lru_cache()
def get_file_storage():
    """Get file storage service."""
    return LocalFileStorageAdapter()


@lru_cache()
def get_job_repository():
    """Get job repository."""
    return FileBasedJobRepository()


@lru_cache()
def get_audio_reader():
    """Get audio reader service."""
    # TODO: Implement LocalAudioFileReader adapter
    return None


# Use Case Dependencies

@lru_cache()
def get_process_audio_use_case():
    """Get process audio use case with dependencies."""
    return ProcessAudioTranscriptionUseCase(
        transcription_service=get_transcription_service(),
        audio_processor=get_audio_processor(),
        summarizer=get_summarizer(),
        job_repository=get_job_repository(),
        file_storage=get_file_storage(),
        audio_reader=get_audio_reader()
    )


@lru_cache()
def get_process_chunked_use_case():
    """Get process chunked audio use case with dependencies."""
    return ProcessChunkedTranscriptionUseCase(
        transcription_service=get_transcription_service(),
        audio_processor=get_audio_processor(),
        summarizer=get_summarizer(),
        job_repository=get_job_repository(),
        file_storage=get_file_storage()
    )


@lru_cache()
def get_job_status_use_case():
    """Get job status use case with dependencies."""
    return GetJobStatusUseCase(
        job_repository=get_job_repository()
    )


@lru_cache()
def get_summarize_text_use_case():
    """Get summarize text use case with dependencies."""
    return SummarizeExistingTranscriptionUseCase(
        summarizer=get_summarizer(),
        job_repository=get_job_repository(),
        file_storage=get_file_storage()
    )