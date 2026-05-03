# transcriber_app/modules/ai/groq/model.py

from transcriber_app.domain.ports import AIModelPort
from transcriber_app.infrastructure.ai.groq.client import GroqClient


class GroqModel(AIModelPort):
    def __init__(self):
        self.client = GroqClient()

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using Groq."""
        # Implementation would call Groq transcription API
        # For now, return stub
        return f"Groq transcription of {audio_path}"

    def run_agent(self, mode: str, text: str) -> str:
        """Run agent on text."""
        prompt = f"Process this text in {mode} mode: {text}"
        return self.client.chat(prompt)
