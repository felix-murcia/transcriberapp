"""
FFmpeg Conversion Adapter - Handles audio conversion and processing operations.
"""

import os
import tempfile
import logging
from typing import Optional, Dict, Any, Generator, Tuple, List

from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient
from transcriber_app.infrastructure.validation.ffmpeg_health_adapter import FfmpegHealthAdapter

logger = logging.getLogger("transcribeapp")


class FfmpegConversionAdapter:
    """Adapter for FFmpeg API audio conversion and processing operations."""

    def __init__(self, api_client: Optional[FfmpegApiClient] = None):
        self.api_client = api_client or FfmpegApiClient()
        self.health_adapter = FfmpegHealthAdapter(self.api_client)

    def convert_audio(self, path: str, fmt: str = "wav") -> bytes:
        """Convert audio file to specified format."""
        self._ensure_file_exists(path)
        self._ensure_api_healthy()

        file_size = os.path.getsize(path)
        logger.info(f"[FFMPEG CONVERSION] Converting: {path} -> {fmt} ({file_size} bytes)")

        try:
            with open(path, "rb") as f:
                response = self.api_client.post(
                    "/audio/convert",
                    files={"file": f},
                    data={"format": fmt},
                    timeout=self.api_client._get_timeout("convert")
                )

            result_bytes = response.content
            logger.info(f"[FFMPEG CONVERSION] Conversion successful: {len(result_bytes)} bytes output")

            if len(result_bytes) < 1000:
                logger.warning(f"[FFMPEG CONVERSION] Output file very small: {len(result_bytes)} bytes")
                self._save_debug_file(result_bytes, f"_debug_convert.{fmt}")

            return result_bytes

        except Exception as e:
            logger.error(f"[FFMPEG CONVERSION] Conversion error: {e}")
            raise

    def convert_to_mp3_chunked(self, path: str, max_size_mb: int = 22) -> Optional[Dict[str, Any]]:
        """
        Convert audio to MP3 and split into chunks for large files.

        Designed for audio files that exceed 25MB limit.
        Server expects JSON with audio path and returns chunk metadata.
        """
        self._ensure_file_exists(path)
        self._ensure_api_healthy()

        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        logger.info(f"[FFMPEG CONVERSION] Starting chunked MP3 conversion: {path} ({file_size_mb:.2f} MB)")

        container_path = self._adjust_path_for_container(path)

        try:
            response = self.api_client.post(
                "/audio/convert-to-mp3-chunked",
                json={"path": container_path, "max_size_mb": max_size_mb},
                timeout=self.api_client._get_timeout("chunked")
            )
            result = response.json()

            if result.get("error"):
                logger.warning(f"[FFMPEG CONVERSION] Chunked conversion error: {result.get('error')}")
                return None

            chunks = result.get("chunks", [])
            logger.info(f"[FFMPEG CONVERSION] Chunked conversion successful: {len(chunks)} chunks generated")
            return result

        except Exception as e:
            logger.error(f"[FFMPEG CONVERSION] Chunked conversion error: {e}")
            return None

    def convert_audio_streaming(
        self,
        path: str,
        max_size_mb: int = 22,
        cleanup: bool = True
    ) -> Generator[Tuple[int, bytes, int], None, None]:
        """
        Convert audio to MP3 using chunked endpoint and stream chunks.

        Args:
            path: Path to audio file
            max_size_mb: Max size per chunk (default 22MB for Groq margin)
            cleanup: Whether to delete temp files after reading

        Yields:
            Tuple (chunk_index, chunk_data, total_chunks) for each chunk
        """
        self._ensure_file_exists(path)
        self._ensure_api_healthy()

        endpoint_available = self.health_adapter.check_chunked_endpoint_available()
        logger.info(f"[FFMPEG CONVERSION] Chunked endpoint available: {endpoint_available}")
        if not endpoint_available:
            logger.warning("[FFMPEG CONVERSION] Chunked endpoint not available, but proceeding anyway")

        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        logger.info(f"[FFMPEG CONVERSION] Starting streaming conversion: {path} ({file_size_mb:.2f} MB)")

        container_path = self._adjust_path_for_container(path)

        temp_files_to_cleanup = []

        try:
            response = self.api_client.post(
                "/audio/convert-to-mp3-chunked",
                json={"path": container_path, "max_size_mb": max_size_mb},
                timeout=self.api_client._get_timeout("chunked")
            )

            result = response.json()
            if result.get("error"):
                raise RuntimeError(f"Streaming conversion error: {result['error']}")

            chunks = result.get("chunks", [])
            total_chunks = len(chunks)
            original_mp3 = result.get("original_mp3")

            if total_chunks == 0:
                raise RuntimeError("No chunks generated")

            logger.info(f"[FFMPEG CONVERSION] Streaming conversion successful: {total_chunks} chunks")

            for i, chunk_path in enumerate(chunks):
                if not os.path.exists(chunk_path):
                    logger.error(f"[FFMPEG CONVERSION] Chunk not found: {chunk_path}")
                    continue

                with open(chunk_path, "rb") as f:
                    chunk_data = f.read()

                chunk_size_mb = len(chunk_data) / (1024 * 1024)
                logger.info(f"[FFMPEG CONVERSION] Chunk {i+1}/{total_chunks}: {chunk_size_mb:.2f} MB")

                temp_files_to_cleanup.append(chunk_path)
                yield i, chunk_data, total_chunks

            # Cleanup temp files
            if cleanup:
                self._cleanup_temp_files(temp_files_to_cleanup)
                if original_mp3 and os.path.exists(original_mp3):
                    self._cleanup_temp_files([original_mp3])

        except Exception as e:
            logger.error(f"[FFMPEG CONVERSION] Streaming error: {e}")
            if cleanup:
                self._cleanup_temp_files(temp_files_to_cleanup)
            raise

    def clean_audio(self, path: str) -> bytes:
        """Clean audio file using FFmpeg API."""
        self._ensure_file_exists(path)
        self._ensure_api_healthy()

        file_size = os.path.getsize(path)
        logger.info(f"[FFMPEG CONVERSION] Cleaning audio: {path} ({file_size} bytes)")

        try:
            with open(path, "rb") as f:
                response = self.api_client.post(
                    "/audio/clean",
                    files={"file": f},
                    timeout=self.api_client._get_timeout("clean")
                )

            result_bytes = response.content
            logger.info(f"[FFMPEG CONVERSION] Cleaning successful: {len(result_bytes)} bytes output")

            if len(result_bytes) < 1000:
                logger.warning(f"[FFMPEG CONVERSION] Cleaned file very small: {len(result_bytes)} bytes")
                self._save_debug_file(result_bytes, "_debug_clean.wav")

            return result_bytes

        except Exception as e:
            logger.error(f"[FFMPEG CONVERSION] Cleaning error: {e}")
            raise

    def _ensure_file_exists(self, path: str) -> None:
        """Ensure the audio file exists."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")

    def _ensure_api_healthy(self) -> None:
        """Ensure FFmpeg API is healthy."""
        is_healthy, error = self.health_adapter.check_api_health()
        if not is_healthy:
            raise ConnectionError(f"FFmpeg API not available: {error}")

    def _adjust_path_for_container(self, path: str) -> str:
        """Adjust file path for FFmpeg API container mount."""
        if "/app/audios" in path:
            return path.replace("/app/audios", "/tmp/audios")
        elif "/app/uploads" in path:
            return path.replace("/app/uploads", "/tmp/uploads")
        return path

    def _cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files safely."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"[FFMPEG CONVERSION] Temp file deleted: {file_path}")
            except Exception as e:
                logger.warning(f"[FFMPEG CONVERSION] Could not delete {file_path}: {e}")

    def _save_debug_file(self, data: bytes, suffix: str) -> None:
        """Save debug file for small outputs."""
        debug_path = tempfile.mktemp(suffix=suffix)
        with open(debug_path, "wb") as f:
            f.write(data)
        logger.warning(f"[FFMPEG CONVERSION] Debug file saved: {debug_path}")