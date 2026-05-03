"""
Pydantic v2 schemas for API requests and responses.
Used for input validation and response serialization.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Audio validation schemas
class AudioValidationResult(BaseModel):
    """Result of audio validation."""
    valid: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# Process audio schemas
class ProcessAudioRequest(BaseModel):
    """Request schema for audio processing."""
    audio_path: str = Field(..., description="Path to audio file")
    filename: str = Field(..., description="Audio filename")
    mode: str = Field(
        ...,
        description="Summarization mode",
        examples=["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]
    )
    email: Optional[str] = Field(None, description="Email for notifications")
    job_id: Optional[str] = Field(None, description="Optional custom job ID")


class ProcessAudioResponse(BaseModel):
    """Response schema for audio processing."""
    success: bool
    job_id: str
    transcription_text: Optional[str] = None
    summary_text: Optional[str] = None
    mode: str
    processing_time_seconds: Optional[float] = None
    audio_validation: AudioValidationResult


# Chunk upload schemas
class ChunkUploadRequest(BaseModel):
    """Request schema for chunk uploads."""
    upload_id: str = Field(..., description="Unique upload identifier")
    chunk_index: int = Field(..., description="Chunk index (0-based)")
    total_chunks: int = Field(..., description="Total number of chunks")
    filename: str = Field(..., description="Original filename")
    extension: str = Field(..., description="File extension without dot")
    mode: str = Field(..., description="Summarization mode")
    email: Optional[str] = Field(None, description="Email for notifications")


class ChunkUploadResponse(BaseModel):
    """Response schema for chunk uploads."""
    status: str
    chunk_index: int
    upload_id: str
    job_id: str
    message: Optional[str] = None


# Upload complete schemas
class UploadCompleteRequest(BaseModel):
    """Request schema for upload completion."""
    upload_id: str = Field(..., description="Upload identifier")
    filename: str = Field(..., description="Original filename")
    mode: str = Field(..., description="Summarization mode")
    email: Optional[str] = Field(None, description="Email for notifications")


class UploadCompleteResponse(BaseModel):
    """Response schema for upload completion."""
    status: str
    job_id: str
    message: str


# Job status schemas
class JobStatusResponse(BaseModel):
    """Response schema for job status queries."""
    job_id: str
    status: str
    exists: bool
    filename: Optional[str] = None
    mode: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Optional[float] = Field(None, description="Progress 0.0-1.0 for chunked jobs")


# Text summarization schemas
class SummarizeTextRequest(BaseModel):
    """Request schema for text summarization."""
    text: str = Field(..., description="Text to summarize", min_length=1)
    mode: str = Field(
        ...,
        description="Summarization mode",
        examples=["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]
    )
    filename: str = Field(..., description="Reference filename")
    email: Optional[str] = Field(None, description="Email for notifications")
    job_id: Optional[str] = Field(None, description="Optional custom job ID")


class SummarizeTextResponse(BaseModel):
    """Response schema for text summarization."""
    success: bool
    job_id: str
    transcription_text: Optional[str] = None  # The original text
    summary_text: Optional[str] = None
    mode: str
    processing_time_seconds: Optional[float] = None
    audio_validation: AudioValidationResult  # Not applicable but kept for consistency


# Chat schemas
class ChatMessageRequest(BaseModel):
    """Request schema for chat messages."""
    message: str = Field(..., description="User message", min_length=1)
    mode: str = Field(
        default="default",
        description="Agent mode for response",
        examples=["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]
    )


# Error schemas
class ErrorResponse(BaseModel):
    """Generic error response schema."""
    success: bool = Field(default=False, description="Always false for errors")
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Human-readable error message")
    job_id: Optional[str] = Field(None, description="Related job ID if applicable")
    details: Optional[dict] = Field(None, description="Additional error details")


# Health check schemas
class HealthCheckResponse(BaseModel):
    """Response schema for health checks."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: Optional[str] = None
    services: Optional[dict] = Field(None, description="Status of dependent services")


# Configuration schemas
class AppConfig(BaseModel):
    """Application configuration schema."""
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    max_file_size_mb: int = 25
    supported_formats: List[str] = ["mp3", "webm", "wav", "m4a", "ogg"]
    available_modes: List[str] = ["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]