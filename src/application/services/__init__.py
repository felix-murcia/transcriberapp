"""
Application services for TranscriberApp.
Services contain reusable business logic that can be shared across use cases.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from domain.ports import (
    AudioProcessingPort,
    FileStoragePort
)
from domain.entities import AudioFile
from domain.value_objects import AudioMetadata

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """Service for audio processing operations."""

    def __init__(self, audio_processor: AudioProcessingPort, file_storage: FileStoragePort):
        self.audio_processor = audio_processor
        self.file_storage = file_storage

    def validate_and_prepare_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Validate audio file and prepare it for processing.

        Returns:
            Dict with validation results and prepared file info
        """
        logger.info(f"Validating and preparing audio: {audio_path}")

        # Validate audio
        validation_result = self.audio_processor.validate_audio(audio_path)

        if not validation_result.get("valid", False):
            return {
                "valid": False,
                "validation_result": validation_result,
                "prepared_path": None,
                "metadata": None
            }

        # Get metadata
        metadata = self.audio_processor.get_audio_metadata(audio_path)

        # Clean/normalize audio for better transcription
        logger.info("Cleaning audio for better transcription quality")
        cleaned_audio = self.audio_processor.clean_audio(audio_path)

        # Save cleaned audio temporarily
        filename = f"cleaned_{Path(audio_path).name}"
        prepared_path = self.file_storage.save_file(cleaned_audio, filename, "temp")

        return {
            "valid": True,
            "validation_result": validation_result,
            "prepared_path": prepared_path,
            "metadata": metadata
        }

    def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files."""
        for path in file_paths:
            try:
                self.file_storage.delete_file(path)
                logger.info(f"Cleaned up temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {path}: {e}")


class TranscriptionWorkflowService:
    """Service for managing transcription workflows."""

    def __init__(self, audio_processing: AudioProcessingService):
        self.audio_processing = audio_processing

    def prepare_transcription_workflow(self, audio_path: str) -> Dict[str, Any]:
        """
        Prepare everything needed for transcription workflow.

        Returns:
            Dict with workflow preparation results
        """
        # Validate and prepare audio
        prep_result = self.audio_processing.validate_and_prepare_audio(audio_path)

        if not prep_result["valid"]:
            return prep_result

        # Determine if chunking is needed
        metadata = prep_result["metadata"]
        file_size = Path(audio_path).stat().st_size

        # Simple chunking decision (can be made more sophisticated)
        needs_chunking = file_size > 25 * 1024 * 1024  # 25MB

        workflow_info = {
            **prep_result,
            "needs_chunking": needs_chunking,
            "estimated_chunks": self._estimate_chunks(file_size) if needs_chunking else 1
        }

        return workflow_info

    def _estimate_chunks(self, file_size_bytes: int) -> int:
        """Estimate number of chunks needed."""
        # Rough estimation: 10MB per chunk
        chunk_size = 10 * 1024 * 1024  # 10MB
        estimated_chunks = max(1, file_size_bytes // chunk_size)
        return min(estimated_chunks, 50)  # Cap at 50 chunks


class JobManagementService:
    """Service for job lifecycle management."""

    def __init__(self, job_repository):
        self.job_repository = job_repository

    def create_job_tracking(self, job_data: Dict[str, Any]) -> str:
        """Create and start tracking a new job."""
        # This would create a job entity and save it
        # Implementation depends on the job repository interface
        pass

    def update_job_progress(self, job_id: str, progress: float, metadata: Dict[str, Any] = None) -> None:
        """Update job progress."""
        # Implementation depends on job repository
        pass

    def finalize_job(self, job_id: str, results: Dict[str, Any]) -> None:
        """Finalize a completed job."""
        # Implementation depends on job repository
        pass


class NotificationService:
    """Service for handling notifications (email, webhooks, etc.)."""

    def __init__(self, email_service):
        self.email_service = email_service

    def notify_job_completion(self, job_id: str, results: Dict[str, Any]) -> None:
        """Send notifications when job is completed."""
        # Implementation depends on notification requirements
        pass

    def notify_job_failure(self, job_id: str, error: str) -> None:
        """Send notifications when job fails."""
        # Implementation depends on notification requirements
        pass