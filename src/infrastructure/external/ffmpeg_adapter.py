"""
FFmpeg API adapter for audio processing services.
Implements AudioProcessingPort using remote FFmpeg API.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

import requests

from domain.ports import AudioProcessingPort
from domain.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class RemoteFFmpegAdapter(AudioProcessingPort):
    """Adapter for remote FFmpeg API audio processing."""

    def __init__(self):
        self.api_url = os.getenv("FFMPEG_API_URL", "http://ffmpeg-api-prod:8080")
        self.timeout = int(os.getenv("FFMPEG_TIMEOUT", "120"))

    def _make_request(self, endpoint: str, files: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to FFmpeg API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        try:
            if files:
                # Multipart file upload
                response = requests.post(url, files=files, data=data, timeout=self.timeout)
            else:
                # JSON request
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"FFmpeg API request failed for {endpoint}: {e}")
            raise ExternalServiceError("ffmpeg_api", f"Request failed: {e}") from e

    def validate_audio(self, audio_path: str) -> Dict[str, Any]:
        """Validate audio file using FFmpeg API."""
        logger.info(f"Validating audio file: {audio_path}")

        try:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                result = self._make_request("/validate", files=files)

            return {
                "valid": result.get("valid", False),
                "issues": result.get("issues", []),
                "warnings": result.get("warnings", []),
                "metadata": result.get("metadata", {})
            }

        except FileNotFoundError:
            return {
                "valid": False,
                "issues": [f"File not found: {audio_path}"],
                "warnings": [],
                "metadata": {}
            }

    def convert_audio(self, audio_path: str, output_format: str) -> bytes:
        """Convert audio file to specified format."""
        logger.info(f"Converting audio {audio_path} to {output_format}")

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
            data = {"format": output_format}
            result = self._make_request("/convert", files=files, data=data)

        # Assuming the API returns base64 encoded audio
        import base64
        audio_data = base64.b64decode(result["audio_data"])
        return audio_data

    def clean_audio(self, audio_path: str) -> bytes:
        """Clean/normalize audio using FFmpeg API."""
        logger.info(f"Cleaning audio: {audio_path}")

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
            result = self._make_request("/clean", files=files)

        # Assuming the API returns base64 encoded audio
        import base64
        audio_data = base64.b64decode(result["audio_data"])
        return audio_data

    def get_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """Extract metadata from audio file."""
        logger.info(f"Extracting metadata from: {audio_path}")

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
            result = self._make_request("/metadata", files=files)

        return result