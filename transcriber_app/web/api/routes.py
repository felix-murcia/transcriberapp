# transcriber_app/web/api/routes.py
import os
import uuid
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from transcriber_app.domain.entities import TranscriptionJob
from transcriber_app.infrastructure.ai.gemini.ai_manager import AIManager
from transcriber_app.runner.orchestrator import Orchestrator
from transcriber_app.infrastructure.output import LocalOutputFormatter as OutputFormatter
from transcriber_app.infrastructure.audio import LocalAudioFileReader as AudioReceiver
from transcriber_app.infrastructure.ai.groq.transcriber import GroqTranscriber
from transcriber_app.web.api.background import process_audio_job, JOB_STATUS
from transcriber_app.infrastructure.logging.logging_config import setup_logging

logger = setup_logging("transcribeapp")

RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "/tmp/recordings")
UPLOADS_TEMP_DIR = os.getenv("UPLOADS_TEMP_DIR", "/tmp/audios_chunks")
Path(UPLOADS_TEMP_DIR).mkdir(exist_ok=True)

router = APIRouter(prefix="", tags=["auth"])


def check_auth(request: Request):
    return request.cookies.get("logged_in") == "true"


async def process_single_chunk_sync(
    job_id: str,
    upload_id: str,
    chunk_index: int,
    chunk_path: Path,
    metadata_path: Path,
    nombre: str,
    modo: str,
    email: str,
):
    """Process a single chunk synchronously (not in background)."""
    try:
        logger.info(f"[SINGLE_CHUNK_PROCESSOR] ===== STARTING CHUNK {chunk_index} PROCESSING =====")
        logger.info(f"[SINGLE_CHUNK_PROCESSOR] Processing chunk {chunk_index} for job {job_id}")
        logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk path: {chunk_path}")
        logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk exists: {chunk_path.exists()}")

        # Load current job
        from transcriber_app.di import get_job_status_repository
        job_repo = get_job_status_repository()
        job = job_repo.get_status(job_id)
        if not job:
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Job {job_id} not found - available jobs: {list(job_repo._statuses.keys()) if hasattr(job_repo, '_statuses') else 'N/A'}")
            return

        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        chunk_info = next((c for c in metadata["chunks"] if c["index"] == chunk_index), None)
        if not chunk_info:
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} not found in metadata")
            return

        if not chunk_path.exists():
            logger.error(f"[SINGLE_CHUNK_PROCESSOR] Chunk file not found: {chunk_path}")
            return

        logger.info(f"[SINGLE_CHUNK_PROCESSOR] Starting MP3 conversion for chunk {chunk_index}")
        try:
            # Convert chunk to MP3
            from transcriber_app.infrastructure.validation.ffmpeg_conversion_adapter import FfmpegConversionAdapter
            ffmpeg_adapter = FfmpegConversionAdapter()
            logger.info(f"[SINGLE_CHUNK_PROCESSOR] FFmpeg adapter created for chunk {chunk_index}")

            mp3_data = ffmpeg_adapter.convert_audio(str(chunk_path), fmt="mp3")
            logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} converted to MP3: {len(mp3_data)} bytes")
            logger.info(f"[SINGLE_CHUNK_PROCESSOR] Starting transcription preparation for chunk {chunk_index}")

            # Save temp MP3 file for transcriber
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(mp3_data)
                temp_mp3_path = temp_file.name

            try:
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Starting Groq transcription for chunk {chunk_index}")
                # Transcribe with Groq
                from transcriber_app.infrastructure.ai.groq.transcriber import GroqTranscriber
                transcriber = GroqTranscriber(skip_validation=True)
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] GroqTranscriber created for chunk {chunk_index}")

                transcription_text, metadata_chunk = transcriber.transcribe(temp_mp3_path)
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Chunk {chunk_index} transcribed successfully: {len(transcription_text)} chars")
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Finishing processing for chunk {chunk_index}")

                # Update job with partial transcription
                job["partial_transcriptions"][chunk_index] = transcription_text
                job["processed_chunks"] += 1

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

                job_repo.set_status(job_id, job)
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Updated job {job_id}: {job['processed_chunks']}/{job['total_chunks']} chunks processed")

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
            job["processed_chunks"] += 1
            job_repo.set_status(job_id, job)

    except Exception as e:
        logger.error(f"[SINGLE_CHUNK_PROCESSOR] Error in single chunk processor: {e}", exc_info=True)


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
        from transcriber_app.di import get_job_status_repository
        job_repo = get_job_status_repository()
        job = job_repo.get_status(job_id)
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
                job["partial_transcriptions"][chunk_index] = transcription_text
                job["processed_chunks"] += 1

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

                job_repo.set_status(job_id, job)
                logger.info(f"[SINGLE_CHUNK_PROCESSOR] Updated job {job_id}: {job['processed_chunks']}/{job['total_chunks']} chunks processed")

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
            job["processed_chunks"] += 1
            job_repo.set_status(job_id, job)

    except Exception as e:
        logger.error(f"[SINGLE_CHUNK_PROCESSOR] Error in single chunk processor: {e}", exc_info=True)
        # Update job status on error
        try:
            job_repo.set_status(job_id, job)
        except:
            pass


async def finalize_chunked_transcription_sync(
    job_id: str,
    upload_id: str,
    nombre: str,
    modo: str,
    email: str,
):
    """Combine partial transcriptions and generate final summary synchronously."""
    try:
        logger.info(f"[FINALIZE_TRANSCRIPTION] Starting finalization for job {job_id}")

        # Load job
        from transcriber_app.di import get_job_status_repository
        job_repo = get_job_status_repository()
        job = job_repo.get_status(job_id)

        if not job:
            logger.error(f"[FINALIZE_TRANSCRIPTION] Job {job_id} not found")
            return

        # Combine transcriptions in order
        combined_transcription = ""
        for i in range(job["total_chunks"]):
            if i in job["partial_transcriptions"]:
                transcription = job["partial_transcriptions"][i]
                combined_transcription += transcription + " "
                logger.info(f"[FINALIZE_TRANSCRIPTION] Added chunk {i}: {len(transcription)} chars")
            else:
                logger.warning(f"[FINALIZE_TRANSCRIPTION] Missing transcription for chunk {i}")
                combined_transcription += f"[CHUNK {i} MISSING] "

        job["transcription_text"] = combined_transcription.strip()
        logger.info(f"[FINALIZE_TRANSCRIPTION] Combined transcription: {len(job['transcription_text'])} chars")

        # Generate summary
        from transcriber_app.di import get_ai_summarizer
        summarizer = get_ai_summarizer()
        summary_output = summarizer.summarize(job["transcription_text"], modo)
        job["summary_output"] = summary_output

        # Save results
        from transcriber_app.di import get_output_formatter
        formatter = get_output_formatter()
        output_path = formatter.save_output(job_id, nombre, summary_output, modo)
        formatter.save_transcription(job_id, nombre, job["transcription_text"])
        formatter.save_metrics(job_id, nombre, summary_output, modo)

        # Update job status
        job["status"] = "completed"
        job["completed_at"] = datetime.now().isoformat()
        job_repo.set_status(job_id, job)

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
            from transcriber_app.di import get_job_status_repository
            job_repo = get_job_status_repository()
            job = job_repo.get_status(job_id)
            if job:
                job["status"] = "error"
                job["error_message"] = str(e)
                job_repo.set_status(job_id, job)
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
        from transcriber_app.di import get_job_status_repository
        job_repo = get_job_status_repository()
        job = job_repo.get_status(job_id)

        if not job:
            logger.error(f"[FINALIZE_TRANSCRIPTION] Job {job_id} not found")
            return

        # Wait for all chunks to be processed
        max_wait_time = 300  # 5 minutes max wait
        wait_time = 0

        while wait_time < max_wait_time:
            job = job_repo.get_status(job_id)
            if job["processed_chunks"] >= job["total_chunks"]:
                logger.info(f"[FINALIZE_TRANSCRIPTION] All {job['total_chunks']} chunks processed")
                break

            logger.info(f"[FINALIZE_TRANSCRIPTION] Waiting for chunks: {job['processed_chunks']}/{job['total_chunks']} processed")
            await asyncio.sleep(5)
            wait_time += 5

        if job["processed_chunks"] < job["total_chunks"]:
            logger.warning(f"[FINALIZE_TRANSCRIPTION] Timeout waiting for chunks: {job['processed_chunks']}/{job['total_chunks']}")
            # Continue anyway with available transcriptions

        # Combine transcriptions in order
        combined_transcription = ""
        for i in range(job["total_chunks"]):
            if i in job["partial_transcriptions"]:
                transcription = job["partial_transcriptions"][i]
                combined_transcription += transcription + " "
                logger.info(f"[FINALIZE_TRANSCRIPTION] Added chunk {i}: {len(transcription)} chars")
            else:
                logger.warning(f"[FINALIZE_TRANSCRIPTION] Missing transcription for chunk {i}")
                combined_transcription += f"[CHUNK {i} MISSING] "

        job["transcription_text"] = combined_transcription.strip()
        logger.info(f"[FINALIZE_TRANSCRIPTION] Combined transcription: {len(job['transcription_text'])} chars")

        # Generate summary
        from transcriber_app.di import get_ai_summarizer
        summarizer = get_ai_summarizer()
        summary_output = summarizer.summarize(job["transcription_text"], modo)
        job["summary_output"] = summary_output

        # Save results
        from transcriber_app.di import get_output_formatter
        formatter = get_output_formatter()
        output_path = formatter.save_output(job_id, nombre, summary_output, modo)
        formatter.save_transcription(job_id, nombre, job["transcription_text"])
        formatter.save_metrics(job_id, nombre, summary_output, modo)

        # Update job status
        job["status"] = "completed"
        job["completed_at"] = datetime.now().isoformat()
        job_repo.set_status(job_id, job)

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
            from transcriber_app.di import get_job_status_repository
            job_repo = get_job_status_repository()
            job = job_repo.get_status(job_id)
            if job:
                job["status"] = "error"
                job["error_message"] = str(e)
                job_repo.set_status(job_id, job)
        except:
            pass


@router.post("/upload-audio")
async def upload_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    if modo not in ["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]:
        raise HTTPException(status_code=400, detail="Modo inválido")
    audios_dir = Path("audios")
    audios_dir.mkdir(exist_ok=True)
    safe_name = nombre.lower()
    if '.' in safe_name:
        safe_name = safe_name.rsplit('.', 1)[0]
    original_ext = Path(audio.filename).suffix.lower() if audio.filename else ".webm"
    if not original_ext:
        original_ext = ".webm"
    audio_path = audios_dir / f"{safe_name}{original_ext}"
    audio_content = await audio.read()
    audio_size = len(audio_content)
    logger.info("[UPLOAD AUDIO] Iniciando subida simple")
    logger.info(f"  Nombre: {nombre}")
    logger.info(f"  Tamaño: {audio_size/1024/1024:.2f} MB")
    logger.info(f"  Extensión: {original_ext}")
    logger.info(f"  Ruta destino: {audio_path}")
    with audio_path.open("wb") as f:
        f.write(audio_content)
    saved_size = audio_path.stat().st_size
    logger.info(f"[UPLOAD AUDIO] Archivo guardado correctamente - tamaño: {saved_size/1024/1024:.2f} MB")
    job_id = str(uuid.uuid4())
    background_tasks.add_task(process_audio_job, job_id=job_id, nombre=safe_name, modo=modo, email=email)
    logger.info(f"[API ROUTE] Job {job_id} iniciado para audio: {nombre} (subida simple)")
    return {"status": "processing", "job_id": job_id, "message": "Audio recibido. Procesamiento iniciado."}


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
    """Receive a chunk of uploaded audio file and process it immediately."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    if modo not in ["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]:
        raise HTTPException(status_code=400, detail="Modo inválido")

    # Create chunks directory
    chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
    upload_dir = chunks_base_dir / uploadId
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Initialize metadata and job on first chunk
    metadata_path = upload_dir / "metadata.json"
    job_id = None

    if chunkIndex == 0:
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
        from transcriber_app.di import get_job_status_repository
        job_repo = get_job_status_repository()

        job = {
            "job_id": job_id,
            "audio_filename": nombre,
            "audio_path": "",  # Not used in chunked flow
            "mode": modo,
            "email": email,
            "status": "processing",
            "total_chunks": totalChunks,
            "processed_chunks": 0,
            "partial_transcriptions": {}
        }
        job_repo.set_status(job_id, job)

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
    with open(chunk_path, "wb") as f:
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

    # Start processing chunk asynchronously to avoid timeouts
    background_tasks.add_task(
        process_single_chunk_sync,
        job_id=job_id,
        upload_id=uploadId,
        chunk_index=chunkIndex,
        chunk_path=chunk_path,
        metadata_path=metadata_path,
        nombre=nombre,
        modo=modo,
        email=email,
    )

    return {
        "status": "chunk_received_and_processing_started",
        "chunkIndex": chunkIndex,
        "uploadId": uploadId,
        "job_id": job_id,
        "message": f"Chunk {chunkIndex + 1} accepted, processing in background"
    }


@router.post("/upload-complete")
async def upload_complete(
    request: Request,
    uploadId: str = Form(...),
    nombre: str = Form(...),
    modo: str = Form(...),
    email: str = Form(...),
):
    """Finalize upload and combine transcriptions for summary."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    if modo not in ["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]:
        raise HTTPException(status_code=400, detail="Modo inválido")

    chunks_base_dir = Path(os.getenv("CHUNKS_BASE_DIR", "/app/audios/chunks"))
    upload_dir = chunks_base_dir / uploadId

    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="Upload no encontrado")

    # Load metadata
    metadata_path = upload_dir / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=400, detail="Metadata no encontrado")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    job_id = metadata.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="Job no encontrado")

    # Validate all chunks are present
    expected_chunks = metadata["total_chunks"]
    received_chunks = len(metadata["chunks"])

    if received_chunks != expected_chunks:
        raise HTTPException(status_code=400, detail=f"Faltan chunks: esperados {expected_chunks}, recibidos {received_chunks}")

    logger.info(f"[UPLOAD COMPLETE] Todos los {received_chunks} chunks recibidos para uploadId={uploadId}, job={job_id}")

    # Finalize synchronously
    await finalize_chunked_transcription_sync(
        job_id=job_id,
        upload_id=uploadId,
        nombre=nombre,
        modo=modo,
        email=email,
    )

    return {
        "status": "completed",
        "job_id": job_id,
        "message": f"Transcripción completada para {received_chunks} chunks.",
    }


@router.post("/upload-cancel")
async def upload_cancel(request: Request, uploadId: str = Form(...)):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    upload_dir = Path(UPLOADS_TEMP_DIR) / uploadId
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="Upload no encontrado")
    shutil.rmtree(upload_dir)
    logger.info(f"[UPLOAD CANCEL] Limpiado: {uploadId}")
    return {"status": "cancelled", "uploadId": uploadId, "message": "Upload cancelado."}


@router.get("/status/{job_id}")
def get_status(job_id: str):
    job_data = JOB_STATUS.get(job_id, "unknown")
    if isinstance(job_data, dict):
        return job_data
    return {"job_id": job_id, "status": job_data}


@router.post("/chat/stream")
async def chat_stream(request: Request, payload: dict):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    message = payload.get("message", "")
    mode = payload.get("mode", "default")
    agent = AIManager.get_agent(mode)

    async def chat_stream_gen():
        try:
            for chunk in agent.run(message, stream=True):
                if chunk:
                    yield chunk
        except Exception as e:
            yield f"\n[Error: {str(e)}]"
    return StreamingResponse(chat_stream_gen(), media_type="text/plain")


@router.get("/check-name")
def check_name(name: str):
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
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    text = transcription
    if not text:
        transcript_path = Path("transcripts") / f"{nombre}.txt"
        if transcript_path.exists():
            text = transcript_path.read_text(encoding="utf-8")
        else:
            raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    orchestrator = Orchestrator(AudioReceiver(), GroqTranscriber(), OutputFormatter(), save_files=False)
    summary_output = AIManager.summarize(text, modo)
    orchestrator.formatter.save_metrics(nombre, summary_output, modo)
    return {"status": "done", "mode": modo, "markdown": summary_output, "transcription": text}


@router.get("/transcripciones/{filename}")
def get_transcription(filename: str):
    path = Path("transcripts") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="text/plain")


@router.get("/resultados/{filename}")
def get_result(filename: str):
    path = Path("outputs") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="text/markdown")
