"""
Application use cases for TranscriberApp.
Use cases orchestrate business logic using domain ports.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from application.dtos import (
    ProcessAudioRequest,
    ProcessAudioResponse,
    JobStatusResponse,
    AudioValidationResult
)
from domain.entities import TranscriptionJob
from domain.ports import (
    TranscriptionServicePort,
    AudioProcessingPort,
    AISummarizerPort,
    JobRepositoryPort,
    FileStoragePort,
    AudioReaderPort
)
from domain.exceptions import (
    AudioValidationError,
    TranscriptionError,
    SummarizationError
)
import uuid


class ProcessAudioTranscriptionUseCase:
    """Use case for processing complete audio files through transcription pipeline."""

    def __init__(
        self,
        transcription_service: TranscriptionServicePort,
        audio_processor: AudioProcessingPort,
        summarizer: AISummarizerPort,
        job_repository: JobRepositoryPort,
        file_storage: FileStoragePort,
        audio_reader: AudioReaderPort
    ):
        self.transcription_service = transcription_service
        self.audio_processor = audio_processor
        self.summarizer = summarizer
        self.job_repository = job_repository
        self.file_storage = file_storage
        self.audio_reader = audio_reader

    def execute(self, request: ProcessAudioRequest) -> ProcessAudioResponse:
        """
        Execute complete audio transcription workflow.

        Steps:
        1. Create and save job
        2. Validate audio file
        3. Transcribe audio
        4. Generate summary
        5. Save results
        6. Update job status
        """
        job_id = request.job_id or str(uuid.uuid4())

        # Create job entity
        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=request.filename,
            audio_path=request.audio_path,
            mode=request.mode,
            email=request.email
        )

        try:
            # Save initial job state
            self.job_repository.save(job)

            # Validate audio
            validation_result = self.audio_processor.validate_audio(request.audio_path)
            if not validation_result.get("valid", False):
                issues = validation_result.get("issues", [])
                raise AudioValidationError(
                    f"Audio validation failed: {', '.join(issues)}",
                    validation_result
                )

            # Update job status
            job.status = "processing"
            self.job_repository.save(job)

            # Transcribe audio
            transcription_text, transcription_metadata = self.transcription_service.transcribe_audio(request.audio_path)

            # Update job with transcription
            job.transcription_text = transcription_text
            self.job_repository.save(job)

            # Generate summary
            summary_text = self.summarizer.summarize(transcription_text, request.mode)

            # Update job with summary
            job.summary_output = summary_text
            job.status = "completed"
            job.completed_at = datetime.now()
            self.job_repository.save(job)

            # Create response
            response = ProcessAudioResponse(
                success=True,
                job_id=job_id,
                transcription_text=transcription_text,
                summary_text=summary_text,
                mode=request.mode,
                processing_time_seconds=transcription_metadata.get("transcription_time", 0),
                audio_validation=AudioValidationResult(
                    valid=True,
                    issues=[],
                    warnings=validation_result.get("warnings", [])
                )
            )

            return response

        except AudioValidationError as e:
            job.status = "error"
            job.error_message = str(e)
            self.job_repository.save(job)
            raise

        except TranscriptionError as e:
            job.status = "error"
            job.error_message = str(e)
            self.job_repository.save(job)
            raise

        except SummarizationError as e:
            job.status = "error"
            job.error_message = str(e)
            self.job_repository.save(job)
            raise

        except Exception as e:
            job.status = "error"
            job.error_message = f"Unexpected error: {str(e)}"
            self.job_repository.save(job)
            raise TranscriptionError(f"Processing failed: {str(e)}") from e


class ProcessChunkedTranscriptionUseCase:
    """Use case for processing chunked audio files."""

    def __init__(
        self,
        transcription_service: TranscriptionServicePort,
        audio_processor: AudioProcessingPort,
        summarizer: AISummarizerPort,
        job_repository: JobRepositoryPort,
        file_storage: FileStoragePort
    ):
        self.transcription_service = transcription_service
        self.audio_processor = audio_processor
        self.summarizer = summarizer
        self.job_repository = job_repository
        self.file_storage = file_storage

    def process_single_chunk(self, job_id: str, chunk_path: str, chunk_index: int) -> None:
        """Process a single chunk and update job."""
        job = self.job_repository.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        try:
            # Convert chunk to MP3
            mp3_data = self.audio_processor.convert_audio(chunk_path, "mp3")

            # Save temp file for transcription
            temp_path = f"/tmp/chunk_{job_id}_{chunk_index}.mp3"
            with open(temp_path, "wb") as f:
                f.write(mp3_data)

            # Transcribe chunk
            transcription_text, _ = self.transcription_service.transcribe_audio(temp_path)

            # Update job with partial transcription
            job.partial_transcriptions[chunk_index] = transcription_text
            job.processed_chunks += 1

            # Clean up temp file and chunk
            import os
            os.unlink(temp_path)
            os.unlink(chunk_path)

            self.job_repository.save(job)

        except Exception as e:
            # Mark chunk as failed but continue
            job.partial_transcriptions[chunk_index] = f"[ERROR: {str(e)}]"
            job.processed_chunks += 1
            self.job_repository.save(job)

    def finalize_chunked_transcription(self, job_id: str) -> ProcessAudioResponse:
        """Combine partial transcriptions and generate final summary."""
        job = self.job_repository.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Combine transcriptions
        combined_transcription = job.get_combined_transcription()

        # Generate summary
        summary_text = self.summarizer.summarize(combined_transcription, job.mode)

        # Update job
        job.transcription_text = combined_transcription
        job.summary_output = summary_text
        job.status = "completed"
        job.completed_at = datetime.now()
        self.job_repository.save(job)

        return ProcessAudioResponse(
            success=True,
            job_id=job_id,
            transcription_text=combined_transcription,
            summary_text=summary_text,
            mode=job.mode,
            processing_time_seconds=0,  # Not tracked for chunked
            audio_validation=AudioValidationResult(valid=True, issues=[], warnings=[])
        )


class GetJobStatusUseCase:
    """Use case for retrieving job status."""

    def __init__(self, job_repository: JobRepositoryPort):
        self.job_repository = job_repository

    def execute(self, job_id: str) -> JobStatusResponse:
        """Get status of a specific job."""
        job = self.job_repository.get_by_id(job_id)

        if not job:
            return JobStatusResponse(
                job_id=job_id,
                status="not_found",
                exists=False
            )

        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            exists=True,
            filename=job.audio_filename,
            mode=job.mode,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            progress=job.processed_chunks / job.total_chunks if job.total_chunks else None
        )


class SummarizeExistingTranscriptionUseCase:
    """Use case for summarizing existing transcription text."""

    def __init__(
        self,
        summarizer: AISummarizerPort,
        job_repository: JobRepositoryPort,
        file_storage: FileStoragePort
    ):
        self.summarizer = summarizer
        self.job_repository = job_repository
        self.file_storage = file_storage

    def execute(self, text: str, mode: str, filename: str, job_id: Optional[str] = None) -> ProcessAudioResponse:
        """Summarize existing transcription text."""
        job_id = job_id or str(uuid.uuid4())

        # Create job for text processing
        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=filename,
            mode=mode,
            transcription_text=text  # Pre-populated
        )

        try:
            self.job_repository.save(job)

            # Generate summary
            summary_text = self.summarizer.summarize(text, mode)

            # Update job
            job.summary_output = summary_text
            job.status = "completed"
            job.completed_at = datetime.now()
            self.job_repository.save(job)

            return ProcessAudioResponse(
                success=True,
                job_id=job_id,
                transcription_text=text,
                summary_text=summary_text,
                mode=mode,
                processing_time_seconds=0,
                audio_validation=AudioValidationResult(valid=True, issues=[], warnings=[])
            )

        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            self.job_repository.save(job)
            raise SummarizationError(f"Text summarization failed: {str(e)}", mode=mode) from e