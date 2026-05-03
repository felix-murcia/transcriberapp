# transcriber_app/infrastructure/ai/groq/transcriber.py

import os
import logging
from typing import Tuple, Dict, Any, Optional

from transcriber_app.config import GROQ_API_KEY
from transcriber_app.domain.ports import AudioTranscriberPort
from transcriber_app.domain.exceptions import AudioValidationError
from .ffmpeg_adapter import FfmpegAdapter
from .audio_preparer import FfmpegAudioPreparer
from .groq_api_client import GroqApiClient

# Timeout configuration via environment variables
GROQ_TIMEOUT_FFMPEG_READY = int(os.getenv("GROQ_TIMEOUT_FFMPEG_READY", 10))
FFPROBE_TIMEOUT = int(os.getenv("FFPROBE_TIMEOUT", 10))
GROQ_TIMEOUT_API = int(os.getenv("GROQ_TIMEOUT_API", 300))

logger = logging.getLogger("transcribeapp")


class GroqTranscriber(AudioTranscriberPort):
    """
    Adaptador principal para transcripción usando Groq.
    Coordina preparación de audio y comunicación con Groq API.
    Respects Single Responsibility: coordination only.
    """

    def __init__(self, skip_validation: bool = False):
        """
        Inicializa el transcriber de Groq con sus dependencias.

        Args:
            skip_validation: Si es True, omite la validación del audio
        """
        self.skip_validation = skip_validation

        # Inyección de dependencias - adaptadores
        from transcriber_app.infrastructure.validation import FfmpegConversionAdapter
        self.ffmpeg_adapter = FfmpegAdapter()
        self.conversion_adapter = FfmpegConversionAdapter()
        self.audio_preparer = FfmpegAudioPreparer(self.ffmpeg_adapter._validator, self.conversion_adapter)
        self.groq_client = GroqApiClient()

    def transcribe(self, audio_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe un archivo de audio usando Groq Whisper.
        Coordina preparación de audio y comunicación con Groq API.

        Secuencia lógica (respetando SRP):
        1. Validación del audio (si no se omite)
        2. Preparación completa del audio (adaptador AudioPreparer)
        3. Envío a Groq API (adaptador GroqApiClient)
        4. Limpieza de archivos temporales

        Args:
            audio_path: Ruta al archivo de audio

        Returns:
            Tuple con (texto_transcrito, metadata)
        """
        if not GROQ_API_KEY:
            raise RuntimeError("Falta GROQ_API_KEY")

        logger.info(f"[GROQ] Iniciando transcripción: {audio_path}")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

        original_size = os.path.getsize(audio_path)
        logger.info(f"[GROQ] Audio original: {audio_path}, tamaño={original_size} bytes")

        # Verificar FFmpeg API antes de empezar
        if not self.ffmpeg_adapter.ensure_ffmpeg_api_ready():
            raise ConnectionError("FFmpeg API no disponible")

        # Validar audio (si no se omite)
        if not self.skip_validation:
            try:
                validation = self.ffmpeg_adapter.validate_audio(audio_path)
                logger.info(f"[GROQ] Validación exitosa: {validation.get('metadata', {}).get('duration_seconds', 0)}s")

                # Verificar si es válido
                if not validation['valid']:
                    issues = validation.get('issues', [])
                    non_length_issues = [
                        issue for issue in issues
                        if "demasiado largo" not in issue.lower() and "too long" not in issue.lower()
                    ]
                    if non_length_issues:
                        error_msg = f"Audio no válido: {', '.join(non_length_issues)}"
                        logger.error(f"[GROQ] {error_msg}")
                        raise AudioValidationError(error_msg, validation_result=validation)

                    logger.warning("[GROQ] Audio inválido solo por duración; continuando...")
                    if not validation['optimal']:
                        warnings = validation.get('warnings', [])
                        logger.warning(f"[GROQ] Audio no óptimo: {', '.join(warnings)}")

            except AudioValidationError:
                raise
            except Exception as e:
                logger.warning(f"[GROQ] Error en validación, continuando: {e}")

        # FASE 1: Preparación completa del audio
        logger.info(f"[GROQ] Fase 1: Preparando audio {audio_path}...")
        prep_result = None
        try:
            logger.info(f"[GROQ] Llamando audio_preparer.prepare_audio con skip_validation={self.skip_validation}")
            prep_result = self.audio_preparer.prepare_audio(audio_path, skip_validation=self.skip_validation)
            logger.info(f"[GROQ] Preparación completada: prep_result keys = {list(prep_result.keys()) if prep_result else None}")
            if prep_result and prep_result.get('chunks'):
                logger.info(f"[GROQ] Usando {len(prep_result['chunks'])} chunks")
            elif prep_result and prep_result.get('audio_path'):
                logger.info(f"[GROQ] Usando archivo único: {prep_result['audio_path']}")
            else:
                logger.warning(f"[GROQ] Preparación completada pero sin chunks ni audio_path: {prep_result}")

            # FASE 2: Enviar a Groq API
            logger.info("[GROQ] Fase 2: Enviando a Groq API...")
            logger.info(f"[GROQ] prep_result enviado a groq_client: {type(prep_result)}")
            logger.info(f"[GROQ] prep_result content: {prep_result}")

            try:
                result = self.groq_client.transcribe_audio(prep_result)
                logger.info(f"[GROQ] groq_client result type: {type(result)}, len: {len(result) if hasattr(result, '__len__') else 'N/A'}")

                if not isinstance(result, tuple) or len(result) != 2:
                    raise ValueError(f"[GROQ] groq_client.transcribe_audio returned invalid result: {result}")

                text, transcription_time = result
                logger.info(f"[GROQ] Unpacked result - text len: {len(text)}, time: {transcription_time}")
                logger.info(f"[GROQ] Transcripción completada: {len(text)} caracteres, tiempo={transcription_time}s")

                metadata = {
                    "engine": "groq-whisper",
                    "model": "whisper-large-v3",  # TODO: usar env var
                    "transcription_time": transcription_time,
                    "audio_duration": None,
                }

                logger.info(f"[GROQ] Returning successful result: text_len={len(text)}, metadata_keys={list(metadata.keys())}")
                return text, metadata

            except Exception as groq_error:
                logger.error(f"[GROQ] Error in groq_client.transcribe_audio: {groq_error}", exc_info=True)
                raise RuntimeError(f"Failed to transcribe audio with Groq API: {groq_error}") from groq_error

        except Exception as e:
            logger.error(f"[GROQ] Error en transcripción: {e}", exc_info=True)
            raise
        finally:
            # Limpieza de archivos temporales
            if prep_result:
                for tmp_file in prep_result.get("cleanup_files", []):
                    if tmp_file and os.path.exists(tmp_file):
                        try:
                            os.unlink(tmp_file)
                            logger.info(f"[GROQ] Eliminado temporal: {tmp_file}")
                        except Exception as e:
                            logger.warning(f"[GROQ] No se pudo eliminar {tmp_file}: {e}")

                # Limpiar chunks si existen
                if prep_result.get("is_chunked") and prep_result.get("chunks"):
                    for chunk_path in prep_result["chunks"]:
                        try:
                            if os.path.exists(chunk_path):
                                os.unlink(chunk_path)
                                logger.info(f"[GROQ] Eliminado chunk: {chunk_path}")
                        except Exception as e:
                            logger.warning(f"[GROQ] No se pudo eliminar chunk {chunk_path}: {e}")


