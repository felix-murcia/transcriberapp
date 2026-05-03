# transcriber_app/infrastructure/ai/groq/ffmpeg_adapter.py

from typing import Optional
from transcriber_app.domain.ports import FfmpegValidatorPort
from transcriber_app.infrastructure.validation import FFmpegAudioValidator


class FfmpegAdapter(FfmpegValidatorPort):
    """Adaptador que envuelve las funciones de ffmpeg_validator"""

    def __init__(self, validator: Optional[FfmpegValidatorPort] = None):
        if validator is None:
            validator = FFmpegAudioValidator()
        self._validator = validator

    def ensure_ffmpeg_api_ready(self) -> bool:
        return self._validator.ensure_ffmpeg_api_ready()

    def validate_audio(self, path: str) -> dict:
        return self._validator.validate_audio(path)

    def convert_audio(self, path: str, fmt: str) -> bytes:
        return self._validator.convert_audio(path, fmt)

    def clean_audio(self, path: str) -> bytes:
        return self._validator.clean_audio(path)

    def convert_to_mp3_chunked(self, path: str, max_size_mb: int) -> Optional[dict]:
        return self._validator.convert_to_mp3_chunked(path, max_size_mb)

    def check_chunked_endpoint_available(self) -> bool:
        return self._validator.check_chunked_endpoint_available()