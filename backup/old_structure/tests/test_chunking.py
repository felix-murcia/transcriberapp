#!/usr/bin/env python3
"""
Script para probar el procesamiento de archivos grandes directamente.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Configurar la URL del servidor FFmpeg
os.environ["FFMPEG_API_URL"] = "http://localhost:8082"

from transcriber_app.domain.services import TranscriptionService
from transcriber_app.domain.entities import TranscriptionJob
from transcriber_app.di import get_transcription_service

def test_large_file_processing():
    # Archivo grande real para testing chunking
    audio_path = "audios/test_large_real.wav"

    if not os.path.exists(audio_path):
        print(f"❌ Archivo no encontrado: {audio_path}")
        return

    file_size = os.path.getsize(audio_path)
    print(f"📁 Probando archivo: {audio_path}")
    print(f"📏 Tamaño: {file_size / (1024*1024):.2f} MB")

    try:
        # Crear servicio de transcripción
        transcription_service = get_transcription_service(save_files=False)

        # Crear job
        job = TranscriptionJob(
            job_id="test-chunking",
            audio_filename="hexagonal.webm",
            audio_path=audio_path,
            mode="default",
            email=None
        )

        print("🚀 Iniciando procesamiento...")
        result = transcription_service.process_audio(job)

        print("✅ Procesamiento completado")
        print(f"📝 Transcripción: {len(result.transcription_text or '')} caracteres")
        print(f"🎯 Estado: {result.success}")

    except Exception as e:
        print(f"❌ Error durante procesamiento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_large_file_processing()