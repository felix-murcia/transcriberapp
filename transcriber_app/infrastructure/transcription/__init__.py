"""
Infrastructure layer - transcription implementations.
Concrete implementations of transcription ports.
"""

from transcriber_app.domain.ports import AudioTranscriberPort
from transcriber_app.domain.exceptions import TranscriptionError


class GroqAudioTranscriber(AudioTranscriberPort):
    """Groq-based audio transcriber stub."""

    def __init__(self):
        pass

    def transcribe(self, audio_path: str) -> tuple[str, dict]:
        """Transcribe audio - stub implementation."""
        # Real implementation would call Groq API
        # This is a stub returning empty transcription
        return "", {"time": 0.0}
