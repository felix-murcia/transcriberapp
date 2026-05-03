"""
FFmpeg API Client - Base HTTP client for FFmpeg API communication.
"""

import os
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger("transcribeapp")


class FfmpegApiClient:
    """Base client for FFmpeg API HTTP communication."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("FFMPEG_API_URL", "http://ffmpeg-api:8080")
        self.timeouts = {
            "health": int(os.getenv("FFMPEG_TIMEOUT_HEALTH", 5)),
            "gpu_status": int(os.getenv("FFMPEG_TIMEOUT_GPU_STATUS", 5)),
            "endpoint_check": int(os.getenv("FFMPEG_TIMEOUT_ENDPOINT_CHECK", 10)),
            "audio_info": int(os.getenv("FFMPEG_TIMEOUT_AUDIO_INFO", 30)),
            "convert": int(os.getenv("FFMPEG_TIMEOUT_CONVERT", 300)),
            "chunked": int(os.getenv("FFMPEG_TIMEOUT_CHUNKED", 600)),
            "clean": int(os.getenv("FFMPEG_TIMEOUT_CLEAN", 300)),
            "validate": int(os.getenv("FFMPEG_TIMEOUT_VALIDATE", 300)),
            "ready": int(os.getenv("FFMPEG_TIMEOUT_READY", 30)),
        }

    def _get_timeout(self, operation: str) -> int:
        """Get timeout for specific operation."""
        return self.timeouts.get(operation, 30)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to FFmpeg API."""
        url = f"{self.base_url}{endpoint}"
        timeout = kwargs.pop('timeout', self._get_timeout('default'))

        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"[FFMPEG API] {method.upper()} {endpoint} failed: {e}")
            raise

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return self._make_request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return self._make_request('POST', endpoint, **kwargs)