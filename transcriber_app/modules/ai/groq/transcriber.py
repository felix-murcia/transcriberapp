import os
import time
import tempfile
import requests
from typing import Tuple, Dict, Any

from transcriber_app.config import GROQ_API_KEY
from transcriber_app.modules.ai.base.transcriber_interface import TranscriberInterface
from transcriber_app.modules.ffmpeg_client import convert_audio, clean_audio


class GroqTranscriber(TranscriberInterface):
    URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    MODEL = "whisper-large-v3"

    def ensure_wav(self, input_path: str) -> str:
        """
        Convierte el archivo a WAV 16kHz mono usando ffmpeg-api.
        """
        wav_bytes = convert_audio(input_path, fmt="wav")

        tmp = tempfile.mktemp(suffix=".wav")
        with open(tmp, "wb") as f:
            f.write(wav_bytes)

        return tmp

    def clean_wav(self, wav_path: str) -> str:
        """
        Limpia el audio usando ffmpeg-api (/audio/clean).
        """
        cleaned_bytes = clean_audio(wav_path)

        cleaned_path = tempfile.mktemp(suffix="_clean.wav")
        with open(cleaned_path, "wb") as f:
            f.write(cleaned_bytes)

        return cleaned_path

    def transcribe(self, audio_path: str) -> Tuple[str, Dict[str, Any]]:
        if not GROQ_API_KEY:
            raise RuntimeError("Falta GROQ_API_KEY")

        # 1. Convertir a WAV estándar
        wav = self.ensure_wav(audio_path)

        # 2. Limpiar audio (opcional pero recomendado)
        cleaned_wav = self.clean_wav(wav)

        start = time.time()

        with open(cleaned_wav, "rb") as f:
            resp = requests.post(
                self.URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                data={"model": self.MODEL},
                files={"file": ("audio.wav", f, "audio/wav")},
                timeout=300
            )

        # Limpieza de temporales
        try:
            os.unlink(wav)
        except:
            pass

        try:
            os.unlink(cleaned_wav)
        except:
            pass

        resp.raise_for_status()

        text = resp.json().get("text", "").strip()
        elapsed = time.time() - start

        return text, {
            "engine": "groq-whisper",
            "model": self.MODEL,
            "transcription_time": elapsed,
        }
