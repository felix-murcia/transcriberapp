"""
Application layer - use cases.
Defines specific business operations the application can perform.
"""

from transcriber_app.domain.services import TranscriptionService
from transcriber_app.domain.entities import TranscriptionJob
from transcriber_app.domain.exceptions import AudioValidationError
import uuid


class ProcessAudioUseCase:
    """Use case: Process an audio file through transcription pipeline."""

    def __init__(self, transcription_service: TranscriptionService):
        self.transcription_service = transcription_service

    def execute(
        self,
        audio_path: str,
        mode: str,
        email: str = None,
        job_id: str = None,
    ) -> dict:
        """
        Execute audio processing.

        Args:
            audio_path: Path to audio file
            mode: Summarization mode
            email: Optional email for notifications
            job_id: Optional job ID (auto-generated if not provided)

        Returns:
            dict: Processing result
        """
        if job_id is None:
            job_id = str(uuid.uuid4())

        audio_filename = audio_path.split("/")[-1]  # Simple extraction, use pathlib in prod

        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=audio_filename,
            audio_path=audio_path,
            mode=mode,
            email=email,
        )

        try:
            result = self.transcription_service.process_audio(job)
            return {
                "status": result.success,
                "job_id": result.job_id,
                "transcription": result.transcription_text,
                "summary": result.summary_output,
                "mode": result.mode,
            }
        except AudioValidationError as e:
            return {
                "status": "error",
                "error_type": "validation_error",
                "job_id": job_id,
                "error": str(e),
                "validation_result": e.validation_result,
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "processing_error",
                "job_id": job_id,
                "error": str(e),
            }


class ProcessTextUseCase:
    """Use case: Process existing text through summarization."""

    def __init__(self, transcription_service: TranscriptionService):
        self.transcription_service = transcription_service

    def execute(
        self,
        text: str,
        mode: str,
        filename: str,
        email: str = None,
        job_id: str = None,
        save_files: bool = True,
    ) -> dict:
        """
        Execute text processing.

        Args:
            text: Text to process
            mode: Summarization mode
            filename: Filename for reference
            email: Optional email
            job_id: Optional job ID
            save_files: Whether to save output files

        Returns:
            dict: Processing result
        """
        if job_id is None:
            job_id = str(uuid.uuid4())

        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=filename,
            audio_path=None,
            mode=mode,
            email=email,
        )

        # Temporarily override the service's save_files setting
        original_setting = self.transcription_service.save_files
        self.transcription_service.save_files = save_files

        try:
            result = self.transcription_service.process_text(job, text)
            return {
                "status": result.success,
                "job_id": result.job_id,
                "transcription": result.transcription_text,
                "markdown": result.summary_output,
                "mode": result.mode,
            }
        finally:
            self.transcription_service.save_files = original_setting


class GetJobStatusUseCase:
    """Use case: Get job status."""

    def __init__(self, job_repo):
        self.job_repo = job_repo

    def execute(self, job_id: str) -> dict:
        """
        Get status of a job.

        Args:
            job_id: Job ID

        Returns:
            dict: Job status
        """
        status = self.job_repo.get_status(job_id)
        if status is None:
            return {"job_id": job_id, "status": "unknown"}
        return status


class StreamChatResponseUseCase:
    """Use case: Stream chat response."""

    def __init__(self, summarizer):
        self.summarizer = summarizer

    def execute(self, message: str, mode: str = "default"):
        """
        Stream chat response.

        Args:
            message: User message
            mode: Agent mode

        Yields:
            str: Response chunks
        """
        agent = self.summarizer.get_agent(mode)
        result = agent.run(message, stream=True)
        for chunk in result:
            if chunk:
                yield chunk
