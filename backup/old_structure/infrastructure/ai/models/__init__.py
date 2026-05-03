"""
Infrastructure layer - AI model implementations.
Concrete implementations of AI model ports.
"""

from transcriber_app.domain.ports import AIModelPort


class GroqAIModelAdapter(AIModelPort):
    """Adapter for Groq AI model implementation."""

    def __init__(self):
        from transcriber_app.infrastructure.ai.groq.model import GroqModel
        self._model = GroqModel()

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using Groq model."""
        return self._model.transcribe(audio_path)

    def run_agent(self, mode: str, text: str) -> str:
        """Run agent using Groq model."""
        return self._model.run_agent(mode, text)


class GeminiAIModelAdapter(AIModelPort):
    """Adapter for Gemini AI model implementation."""

    def __init__(self):
        from transcriber_app.infrastructure.ai.gemini.client import GeminiModel
        self._model = GeminiModel()

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using Gemini model."""
        return self._model.transcribe(audio_path)

    def run_agent(self, mode: str, text: str) -> str:
        """Run agent using Gemini model."""
        return self._model.run_agent(mode, text)