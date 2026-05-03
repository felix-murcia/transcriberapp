"""
Groq API adapter for transcription services.
Implements TranscriptionServicePort using Groq API.
"""

import os
import time
import json
import logging
from typing import Dict, Any, Tuple, List

import requests

from domain.ports import TranscriptionServicePort
from domain.exceptions import ExternalServiceError, TranscriptionError

logger = logging.getLogger(__name__)


class GroqTranscriptionAdapter(TranscriptionServicePort):
    """Adapter for Groq transcription service."""

    def __init__(self):
        self.api_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/audio/transcriptions")
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL_TRANSCRIBER", "whisper-large-v3")
        self.timeout = int(os.getenv("GROQ_TIMEOUT_API", "300"))

        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")

    def _transcribe_single_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Transcribe a single audio file using Groq API."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        start_time = time.time()

        try:
            with open(file_path, "rb") as audio_file:
                files = {"file": (os.path.basename(file_path), audio_file, "audio/mpeg")}
                data = {"model": self.model}

                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=self.timeout
                )

                response.raise_for_status()

                result = response.json()
                transcription_text = result.get("text", "").strip()

                elapsed_time = time.time() - start_time

                metadata = {
                    "engine": "groq",
                    "model": self.model,
                    "transcription_time": elapsed_time,
                    "file_size_bytes": os.path.getsize(file_path),
                    "provider": "groq"
                }

                return transcription_text, metadata

        except requests.exceptions.RequestException as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Groq API request failed after {elapsed_time:.2f}s: {e}")
            raise ExternalServiceError("groq", f"API request failed: {e}") from e
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Unexpected error in Groq transcription after {elapsed_time:.2f}s: {e}")
            raise TranscriptionError(f"Groq transcription failed: {e}") from e

    def transcribe_audio(self, audio_path: str) -> Tuple[str, Dict[str, Any]]:
        """Transcribe a single audio file."""
        logger.info(f"Starting Groq transcription for: {audio_path}")
        return self._transcribe_single_file(audio_path)

    def transcribe_audio_chunked(self, audio_chunks: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Transcribe multiple audio chunks and combine results."""
        logger.info(f"Starting Groq chunked transcription for {len(audio_chunks)} chunks")

        all_transcriptions = []
        total_time = 0.0
        total_size = 0

        for i, chunk_path in enumerate(audio_chunks, 1):
            logger.info(f"Processing chunk {i}/{len(audio_chunks)}: {chunk_path}")
            transcription_text, metadata = self._transcribe_single_file(chunk_path)

            all_transcriptions.append(transcription_text)
            total_time += metadata["transcription_time"]
            total_size += metadata["file_size_bytes"]

        # Combine all transcriptions
        combined_text = " ".join(all_transcriptions)

        metadata = {
            "engine": "groq",
            "model": self.model,
            "transcription_time": total_time,
            "total_file_size_bytes": total_size,
            "chunks_processed": len(audio_chunks),
            "provider": "groq"
        }

        logger.info(f"Completed chunked transcription: {len(combined_text)} chars, {total_time:.2f}s total")
        return combined_text, metadata