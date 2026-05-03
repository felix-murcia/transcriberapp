"""
Primary adapters - HTTP/API layer (FastAPI).
Converts external HTTP requests into use case invocations.
"""

import os
import uuid
import json
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

from transcriber_app.infrastructure.logging.logging_config import setup_logging
from transcriber_app.infrastructure.queue import FastAPIBackgroundTasksAdapter

logger = setup_logging("transcribeapp")

router = APIRouter(prefix="", tags=["api"])


# ============================================================================
# Dependency Injection - Imported from composition root
# ============================================================================

from transcriber_app.di import (
    get_audio_file_reader,
    get_audio_validator,
    get_audio_transcriber,
    get_ai_summarizer,
    get_output_formatter,
    get_job_status_repository,
    get_transcription_service,
    get_process_audio_use_case,
    get_process_text_use_case,
    get_get_job_status_use_case,
    get_stream_chat_response_use_case,
)
from transcriber_app.application.use_cases import ProcessAudioUseCase


def get_job_queue(background_tasks: BackgroundTasks) -> JobQueuePort:
    adapter = FastAPIBackgroundTasksAdapter()
    adapter.set_background_tasks(background_tasks)
    return adapter


def get_session_manager() -> Optional[SessionManagerPort]:
    # Session manager is optional - some endpoints may not require auth
    return None


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
    use_case = get_process_audio_use_case(save_files=True)

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


async def process_single_chunk_job(
    job_id: str,
    upload_id: str,
    chunk_index: int,
    nombre: str,
    modo: str,
    email: str,
):
    """Background task for processing a single chunk and updating accumulated job."""
    try:
        logger.info(f"[SINGLE_CHUNK_PROCESSOR] Processing chunk {chunk_index} for job {job_id}")

        chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
        upload_dir = chunks_base_dir / upload_id
        metadata_path = upload_dir / "metadata.json"

        # Load metadata and chunk info
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        chunk_info = next((c for c in metadata["chunks"] if c["index"] == chunk_index), None)
        if not chunk_info:
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} not found in metadata")
            return

        chunk_path = Path(chunk_info["path"])
        if not chunk_path.exists():
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Chunk file not found: {chunk_path}")
            return

        # Load current job
        from transcriber_app.di import get_job_repo
        job_repo = get_job_repo()
        job = job_repo.get(job_id)
        if not job:
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Job {job_id} not found")
            return

        try:
            # Convert chunk to MP3
            from transcriber_app.infrastructure.validation.ffmpeg_conversion_adapter import FfmpegConversionAdapter
            ffmpeg_adapter = FfmpegConversionAdapter()

            mp3_data = ffmpeg_adapter.convert_audio(str(chunk_path), fmt="mp3")
            logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} converted to MP3: {len(mp3_data)} bytes")

            # Save temp MP3 file for transcriber
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(mp3_data)
                temp_mp3_path = temp_file.name

            try:
                # Transcribe with Groq
                from transcriber_app.infrastructure.ai.groq.transcriber import GroqTranscriber
                transcriber = GroqTranscriber(skip_validation=True)
                transcription_text, metadata_chunk = transcriber.transcribe(temp_mp3_path)

                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} transcribed: {len(transcription_text)} chars")

                # Update job with partial transcription
                job.partial_transcriptions[chunk_index] = transcription_text
                job.processed_chunks += 1

                # Mark chunk as processed in metadata
                chunk_info["status"] = "processed"
                chunk_info["transcription_length"] = len(transcription_text)

                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                # Clean up chunk file after processing
                try:
                    os.unlink(chunk_path)
                    logger.info(f"[SINGLE_CHUNK_PROCESSOR] Cleaned up chunk file: {chunk_path}")
                except Exception as e:
                    logger.warning(f"[SINGLE_CHUNK_PROCESSOR] Failed to clean up {chunk_path}: {e}")

                job_repo.save(job)
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Updated job {job_id}: {job.processed_chunks}/{job.total_chunks} chunks processed")

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_mp3_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Failed to process chunk {chunk_index}: {e}")
            chunk_info["status"] = "failed"
            chunk_info["error"] = str(e)

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            # Still increment processed chunks even on failure
            job.processed_chunks += 1
            job_repo.save(job)

    except Exception as e:
        logger.error(f"[SINGLE_CHUNK_PROCESSOR] Error in single chunk processor: {e}", exc_info=True)


async def process_chunks_job(
    job_id: str,
    upload_id: str,
    nombre: str,
    modo: str,
    email: str,
):
    """Background task for processing individual chunks."""
    try:
        logger.info(f"[CHUNK_PROCESSOR] Starting job {job_id} for upload {upload_id}")

        chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
        upload_dir = chunks_base_dir / upload_id
        metadata_path = upload_dir / "metadata.json"

        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        total_chunks = metadata["total_chunks"]
        chunks = sorted(metadata["chunks"], key=lambda c: c["index"])

        logger.info(f"[CHUNK_PROCESSOR] Processing {total_chunks} chunks for {nombre}")

        # Initialize services (similar to use case)
        from transcriber_app.di import get_transcription_service
        transcription_service = get_transcription_service()

        # Initialize job in repository
        from transcriber_app.di import get_job_repo
        job_repo = get_job_repo()

        # Create TranscriptionJob
        from transcriber_app.domain.entities import TranscriptionJob
        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=nombre,
            audio_path="",  # Not used in this flow
            mode=modo,
            email=email,
        )
        job.status = "processing"
        job_repo.save(job)

        combined_transcription = ""
        all_transcriptions = []

        # Process each chunk
        for i, chunk_info in enumerate(chunks):
            chunk_index = chunk_info["index"]
            chunk_path = Path(chunk_info["path"])

            logger.info(f"[CHUNK_PROCESSOR] Processing chunk {chunk_index + 1}/{total_chunks}: {chunk_path}")

            try:
                # Convert chunk to MP3
                from transcriber_app.infrastructure.validation.ffmpeg_conversion_adapter import FfmpegConversionAdapter
                ffmpeg_adapter = FfmpegConversionAdapter()

                # Convert chunk file to MP3
                mp3_data = ffmpeg_adapter.convert_audio(str(chunk_path), fmt="mp3")
                logger.info(f"[CHUNK_PROCESSOR] Chunk {chunk_index} converted to MP3: {len(mp3_data)} bytes")

                # Save temp MP3 file for transcriber
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_file.write(mp3_data)
                    temp_mp3_path = temp_file.name

                try:
                    # Transcribe with Groq (skip validation since we already converted to MP3)
                    from transcriber_app.infrastructure.ai.groq.transcriber import GroqTranscriber
                    transcriber = GroqTranscriber(skip_validation=True)
                    transcription_text, metadata_chunk = transcriber.transcribe(temp_mp3_path)

                    logger.info(f"[CHUNK_PROCESSOR] Chunk {chunk_index} transcribed: {len(transcription_text)} chars")

                    # Add to combined result
                    all_transcriptions.append({
                        "chunk_index": chunk_index,
                        "text": transcription_text,
                        "metadata": metadata_chunk
                    })

                    combined_transcription += transcription_text + " "

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_mp3_path)
                    except:
                        pass

                # Update chunk status
                chunk_info["status"] = "processed"

            except Exception as e:
                logger.error(f"[CHUNK_PROCESSOR] Failed to process chunk {chunk_index}: {e}")
                chunk_info["status"] = "failed"
                chunk_info["error"] = str(e)
                # Continue with other chunks

        # Combine transcriptions
        final_transcription = combined_transcription.strip()

        logger.info(f"[CHUNK_PROCESSOR] Combined transcription: {len(final_transcription)} chars")

        # Summarize using AI
        from transcriber_app.di import get_summarizer
        summarizer = get_summarizer()
        summary_output = summarizer.summarize(final_transcription, modo)

        # Save results
        from transcriber_app.di import get_formatter
        formatter = get_formatter()
        output_path = formatter.save_output(job_id, nombre, summary_output, modo)
        formatter.save_transcription(job_id, nombre, final_transcription)
        formatter.save_metrics(job_id, nombre, summary_output, modo)

        # TODO: Send email notification if email provided
        # Email sending logic to be implemented based on existing patterns

        # Update job status
        job.status = "completed"
        job.transcription_text = final_transcription
        job.summary_output = summary_output
        job_repo.save(job)

        # Clean up chunks if configured
        if os.getenv("KEEP_CHUNKS_AFTER_PROCESSING", "false").lower() != "true":
            try:
                shutil.rmtree(upload_dir)
                logger.info(f"[CHUNK_PROCESSOR] Cleaned up chunks: {upload_dir}")
            except Exception as e:
                logger.warning(f"[CHUNK_PROCESSOR] Failed to clean up {upload_dir}: {e}")

        logger.info(f"[CHUNK_PROCESSOR] Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"[CHUNK_PROCESSOR] Job {job_id} failed: {e}", exc_info=True)

        # Update job status on failure
        try:
            job_repo = get_job_repo()
            job = job_repo.get(job_id)
            if job:
                job.status = "error"
                job.error_message = str(e)
                job_repo.save(job)
        except:
            pass


async def finalize_chunked_transcription(
    job_id: str,
    upload_id: str,
    nombre: str,
    modo: str,
    email: str,
):
    """Combine partial transcriptions and generate final summary."""
    try:
        logger.info(f"[FINALIZE_TRANSCRIPTION] Starting finalization for job {job_id}")

        # Load job
        from transcriber_app.di import get_job_repo
        job_repo = get_job_repo()
        job = job_repo.get(job_id)

        if not job:
            logger.error(f"[FINALIZE_TRANSCRIPTION] Job {job_id} not found")
            return

        # Wait for all chunks to be processed
        max_wait_time = 300  # 5 minutes max wait
        wait_time = 0
        import asyncio

        while wait_time < max_wait_time:
            job = job_repo.get(job_id)
            if job.processed_chunks >= job.total_chunks:
                logger.info(f"[FINALIZE_TRANSCRIPTION] All {job.total_chunks} chunks processed")
                break

            logger.info(f"[FINALIZE_TRANSCRIPTION] Waiting for chunks: {job.processed_chunks}/{job.total_chunks} processed")
            await asyncio.sleep(5)
            wait_time += 5

        if job.processed_chunks < job.total_chunks:
            logger.warning(f"[FINALIZE_TRANSCRIPTION] Timeout waiting for chunks: {job.processed_chunks}/{job.total_chunks}")
            # Continue anyway with available transcriptions

        # Combine transcriptions in order
        combined_transcription = ""
        for i in range(job.total_chunks):
            if i in job.partial_transcriptions:
                transcription = job.partial_transcriptions[i]
                combined_transcription += transcription + " "
                logger.info(f"[FINALIZE_TRANSCRIPTION] Added chunk {i}: {len(transcription)} chars")
            else:
                logger.warning(f"[FINALIZE_TRANSCRIPTION] Missing transcription for chunk {i}")
                combined_transcription += f"[CHUNK {i} MISSING] "

        job.transcription_text = combined_transcription.strip()
        logger.info(f"[FINALIZE_TRANSCRIPTION] Combined transcription: {len(job.transcription_text)} chars")

        # Generate summary
        from transcriber_app.di import get_summarizer
        summarizer = get_summarizer()
        summary_output = summarizer.summarize(job.transcription_text, modo)
        job.summary_output = summary_output

        # Save results
        from transcriber_app.di import get_formatter
        formatter = get_formatter()
        output_path = formatter.save_output(job_id, nombre, summary_output, modo)
        formatter.save_transcription(job_id, nombre, job.transcription_text)
        formatter.save_metrics(job_id, nombre, summary_output, modo)

        # Update job status
        from datetime import datetime
        job.status = "completed"
        job.completed_at = datetime.now()
        job_repo.save(job)

        # Clean up upload directory
        chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
        upload_dir = chunks_base_dir / upload_id

        if os.getenv("KEEP_CHUNKS_AFTER_PROCESSING", "false").lower() != "true":
            try:
                shutil.rmtree(upload_dir)
                logger.info(f"[FINALIZE_TRANSCRIPTION] Cleaned up upload directory: {upload_dir}")
            except Exception as e:
                logger.warning(f"[FINALIZE_TRANSCRIPTION] Failed to clean up {upload_dir}: {e}")

        logger.info(f"[FINALIZE_TRANSCRIPTION] Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"[FINALIZE_TRANSCRIPTION] Failed to finalize job {job_id}: {e}", exc_info=True)

        # Update job status on failure
        try:
            job_repo = get_job_repo()
            job = job_repo.get(job_id)
            if job:
                job.status = "error"
                job.error_message = str(e)
                job_repo.save(job)
        except:
            pass


@router.post("/upload-chunk")
async def upload_chunk(
    request: Request,
    background_tasks: BackgroundTasks,
    chunk: UploadFile = File(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    uploadId: str = Form(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
    extension: str = Form(...),
):
    """Receive a chunk of uploaded audio file and start processing immediately."""
    require_auth(request)

    if modo not in VALID_MODES:
        logger.error(f"[CHUNK UPLOAD] Invalid mode: {modo}")
        raise HTTPException(status_code=400, detail="Invalid mode")

    # Create chunks directory
    chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
    upload_dir = chunks_base_dir / uploadId
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Initialize metadata and job on first chunk
    metadata_path = upload_dir / "metadata.json"
    job_id = None

    if chunkIndex == 0:
        import json
        from datetime import datetime

        # Create metadata
        metadata = {
            "upload_id": uploadId,
            "original_filename": nombre,
            "total_chunks": totalChunks,
            "created_at": datetime.now().isoformat(),
            "job_id": None,  # Will be set below
            "chunks": []
        }

        # Create job for this upload
        job_id = str(uuid.uuid4())
        metadata["job_id"] = job_id

        # Initialize job in repository
        from transcriber_app.di import get_job_repo
        from transcriber_app.domain.entities import TranscriptionJob
        job_repo = get_job_repo()

        job = TranscriptionJob(
            job_id=job_id,
            audio_filename=nombre,
            audio_path="",  # Not used in chunked flow
            mode=modo,
            email=email,
            status="processing",
            total_chunks=totalChunks,
            processed_chunks=0,
        )
        job_repo.save(job)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"[CHUNK UPLOAD] Created job {job_id} for upload {uploadId}")

    # Load job_id from metadata
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    job_id = metadata["job_id"]

    logger.info(f"[CHUNK UPLOAD] Processing - uploadId: {uploadId}, jobId: {job_id}")
    logger.info(f"  nombre: {nombre}, chunk: {chunkIndex + 1}/{totalChunks}, ext: .{extension}")

    # Save chunk with extension
    chunk_filename = f"chunk_{chunkIndex:06d}.{extension}"
    chunk_path = upload_dir / chunk_filename
    with chunk_path.open("wb") as f:
        shutil.copyfileobj(chunk.file, f)

    chunk_size = chunk_path.stat().st_size
    logger.info(f"[CHUNK UPLOAD] Chunk {chunkIndex + 1}/{totalChunks} saved - size: {chunk_size/1024/1024:.2f}MB")

    # Update metadata with chunk info
    chunk_info = {
        "index": chunkIndex,
        "filename": chunk_filename,
        "path": str(chunk_path),
        "size": chunk_size,
        "status": "received"
    }
    metadata["chunks"].append(chunk_info)

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Start processing this chunk immediately
    background_tasks.add_task(
        process_single_chunk_job,
        job_id=job_id,
        upload_id=uploadId,
        chunk_index=chunkIndex,
        nombre=nombre,
        modo=modo,
        email=email,
    )

    return {
        "status": "chunk_received_and_processing",
        "chunkIndex": chunkIndex,
        "uploadId": uploadId,
        "job_id": job_id,
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
    """Finalize upload and combine transcriptions for summary."""
    require_auth(request)

    if modo not in VALID_MODES:
        logger.error(f"[UPLOAD COMPLETE] Invalid mode: {modo}")
        raise HTTPException(status_code=400, detail="Invalid mode")

    chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
    upload_dir = chunks_base_dir / uploadId

    if not upload_dir.exists():
        logger.error(f"[UPLOAD COMPLETE] Upload not found: {uploadId}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Load metadata
    metadata_path = upload_dir / "metadata.json"
    if not metadata_path.exists():
        logger.error(f"[UPLOAD COMPLETE] Metadata not found: {metadata_path}")
        raise HTTPException(status_code=400, detail="Metadata not found")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    job_id = metadata.get("job_id")
    if not job_id:
        logger.error(f"[UPLOAD COMPLETE] No job_id found in metadata")
        raise HTTPException(status_code=400, detail="Job not found")

    # Validate all chunks are present
    expected_chunks = metadata["total_chunks"]
    received_chunks = len(metadata["chunks"])

    if received_chunks != expected_chunks:
        logger.error(f"[UPLOAD COMPLETE] Missing chunks: expected {expected_chunks}, received {received_chunks}")
        raise HTTPException(status_code=400, detail=f"Missing chunks: expected {expected_chunks}, received {received_chunks}")

    logger.info(f"[UPLOAD COMPLETE] All {received_chunks} chunks received for uploadId={uploadId}, job={job_id}")

    # Mark upload as complete and start finalization
    background_tasks.add_task(
        finalize_chunked_transcription,
        job_id=job_id,
        upload_id=uploadId,
        nombre=nombre,
        modo=modo,
        email=email,
    )

    return {
        "status": "finalizing",
        "job_id": job_id,
        "message": f"All {received_chunks} chunks received. Finalizing transcription...",
    }


@router.post("/process-chunks")
async def process_chunks(
    request: Request,
    background_tasks: BackgroundTasks,
    upload_id: str = Form(...),
    job_id: str = Form(...),
    email: str = Form(...),
):
    """Start processing saved chunks."""
    require_auth(request)

    # Validate upload exists
    chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
    upload_dir = chunks_base_dir / upload_id

    if not upload_dir.exists():
        logger.error(f"[PROCESS CHUNKS] Upload not found: {upload_id}")
        raise HTTPException(status_code=404, detail="Upload not found")

    # Load metadata
    metadata_path = upload_dir / "metadata.json"
    if not metadata_path.exists():
        logger.error(f"[PROCESS CHUNKS] Metadata not found: {metadata_path}")
        raise HTTPException(status_code=400, detail="Metadata not found")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    total_chunks = metadata["total_chunks"]

    # Launch background processing
    background_tasks.add_task(
        process_chunks_job,
        job_id=job_id,
        upload_id=upload_id,
        nombre=metadata["original_filename"],
        modo="default",  # Could be passed as parameter
        email=email,
    )

    logger.info(f"[API ROUTE] Chunk processing job {job_id} started for upload: {upload_id}")

    return {
        "job_id": job_id,
        "status": "processing",
        "total_chunks": total_chunks
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
    use_case = get_get_job_status_use_case()
    return use_case.execute(job_id)


@router.post("/chat/stream")
async def chat_stream(request: Request, payload: dict):
    """Stream chat response."""
    require_auth(request)

    message = payload.get("message", "")
    mode = payload.get("mode", "default")

    use_case = get_stream_chat_response_use_case()

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
    use_case = get_process_text_use_case(save_files=True)
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
