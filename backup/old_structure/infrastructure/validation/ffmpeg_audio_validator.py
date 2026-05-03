"""
FFmpeg Audio Validator - Main adapter implementing FfmpegValidatorPort protocol.

This adapter composes the smaller, focused adapters to provide a complete
FFmpeg validation and processing interface.
"""

import logging
from typing import Optional, Dict, Any

from transcriber_app.domain.ports import AudioValidatorPort, FfmpegValidatorPort
from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient
from transcriber_app.infrastructure.validation.ffmpeg_health_adapter import FfmpegHealthAdapter
from transcriber_app.infrastructure.validation.ffmpeg_validation_adapter import FfmpegValidationAdapter
from transcriber_app.infrastructure.validation.ffmpeg_conversion_adapter import FfmpegConversionAdapter

logger = logging.getLogger("transcribeapp")


class FFmpegAudioValidator(AudioValidatorPort, FfmpegValidatorPort):
    """
    Main FFmpeg adapter implementing the FfmpegValidatorPort protocol.

    This adapter composes specialized adapters for different concerns:
    - Health checking
    - Audio validation
    - Audio conversion and processing
    """

    def __init__(self, api_client: Optional[FfmpegApiClient] = None):
        self.api_client = api_client or FfmpegApiClient()

        # Compose specialized adapters
        self.health_adapter = FfmpegHealthAdapter(self.api_client)
        self.validation_adapter = FfmpegValidationAdapter(self.api_client)
        self.conversion_adapter = FfmpegConversionAdapter(self.api_client)

        logger.info("[FFMPEG VALIDATOR] FFmpegAudioValidator initialized")

    def validate(self, audio_path: str) -> Dict[str, Any]:
        """Validate audio file - implements AudioValidatorPort."""
        return self.validation_adapter.validate_audio(audio_path)

    def ensure_ffmpeg_api_ready(self) -> bool:
        """Ensure FFmpeg API is ready."""
        return self.health_adapter.wait_for_api_ready()

    def validate_audio(self, path: str) -> Dict[str, Any]:
        """Validate audio file."""
        return self.validation_adapter.validate_audio(path)

    def convert_audio(self, path: str, fmt: str) -> bytes:
        """Convert audio to specified format."""
        return self.conversion_adapter.convert_audio(path, fmt)

    def clean_audio(self, path: str) -> bytes:
        """Clean audio file."""
        return self.conversion_adapter.clean_audio(path)

    def convert_to_mp3_chunked(self, path: str, max_size_mb: int) -> Optional[Dict[str, Any]]:
        """Convert audio to MP3 chunks for large files."""
        return self.conversion_adapter.convert_to_mp3_chunked(path, max_size_mb)

    def check_chunked_endpoint_available(self) -> bool:
        """Check if chunked endpoint is available."""
        return self.health_adapter.check_chunked_endpoint_available()

    # Additional convenience methods for direct access to specialized functionality

    def get_audio_info(self, path: str) -> Dict[str, Any]:
        """Get detailed audio information."""
        return self.validation_adapter.get_audio_info(path)

    def check_api_health(self) -> tuple[bool, Optional[str]]:
        """Check FFmpeg API health."""
        return self.health_adapter.check_api_health()

    def check_gpu_status(self) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Check GPU status."""
        return self.health_adapter.check_gpu_status()