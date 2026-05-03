"""
FFmpeg Validation Adapter - Handles audio validation operations.
"""

import os
import tempfile
import logging
from typing import Optional, Dict, Any

from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient

logger = logging.getLogger("transcribeapp")


class FfmpegValidationAdapter:
    """Adapter for FFmpeg API audio validation operations."""

    def __init__(self, api_client: Optional[FfmpegApiClient] = None):
        self.api_client = api_client or FfmpegApiClient()

    def validate_audio(self, path: str) -> Dict[str, Any]:
        """
        Validate audio file before transcription.

        Returns dict with structure:
        {
            "valid": bool,
            "optimal": bool,
            "issues": list,
            "warnings": list,
            "recommendations": list,
            "metadata": dict,
            "suggested_conversion": dict
        }
        """
        self._ensure_file_exists(path)

        file_size = os.path.getsize(path)
        logger.info(f"[FFMPEG VALIDATION] Validating audio: {path} ({file_size / (1024*1024):.2f} MB)")

        # Para archivos muy grandes, devolver validación básica sin llamar al servidor
        if file_size > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"[FFMPEG VALIDATION] Archivo muy grande ({file_size / (1024*1024):.2f} MB), saltando validación completa")
            return {
                "valid": True,
                "optimal": False,
                "issues": [],
                "warnings": [f"Archivo muy grande ({file_size / (1024*1024):.2f} MB), validación limitada"],
                "recommendations": ["Usar chunking para archivos grandes"],
                "metadata": {"size_bytes": file_size},
                "suggested_conversion": {}
            }

        try:
            with open(path, "rb") as f:
                response = self.api_client.post(
                    "/audio/validate",
                    files={"file": f},
                    timeout=self.api_client._get_timeout("validate")
                )
                result = response.json()

            if result.get("valid"):
                duration = result['metadata'].get('duration_seconds', 0)
                logger.info(f"[FFMPEG VALIDATION] Audio valid: {duration}s duration")
            else:
                issues = result.get('issues', [])
                logger.warning(f"[FFMPEG VALIDATION] Audio invalid: {issues}")

            return result

        except Exception as e:
            logger.error(f"[FFMPEG VALIDATION] Validation error: {e}")
            raise

    def get_audio_info(self, path: str) -> Dict[str, Any]:
        """Get audio file information using ffprobe."""
        self._ensure_file_exists(path)

        file_size = os.path.getsize(path)
        logger.info(f"[FFMPEG VALIDATION] Getting audio info: {path} ({file_size} bytes)")

        try:
            with open(path, "rb") as f:
                response = self.api_client.post(
                    "/audio/info",
                    files={"file": f},
                    timeout=self.api_client._get_timeout("audio_info")
                )
                result = response.json()

            duration = result.get('duration', 0)
            codec = result.get('codec', 'unknown')
            logger.info(f"[FFMPEG VALIDATION] Audio info: duration={duration}s, codec={codec}")

            return result

        except Exception as e:
            logger.error(f"[FFMPEG VALIDATION] Error getting audio info: {e}")
            raise

    def _ensure_file_exists(self, path: str) -> None:
        """Ensure the audio file exists."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")

    def _save_debug_file(self, data: bytes, suffix: str) -> None:
        """Save debug file for small outputs."""
        debug_path = tempfile.mktemp(suffix=suffix)
        with open(debug_path, "wb") as f:
            f.write(data)
        logger.warning(f"[FFMPEG VALIDATION] Debug file saved: {debug_path}")