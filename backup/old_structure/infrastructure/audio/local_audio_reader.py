# transcriber_app/infrastructure/audio/local_audio_reader.py
import os
from pathlib import Path
from transcriber_app.infrastructure.logging.logging_config import setup_logging
from transcriber_app.domain.ports import AudioFileReaderPort
from transcriber_app.domain.entities import AudioFile

# Logging
logger = setup_logging("transcribeapp")


class LocalAudioFileReader(AudioFileReaderPort):
    def load(self, audio_path: str) -> AudioFile:
        logger.info(f"[AUDIO READER] Cargando audio desde: {audio_path}")
        abs_path = Path(audio_path).resolve()

        if not abs_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size = abs_path.stat().st_size
        filename = abs_path.name
        extension = abs_path.suffix.lower() if abs_path.suffix else ""

        return AudioFile(
            path=str(abs_path),
            filename=filename,
            size_bytes=file_size,
            extension=extension,
            is_valid=True,
            validation_issues=[],
            validation_warnings=[],
        )
