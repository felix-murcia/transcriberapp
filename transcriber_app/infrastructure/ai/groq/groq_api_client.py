# transcriber_app/infrastructure/ai/groq/groq_api_client.py

import os
import time
import json
import logging

import requests

from transcriber_app.config import GROQ_API_KEY
from transcriber_app.domain.ports import GroqApiPort

# Timeout configuration via environment variables
GROQ_TIMEOUT_API = int(os.getenv("GROQ_TIMEOUT_API", 300))

logger = logging.getLogger("transcribeapp")


class GroqApiClient(GroqApiPort):
    """Adaptador para comunicación con Groq API"""

    def __init__(self):
        self.url = os.getenv("GROQ_API_URL", "")
        self.model = os.getenv("GROQ_MODEL_TRANSCRIBER", "whisper-large-v3")

    def _send_file_to_groq(self, file_path: str, filename: str, content_type: str) -> tuple[str, float]:
        """Envía archivo a Groq API"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        start = time.time()
        final_size = os.path.getsize(file_path)
        logger.info(f"[GROQ_API] Enviando {filename}: {file_path}, tamaño={final_size} bytes")

        with open(file_path, "rb") as f:
            resp = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                data={"model": self.model},
                files={"file": (filename, f, content_type)},
                timeout=GROQ_TIMEOUT_API
            )

        elapsed = time.time() - start
        resp.raise_for_status()

        text = resp.json().get("text", "").strip()
        logger.info(f"[GROQ_API] Respuesta OK, texto: {len(text)} caracteres")

        return text, elapsed

    def transcribe_audio(self, audio_input: dict[str, any]) -> tuple[str, float]:
        """Transcribe audio - maneja tanto chunks como archivos individuales"""
        if audio_input.get("chunks"):
            # Transcripción por chunks
            chunks = audio_input["chunks"]
            logger.info(f"[GROQ_API] Transcribiendo {len(chunks)} chunks")
            all_texts = []
            total_time = 0.0

            for idx, chunk_path in enumerate(chunks, start=1):
                logger.info(f"[GROQ_API] Chunk {idx}/{len(chunks)}")
                text, elapsed = self._send_file_to_groq(chunk_path, "audio.mp3", "audio/mpeg")
                all_texts.append(text)
                total_time += elapsed

            combined_text = "\n".join([t for t in all_texts if t])
            return combined_text, total_time
        else:
            # Transcripción de archivo único
            audio_path = audio_input["audio_path"]
            logger.info(f"[GROQ_API] Transcribiendo archivo único: {audio_path}")
            return self._send_file_to_groq(audio_path, "audio.mp3", "audio/mpeg")