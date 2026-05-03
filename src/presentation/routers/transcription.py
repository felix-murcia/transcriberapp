"""
FastAPI routers for TranscriberApp presentation layer.
Routers handle HTTP requests and delegate to application use cases.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import logging
from typing import Optional
from datetime import datetime

from presentation.schemas import (
    ProcessAudioRequest as ProcessAudioRequestSchema,
    ProcessAudioResponse as ProcessAudioResponseSchema,
    JobStatusResponse,
    ChunkUploadRequest,
    ChunkUploadResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
    SummarizeTextRequest,
    SummarizeTextResponse,
    ChatMessageRequest,
    ErrorResponse,
)
from presentation.dependencies import (
    get_process_audio_use_case,
    get_process_chunked_use_case,
    get_job_status_use_case,
    get_summarize_text_use_case,
)
from application.use_cases import ProcessChunkedTranscriptionUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["transcription"])


@router.post(
    "/process-audio",
    response_model=ProcessAudioResponseSchema,
    summary="Process complete audio file",
    description="Upload and process a complete audio file through transcription pipeline."
)
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to process"),
    mode: str = Form(..., description="Summarization mode", examples=["tecnico"]),
    email: Optional[str] = Form(None, description="Email for notifications"),
    use_case = Depends(get_process_audio_use_case)
):
    """
    Process a complete audio file.

    - **file**: Audio file (mp3, webm, wav, etc.)
    - **mode**: Summarization mode (default, tecnico, refinamiento, ejecutivo, bullet)
    - **email**: Optional email for completion notifications
    """
    try:
        # Validate file type
        allowed_extensions = {".mp3", ".webm", ".wav", ".m4a", ".ogg"}
        file_extension = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save uploaded file temporarily
        temp_path = f"/tmp/upload_{datetime.now().timestamp()}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Create request DTO
        request = ProcessAudioRequestSchema(
            audio_path=temp_path,
            filename=file.filename,
            mode=mode,
            email=email
        )

        # Execute use case
        result = await use_case.execute(request)

        # Clean up temp file in background
        background_tasks.add_task(_cleanup_file, temp_path)

        return ProcessAudioResponseSchema(**result.__dict__)

    except Exception as e:
        logger.error(f"Error processing audio file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/upload-chunk",
    response_model=ChunkUploadResponse,
    summary="Upload audio chunk",
    description="Upload a chunk of a large audio file for streaming processing."
)
async def upload_chunk(
    background_tasks: BackgroundTasks,
    chunk: UploadFile = File(..., description="Audio chunk file"),
    chunkIndex: int = Form(..., description="Chunk index (0-based)"),
    totalChunks: int = Form(..., description="Total number of chunks"),
    uploadId: str = Form(..., description="Unique upload identifier"),
    nombre: str = Form(..., description="Original filename"),
    modo: str = Form(..., description="Summarization mode"),
    email: Optional[str] = Form(None, description="Email for notifications"),
    extension: str = Form(..., description="File extension without dot"),
    chunked_use_case: ProcessChunkedTranscriptionUseCase = Depends(get_process_chunked_use_case)
):
    """
    Upload and process an audio chunk immediately.

    - **chunk**: Audio chunk file
    - **chunkIndex**: Index of this chunk (0-based)
    - **totalChunks**: Total number of chunks for this file
    - **uploadId**: Unique identifier for the upload session
    - **nombre**: Original filename
    - **modo**: Summarization mode
    - **email**: Optional email for notifications
    - **extension**: File extension (without dot)
    """
    try:
        # Create chunks directory
        chunks_base_dir = "/app/audios/chunks"
        upload_dir = f"{chunks_base_dir}/{uploadId}"
        import os
        os.makedirs(upload_dir, exist_ok=True)

        # Initialize metadata on first chunk
        metadata_path = f"{upload_dir}/metadata.json"
        job_id = None

        if chunkIndex == 0:
            import json
            metadata = {
                "upload_id": uploadId,
                "original_filename": nombre,
                "total_chunks": totalChunks,
                "created_at": datetime.now().isoformat(),
                "job_id": None,
                "chunks": []
            }

            # Create job for this upload
            job_use_case = get_job_status_use_case()
            # TODO: Create job through proper use case

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        # Load job_id from metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        job_id = metadata["job_id"]

        # Save chunk with extension
        chunk_filename = "06d"
        chunk_path = f"{upload_dir}/{chunk_filename}"
        with open(chunk_path, "wb") as f:
            content = await chunk.read()
            f.write(content)

        chunk_size = len(content)

        # Update metadata with chunk info
        chunk_info = {
            "index": chunkIndex,
            "filename": chunk_filename,
            "path": chunk_path,
            "size": chunk_size,
            "status": "received"
        }
        metadata["chunks"].append(chunk_info)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Start processing this chunk asynchronously
        background_tasks.add_task(
            chunked_use_case.process_single_chunk,
            job_id=job_id,
            chunk_path=chunk_path,
            chunk_index=chunkIndex
        )

        return ChunkUploadResponse(
            status="chunk_received_and_processing_started",
            chunk_index=chunkIndex,
            upload_id=uploadId,
            job_id=job_id,
            message=f"Chunk {chunkIndex + 1}/{totalChunks} accepted, processing in background"
        )

    except Exception as e:
        logger.error(f"Error uploading chunk {chunkIndex} for {uploadId}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/upload-complete",
    response_model=UploadCompleteResponse,
    summary="Complete chunked upload",
    description="Signal that all chunks have been uploaded and finalize processing."
)
async def upload_complete(
    background_tasks: BackgroundTasks,
    request: UploadCompleteRequest,
    chunked_use_case: ProcessChunkedTranscriptionUseCase = Depends(get_process_chunked_use_case)
):
    """
    Complete a chunked upload and finalize transcription.

    - **upload_id**: Upload identifier from chunk uploads
    - **filename**: Original filename
    - **mode**: Summarization mode
    - **email**: Optional email for notifications
    """
    try:
        # Validate upload exists
        chunks_base_dir = "/app/audios/chunks"
        upload_dir = f"{chunks_base_dir}/{request.upload_id}"

        if not os.path.exists(upload_dir):
            raise HTTPException(status_code=404, detail="Upload not found")

        # Load metadata
        metadata_path = f"{upload_dir}/metadata.json"
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=400, detail="Metadata not found")

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        job_id = metadata.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Job not found")

        # Validate all chunks are present
        expected_chunks = metadata["total_chunks"]
        received_chunks = len(metadata["chunks"])

        if received_chunks != expected_chunks:
            raise HTTPException(
                status_code=400,
                detail=f"Missing chunks: expected {expected_chunks}, received {received_chunks}"
            )

        # Finalize processing asynchronously
        background_tasks.add_task(
            chunked_use_case.finalize_chunked_transcription,
            job_id=job_id
        )

        return UploadCompleteResponse(
            status="finalizing",
            job_id=job_id,
            message=f"All {received_chunks} chunks received. Finalizing transcription..."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing upload {request.upload_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/job/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Retrieve the current status and progress of a transcription job."
)
async def get_job_status(
    job_id: str,
    use_case = Depends(get_job_status_use_case)
):
    """
    Get the status of a transcription job.

    - **job_id**: Unique job identifier
    """
    try:
        result = use_case.execute(job_id)
        return result

    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/summarize-text",
    response_model=SummarizeTextResponse,
    summary="Summarize existing text",
    description="Process existing transcription text through summarization pipeline."
)
async def summarize_text(
    request: SummarizeTextRequest,
    use_case = Depends(get_summarize_text_use_case)
):
    """
    Summarize existing transcription text.

    - **text**: Text to summarize
    - **mode**: Summarization mode
    - **filename**: Reference filename
    - **email**: Optional email for notifications
    """
    try:
        result = await use_case.execute(
            text=request.text,
            mode=request.mode,
            filename=request.filename,
            email=request.email,
            job_id=request.job_id
        )

        return SummarizeTextResponse(**result.__dict__)

    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# TODO: Implement chat endpoint
# @router.post(
#     "/chat",
#     summary="Stream chat response",
#     description="Send a message and stream AI response for transcription assistance."
# )
# async def chat_stream(
#     request: ChatMessageRequest,
#     use_case = Depends(get_chat_use_case)
# ):
#     """
#     Stream chat response for transcription assistance.
#
#     - **message**: User message
#     - **mode**: Agent mode (default, tecnico, etc.)
#     """
#     try:
#         return StreamingResponse(
#             use_case.execute(message=request.message, mode=request.mode),
#             media_type="text/plain"
#         )
#
#     except Exception as e:
#         logger.error(f"Error in chat stream: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


async def _cleanup_file(file_path: str):
    """Background task to clean up temporary files."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup {file_path}: {e}")