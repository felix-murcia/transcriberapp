# transcriber_app/infrastructure/ai/groq/audio_preparer.py

import os
import tempfile
import logging

from transcriber_app.domain.ports import AudioPreparerPort, FfmpegValidatorPort
from transcriber_app.domain.exceptions import AudioValidationError
from transcriber_app.infrastructure.validation.ffmpeg_conversion_adapter import FfmpegConversionAdapter

logger = logging.getLogger("transcribeapp")


class FfmpegAudioPreparer(AudioPreparerPort):
    """Adaptador para preparación de audio usando FFmpeg API"""

    def __init__(self, ffmpeg_validator: FfmpegValidatorPort, ffmpeg_conversion_adapter: FfmpegConversionAdapter):
        self.ffmpeg = ffmpeg_validator
        self.conversion_adapter = ffmpeg_conversion_adapter

    def prepare_audio(self, audio_path: str, skip_validation: bool = False) -> dict[str, any]:
        """
        Prepara audio para transcripción usando FFmpeg.
        Usa el endpoint chunked para archivos grandes y conversión normal para pequeños.
        """
        logger.info(f"[FFMPEG_PREPARER] Preparando audio: {audio_path}")

        result = {
            "chunks": None,
            "audio_path": None,
            "is_chunked": False,
            "cleanup_files": []
        }

        # Verificar que el archivo existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Archivo no encontrado: {audio_path}")

        original_size = os.path.getsize(audio_path)
        logger.info(f"[FFMPEG_PREPARER] Tamaño original: {original_size / (1024*1024):.2f} MB")

        # Estrategia: Intentar chunked primero para archivos grandes o que probablemente excedan límite
        # Umbral de 15MB para considerar chunked (espacio para conversión)
        USE_CHUNKED_THRESHOLD_MB = 15
        threshold_bytes = USE_CHUNKED_THRESHOLD_MB * 1024 * 1024
        should_use_chunked = original_size > threshold_bytes

        logger.info(f"[FFMPEG_PREPARER] Umbral chunked: {USE_CHUNKED_THRESHOLD_MB}MB ({threshold_bytes} bytes)")
        logger.info(f"[FFMPEG_PREPARER] ¿Usar chunked?: {should_use_chunked}")

        if should_use_chunked:
            logger.info(f"[FFMPEG_PREPARER] Archivo grande ({original_size/(1024*1024):.2f}MB), usando chunked endpoint")

            # Verificar si el endpoint está disponible antes de intentar
            try:
                from transcriber_app.infrastructure.validation.ffmpeg_health_adapter import FfmpegHealthAdapter
                from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient
                health_adapter = FfmpegHealthAdapter(FfmpegApiClient())
                endpoint_available = health_adapter.check_chunked_endpoint_available()
                logger.info(f"[FFMPEG_PREPARER] Endpoint chunked disponible: {endpoint_available}")
            except Exception as e:
                logger.error(f"[FFMPEG_PREPARER] Error verificando endpoint chunked: {e}")
                endpoint_available = False

            if endpoint_available:
                logger.info("[FFMPEG_PREPARER] Intentando chunking con streaming...")
                try:
                    # Usar streaming para obtener los chunks
                    chunks = []
                    cleanup_files = []

                    chunk_count = 0
                    for chunk_idx, chunk_data, total_chunks in self.conversion_adapter.convert_audio_streaming(audio_path, max_size_mb=22):
                        chunk_count += 1
                        logger.info(f"[FFMPEG_PREPARER] Procesando chunk {chunk_idx+1}/{total_chunks} ({len(chunk_data)} bytes)")

                        # Guardar chunk temporalmente si es necesario
                        chunk_temp = tempfile.mktemp(suffix=f"_chunk_{chunk_idx}.mp3")
                        with open(chunk_temp, "wb") as f:
                            f.write(chunk_data)

                        chunks.append(chunk_temp)
                        cleanup_files.append(chunk_temp)

                    if chunks:
                        result["chunks"] = chunks
                        result["is_chunked"] = True
                        result["cleanup_files"].extend(cleanup_files)
                        logger.info(f"[FFMPEG_PREPARER] Chunking completado exitosamente: {len(chunks)} chunks")
                        return result
                    else:
                        logger.warning("[FFMPEG_PREPARER] Streaming completado pero no se generaron chunks")

                except Exception as e:
                    logger.error(f"[FFMPEG_PREPARER] Error en chunked streaming: {e}")
                    logger.info("[FFMPEG_PREPARER] Fallback a método tradicional")

            # Método tradicional: convertir a MP3 primero
            logger.info("[FFMPEG_PREPARER] Usando conversión tradicional a MP3")
        logger.info("[FFMPEG_PREPARER] Usando conversión tradicional a MP3")
        
        try:
            mp3_bytes = self.ffmpeg.convert_audio(audio_path, fmt="mp3")
            mp3_temp = tempfile.mktemp(suffix=".mp3")
            with open(mp3_temp, "wb") as f:
                f.write(mp3_bytes)

            mp3_size = os.path.getsize(mp3_temp)
            logger.info(f"[FFMPEG_PREPARER] MP3 generado: {mp3_temp}, tamaño={mp3_size / (1024*1024):.2f} MB")
            result["cleanup_files"].append(mp3_temp)

            # Verificar si el MP3 excede el límite de 25MB
            if mp3_size > 25 * 1024 * 1024:
                logger.warning(f"[FFMPEG_PREPARER] MP3 excede límite: {mp3_size / (1024*1024):.2f}MB")
                
                # Intentar chunking sobre el MP3 ya convertido
                try:
                    logger.info("[FFMPEG_PREPARER] Intentando chunking sobre MP3 existente")
                    # Usar streaming con el MP3 ya convertido
                    chunks = []
                    for chunk_idx, chunk_data, total_chunks in self.conversion_adapter.convert_audio_streaming(mp3_temp, max_size_mb=22):
                        chunk_temp = tempfile.mktemp(suffix=f"_chunk_{chunk_idx}.mp3")
                        with open(chunk_temp, "wb") as f:
                            f.write(chunk_data)
                        chunks.append(chunk_temp)
                        result["cleanup_files"].append(chunk_temp)
                    
                    if chunks:
                        result["chunks"] = chunks
                        result["is_chunked"] = True
                        logger.info(f"[FFMPEG_PREPARER] Chunking sobre MP3 completado: {len(chunks)} chunks")
                        return result
                        
                except Exception as e:
                    logger.error(f"[FFMPEG_PREPARER] Error en chunking de MP3: {e}")
                
                # Si todo falla, lanzar error
                raise AudioValidationError(
                    f"Audio demasiado grande: {mp3_size / (1024*1024):.2f}MB excede límite de 25MB"
                )

            # Limpiar audio (normalización, etc.)
            try:
                logger.info("[FFMPEG_PREPARER] Limpiando audio...")
                cleaned_bytes = self.ffmpeg.clean_audio(mp3_temp)
                cleaned_temp = tempfile.mktemp(suffix="_clean.mp3")
                with open(cleaned_temp, "wb") as f:
                    f.write(cleaned_bytes)
                result["audio_path"] = cleaned_temp
                result["cleanup_files"].append(cleaned_temp)
                logger.info(f"[FFMPEG_PREPARER] Audio limpiado: {cleaned_temp}")
                
                # Verificar tamaño final
                final_size = os.path.getsize(cleaned_temp)
                if final_size > 25 * 1024 * 1024:
                    logger.warning(f"[FFMPEG_PREPARER] Audio limpio excede límite: {final_size / (1024*1024):.2f}MB")
                    # Usar el MP3 original en lugar del limpio
                    result["audio_path"] = mp3_temp
                    logger.info("[FFMPEG_PREPARER] Usando MP3 original (sin limpiar)")
                
            except Exception as e:
                logger.warning(f"[FFMPEG_PREPARER] No se pudo limpiar el audio: {e}")
                result["audio_path"] = mp3_temp

            # Verificación final del tamaño
            final_path = result.get("audio_path")
            if final_path:
                final_size = os.path.getsize(final_path)
                if final_size > 25 * 1024 * 1024:
                    logger.error(f"[FFMPEG_PREPARER] Audio final excede límite: {final_size / (1024*1024):.2f}MB")
                    raise AudioValidationError(f"Audio final excede límite (25MB): {final_size / (1024*1024):.2f}MB")

            return result
            
        except Exception as e:
            logger.error(f"[FFMPEG_PREPARER] Error en preparación de audio: {e}")
            raise