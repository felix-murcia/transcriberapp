"""
Primary adapters - HTTP/API layer (FastAPI).
Converts external HTTP requests into use case invocations.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse

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
from transcriber_app.application.use_cases import (
    ProcessAudioUseCase,
    ProcessTextUseCase,
    GetJobStatusUseCase,
    StreamChatResponseUseCase,
)
from transcriber_app.infrastructure.logging.logging_config import setup_logging

logger = setup_logging("transcribeapp")

router = APIRouter(prefix="", tags=["api"])


# ============================================================================
# Dependency Injection - Ports provided by infrastructure
# ============================================================================

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
    from transcriber_app.infrastructure.persistence import InMemoryJobStatusRepository
    return InMemoryJobStatusRepository()


def get_job_queue(background_tasks: BackgroundTasks) -> JobQueuePort:
    from transcriber_app.infrastructure.queue import FastAPIBackgroundTasksAdapter
    adapter = FastAPIBackgroundTasksAdapter()
    adapter.set_background_tasks(background_tasks)
    return adapter


def get_session_manager() -> Optional[SessionManagerPort]:
    # Session manager is optional - some endpoints may not require auth
    return None


def get_transcription_service(
    background_tasks: Optional[BackgroundTasks] = None,
    save_files: bool = True,
):
    """Factory for creating a transcription service with all dependencies."""
    from transcriber_app.domain.services import TranscriptionService
    return TranscriptionService(
        file_reader=get_audio_file_reader(),
        validator=get_audio_validator(),
        transcriber=get_audio_transcriber(),
        summarizer=get_ai_summarizer(),
        formatter=get_output_formatter(),
        job_repo=get_job_status_repository(),
        save_files=save_files,
    )


def get_process_audio_use_case(background_tasks: BackgroundTasks, save_files: bool = True):
    """Factory for ProcessAudioUseCase."""
    service = get_transcription_service(background_tasks=background_tasks, save_files=save_files)
    return ProcessAudioUseCase(service)


# ============================================================================
# Authentication check
# ============================================================================

def check_auth(request: Request) -> bool:
    """Verify user authentication from cookies."""
    return request.cookies.get("logged_in") == "true"


def require_auth(request: Request):
    """Raise HTTPException if not authenticated."""
    if not check_auth(request):
        logger.warning("[AUTH] Authentication failed for request")
        raise HTTPException(status_code=401, detail="Authentication required")


# ============================================================================
# API Endpoints
# ============================================================================

VALID_MODES = ["default", "tecnico", "refinamiento", "ejecutivo", "bullet",
               "comparative", "product_manager", "project_manager", "quality_assurance"]
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "/tmp/recordings")


@router.post("/upload-audio")
async def upload_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
):
    """
    Receive audio uploaded from browser and start background processing.
    Single upload (not chunked).
    """
    # Auth check
    require_auth(request)

    # Mode validation
    if modo not in VALID_MODES:
        logger.error(f"[UPLOAD AUDIO] Invalid mode: {modo}")
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Prepare directory
    audios_dir = Path("audios")
    audios_dir.mkdir(exist_ok=True)

    # Save file
    safe_name = nombre.lower()
    original_ext = Path(audio.filename).suffix.lower() if audio.filename else ".webm"
    if not original_ext:
        original_ext = ".webm"

    audio_path = audios_dir / f"{safe_name}{original_ext}"

    # Read and save content
    audio_content = await audio.read()
    audio_size = len(audio_content)

    logger.info(f"[UPLOAD AUDIO] Receiving: nombre={nombre}, size={audio_size/1024/1024:.2f}MB, ext={original_ext}")

    with audio_path.open("wb") as f:
        f.write(audio_content)

    saved_size = audio_path.stat().st_size
    logger.info(f"[UPLOAD AUDIO] Saved to: {audio_path}, size: {saved_size/1024/1024:.2f}MB")

    # Create job ID
    job_id = str(uuid.uuid4())

    # Get use case
    use_case = get_process_audio_use_case(background_tasks, save_files=True)

    # Launch background task
    background_tasks.add_task(
        _process_audio_background,
        use_case=use_case,
        job_id=job_id,
        audio_path=str(audio_path),
        nombre=safe_name,
        modo=modo,
        email=email,
    )

    logger.info(f"[API ROUTE] Job {job_id} started for: {nombre}")

    return {
        "status": "processing",
        "job_id": job_id,
        "message": "Audio received. Processing started.",
    }


async def _process_audio_background(
    use_case: ProcessAudioUseCase,
    job_id: str,
    audio_path: str,
    nombre: str,
    modo: str,
    email: str,
):
    """Background task for audio processing."""
    try:
        result = use_case.execute(
            audio_path=audio_path,
            mode=modo,
            email=email,
            job_id=job_id,
        )
        logger.info(f"[BACKGROUND] Job {job_id} completed: status={result['status']}")
    except Exception as e:
        logger.error(f"[BACKGROUND] Job {job_id} failed: {e}", exc_info=True)


@router.post("/upload-chunk")
async def upload_chunk(
    request: Request,
    chunk: UploadFile = File(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    uploadId: str = Form(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
    extension: str = Form(...),
):
    """Receive a chunk of uploaded audio file."""
    require_auth(request)

    if modo not in VALID_MODES:
        logger.error(f"[CHUNK UPLOAD] Invalid mode: {modo}")
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Create upload directory
    uploads_temp_dir = Path(os.getenv("UPLOADS_TEMP_DIR", "/tmp/audios_chunks"))
    upload_dir = uploads_temp_dir / uploadId
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata on first chunk
    if chunkIndex == 0:
        metadata_path = upload_dir / "metadata.txt"
        metadata_path.write_text(extension)
    logger.info(f"[CHUNK UPLOAD] Started - uploadId: {uploadId}")
    logger.info(f"  nombre: {nombre}, total: {totalChunks}, ext: .{extension}")

    # Save chunk
    chunk_path = upload_dir / f"chunk_{chunkIndex:06d}"
    with chunk_path.open("wb") as f:
        shutil.copyfileobj(chunk.file, f)

    chunk_size = chunk_path.stat().st_size
    logger.info(f"[CHUNK UPLOAD] Chunk {chunkIndex + 1}/{totalChunks} - size: {chunk_size/1024/1024:.2f}MB")

    return {
        "status": "chunk_received",
        "chunkIndex": chunkIndex,
        "uploadId": uploadId,
    }


@router.post("/upload-complete")
async def upload_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    uploadId: str = Form(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
):
    """Assemble chunks and start processing."""
    require_auth(request)

    if modo not in VALID_MODES:
        logger.error(f"[UPLOAD COMPLETE] Invalid mode: {modo}")
        raise HTTPException(status_code=400, detail="Invalid mode")

    uploads_temp_dir = Path(os.getenv("UPLOADS_TEMP_DIR", "/tmp/audios_chunks"))
    upload_dir = uploads_temp_dir / uploadId

    if not upload_dir.exists():
        logger.error(f"[UPLOAD COMPLETE] Upload not found: {uploadId}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Find chunks
    chunk_files = sorted(
        upload_dir.glob("chunk_*"),
        key=lambda p: int(p.stem.split("_")[1]),
    )

    if not chunk_files:
        logger.error(f"[UPLOAD COMPLETE] No chunks found: {uploadId}")
        raise HTTPException(status_code=400, detail="No chunks found")

    # Get extension
    metadata_path = upload_dir / "metadata.txt"
    extension = metadata_path.read_text().strip() if metadata_path.exists() else "webm"

    logger.info(f"[UPLOAD COMPLETE] Assembling {len(chunk_files)} chunks: uploadId={uploadId}, nombre={nombre}")

    # Assemble file
    audios_dir = Path("audios")
    audios_dir.mkdir(exist_ok=True)

    safe_name = nombre.lower()
    audio_path = audios_dir / f"{safe_name}.{extension}"

    # Calculate total size
    total_chunks_size = sum(f.stat().st_size for f in chunk_files)
    logger.info(f"[UPLOAD COMPLETE] Total chunks size: {total_chunks_size/1024/1024:.2f}MB")

    # Assemble
    with audio_path.open("wb") as outfile:
        for idx, chunk_file in enumerate(chunk_files):
            with chunk_file.open("rb") as infile:
                shutil.copyfileobj(infile, outfile)
            if (idx + 1) % 10 == 0 or idx == len(chunk_files) - 1:
                logger.info(f"[UPLOAD COMPLETE] Progress: {idx + 1}/{len(chunk_files)} chunks")

    final_size = audio_path.stat().st_size
    logger.info(f"[UPLOAD COMPLETE] Assembled: {audio_path}, size: {final_size/1024/1024:.2f}MB")

    # Clean up chunks
    try:
        shutil.rmtree(upload_dir)
        logger.info(f"[UPLOAD COMPLETE] Cleaned up: {upload_dir}")
    except Exception as e:
        logger.warning(f"[UPLOAD COMPLETE] Failed to clean up {upload_dir}: {e}")

    # Create job
    job_id = str(uuid.uuid4())

    # Get use case
    use_case = get_process_audio_use_case(background_tasks, save_files=True)

    # Launch background task
    background_tasks.add_task(
        _process_audio_background,
        use_case=use_case,
        job_id=job_id,
        audio_path=str(audio_path),
        nombre=safe_name,
        modo=modo,
        email=email,
    )

    logger.info(f"[API ROUTE] Job {job_id} started for: {nombre}")

    return {
        "status": "processing",
        "job_id": job_id,
        "message": "Audio received. Processing started.",
    }


@router.post("/upload-cancel")
async def upload_cancel(
    request: Request,
    uploadId: str = Form(...),
):
    """Cancel an upload and clean up chunks."""
    require_auth(request)

    uploads_temp_dir = Path(os.getenv("UPLOADS_TEMP_DIR", "/tmp/audios_chunks"))
    upload_dir = uploads_temp_dir / uploadId

    if not upload_dir.exists():
        logger.warning(f"[UPLOAD CANCEL] Not found: {uploadId}")
        raise HTTPException(status_code=404, detail="Upload not found")

    try:
        shutil.rmtree(upload_dir)
        logger.info(f"[UPLOAD CANCEL] Cleaned up: {uploadId}")
        return {
            "status": "cancelled",
            "uploadId": uploadId,
            "message": "Upload cancelled and chunks cleaned up.",
        }
    except Exception as e:
        logger.error(f"[UPLOAD CANCEL] Failed to clean up {upload_dir}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clean up chunks")


@router.get("/status/{job_id}")
def get_status(job_id: str):
    """Get job status."""
    repo = get_job_status_repository()
    use_case = GetJobStatusUseCase(repo)
    return use_case.execute(job_id)


@router.post("/chat/stream")
async def chat_stream(request: Request, payload: dict):
    """Stream chat response."""
    require_auth(request)

    message = payload.get("message", "")
    mode = payload.get("mode", "default")

    use_case = StreamChatResponseUseCase(get_ai_summarizer())

    async def chat_stream_gen():
        try:
            logger.info(f"[CHAT STREAM] Started: mode={mode}, message={message[:50]}...")
            for chunk in use_case.execute(message, mode):
                if chunk:
                    yield chunk
            logger.info("[CHAT STREAM] Completed")
        except Exception as e:
            logger.error(f"[CHAT STREAM] Error: {e}")
            yield f"\n[Server error: {str(e)}]"

    return StreamingResponse(chat_stream_gen(), media_type="text/plain")


@router.get("/check-name")
def check_name(name: str):
    """Check if a recording with given name exists."""
    for ext in [".webm", ".mp3", ".wav", ".m4a", ".mp4"]:
        path = Path(RECORDINGS_DIR) / f"{name}{ext}"
        if path.exists():
            return {"exists": True, "extension": ext}
    return {"exists": False}


@router.post("/process-existing")
async def process_existing(
    request: Request,
    nombre: str = Form(...),
    modo: str = Form(...),
    transcription: str = Form(None),
):
    """Process existing text (with optional transcription)."""
    require_auth(request)

    text = transcription

    # If no transcription provided, check file
    if not text:
        transcript_path = Path("transcripts") / f"{nombre}.txt"
        if transcript_path.exists():
            text = transcript_path.read_text(encoding="utf-8")
            logger.info(f"[PROCESS EXISTING] Loaded transcription from file: {nombre}")
        else:
            raise HTTPException(status_code=404, detail="Transcription not found")

    if modo not in VALID_MODES:
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Process
    use_case = ProcessTextUseCase(get_transcription_service(save_files=True))
    result = use_case.execute(
        text=text,
        mode=modo,
        filename=nombre,
        save_files=True,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))

    return result


@router.get("/transcripciones/{filename}")
def get_transcription(filename: str):
    """Get a transcription file."""
    path = Path("transcripts") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="text/plain")


@router.get("/resultados/{filename}")
def get_result(filename: str):
    """Get a result markdown file."""
    path = Path("outputs") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="text/markdown")
