"""
Application Data Transfer Objects (DTOs).
DTOs for request/response data validation and serialization.
Uses Pydantic v2 for input/output validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AudioValidationResult(BaseModel):
    """Result of audio validation."""
    valid: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProcessAudioRequest(BaseModel):
    """Request DTO for audio processing."""
    audio_path: str
    filename: str
    mode: str = Field(..., description="Summarization mode")
    email: Optional[str] = None
    job_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "audio_path": "/path/to/audio.mp3",
                "filename": "meeting.mp3",
                "mode": "tecnico",
                "email": "user@example.com",
                "job_id": "optional-custom-id"
            }
        }


class ProcessAudioResponse(BaseModel):
    """Response DTO for audio processing."""
    success: bool
    job_id: str
    transcription_text: Optional[str] = None
    summary_text: Optional[str] = None
    mode: str
    processing_time_seconds: Optional[float] = None
    audio_validation: AudioValidationResult

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "job_id": "abc-123-def",
                "transcription_text": "Full transcription text...",
                "summary_text": "Summary of the transcription...",
                "mode": "tecnico",
                "processing_time_seconds": 45.2,
                "audio_validation": {
                    "valid": True,
                    "issues": [],
                    "warnings": []
                }
            }
        }


class JobStatusResponse(BaseModel):
    """Response DTO for job status queries."""
    job_id: str
    status: str
    exists: bool
    filename: Optional[str] = None
    mode: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Optional[float] = Field(None, description="Progress 0.0-1.0 for chunked jobs")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc-123-def",
                "status": "completed",
                "exists": True,
                "filename": "meeting.mp3",
                "mode": "tecnico",
                "created_at": "2023-01-01T10:00:00Z",
                "completed_at": "2023-01-01T10:02:30Z",
                "error_message": None,
                "progress": 1.0
            }
        }


class ChunkUploadRequest(BaseModel):
    """Request DTO for chunk uploads."""
    upload_id: str
    chunk_index: int
    total_chunks: int
    filename: str
    extension: str
    mode: str
    email: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "upload-123",
                "chunk_index": 0,
                "total_chunks": 10,
                "filename": "meeting.webm",
                "extension": "webm",
                "mode": "tecnico",
                "email": "user@example.com"
            }
        }


class ChunkUploadResponse(BaseModel):
    """Response DTO for chunk uploads."""
    status: str
    chunk_index: int
    upload_id: str
    job_id: str
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "chunk_received_and_processing_started",
                "chunk_index": 0,
                "upload_id": "upload-123",
                "job_id": "job-456",
                "message": "Chunk accepted, processing in background"
            }
        }


class UploadCompleteRequest(BaseModel):
    """Request DTO for upload completion."""
    upload_id: str
    filename: str
    mode: str
    email: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "upload-123",
                "filename": "meeting.webm",
                "mode": "tecnico",
                "email": "user@example.com"
            }
        }


class UploadCompleteResponse(BaseModel):
    """Response DTO for upload completion."""
    status: str
    job_id: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "finalizing",
                "job_id": "job-456",
                "message": "All chunks received. Finalizing transcription..."
            }
        }


class SummarizeTextRequest(BaseModel):
    """Request DTO for text summarization."""
    text: str = Field(..., description="Text to summarize")
    mode: str = Field(..., description="Summarization mode")
    filename: str = Field(..., description="Reference filename")
    email: Optional[str] = None
    job_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Long transcription text to summarize...",
                "mode": "ejecutivo",
                "filename": "meeting_transcript.txt",
                "email": "user@example.com"
            }
        }


class ChatMessageRequest(BaseModel):
    """Request DTO for chat/streaming responses."""
    message: str = Field(..., description="User message")
    mode: str = Field(default="default", description="Agent mode")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Can you summarize the key points?",
                "mode": "tecnico"
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response DTO."""
    success: bool = False
    error_type: str
    error_message: str
    job_id: Optional[str] = None
    details: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_type": "validation_error",
                "error_message": "Audio file format not supported",
                "job_id": "job-456",
                "details": {
                    "supported_formats": ["mp3", "webm", "wav"],
                    "provided_format": "exe"
                }
            }
        }