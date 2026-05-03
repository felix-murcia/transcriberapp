"""
Infrastructure layer - transcription implementations.
Concrete implementations of transcription ports.
"""

from transcriber_app.domain.ports import AudioTranscriberPort


class GroqAudioTranscriber(AudioTranscriberPort):
    """Groq-based audio transcriber adapter.

    This adapter delegates to the actual GroqTranscriber implementation
    to maintain pure hexagonal architecture where infrastructure depends
    on domain ports.
    """

    def __init__(self):
        from transcriber_app.infrastructure.ai.groq.transcriber import GroqTranscriber
        self._transcriber = GroqTranscriber()

    def transcribe(self, audio_path: str) -> tuple[str, dict]:
        """Transcribe audio using the Groq implementation."""
        return self._transcriber.transcribe(audio_path)
