"""
Settings adapter for application configuration.
Implements SettingsPort using environment variables.
"""

import os
from domain.ports import SettingsPort, AppSettings


class EnvironmentSettingsAdapter(SettingsPort):
    """Adapter for application settings from environment variables."""

    def get_settings(self) -> AppSettings:
        """Get application settings from environment variables."""
        return AppSettings(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_api_url=os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/audio/transcriptions"),
            groq_model=os.getenv("GROQ_MODEL_TRANSCRIBER", "whisper-large-v3"),

            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),

            ffmpeg_api_url=os.getenv("FFMPEG_API_URL", "http://ffmpeg-api-prod:8080"),
            oauth2_server_url=os.getenv("OAUTH2_URL", "http://oauth2-server:8080"),

            uploads_dir=os.getenv("UPLOADS_DIR", "/app/audios"),
            outputs_dir=os.getenv("OUTPUTS_DIR", "/app/outputs"),
            transcripts_dir=os.getenv("TRANSCRIPTS_DIR", "/app/transcripts"),

            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "25")),
            supported_formats=["mp3", "webm", "wav", "m4a", "ogg"]
        )