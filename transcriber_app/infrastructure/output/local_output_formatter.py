# transcriber_app/infrastructure/output/local_output_formatter.py
import os
import json
from typing import Dict, Any
from transcriber_app.infrastructure.logging.logging_config import setup_logging
from transcriber_app.domain.ports import OutputFormatterPort

# Logging
logger = setup_logging("transcribeapp")

# Rutas absolutas para Docker
APP_BASE_DIR = os.getenv("APP_BASE_DIR", "/app")


class LocalOutputFormatter(OutputFormatterPort):
    def save_output(self, job_id: str, audio_name: str, content: str, mode: str) -> str:
        """
        Save formatted output.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            content: Formatted content to save
            mode: The summarization mode used

        Returns:
            str: Path where output was saved
        """
        logger.info(f"[OUTPUT FORMATTER] Guardando salida para job {job_id}: {audio_name} con modo: {mode}")
        output_filename = f"{audio_name}_{mode}.md"
        output_path = os.path.join(APP_BASE_DIR, "outputs", output_filename)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"[OUTPUT FORMATTER] Archivo guardado en: {output_path}")

        return output_path

    def save_transcription(self, job_id: str, audio_name: str, text: str) -> str:
        """
        Save raw transcription text.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            text: Transcribed text

        Returns:
            str: Path where transcription was saved
        """
        logger.info(f"[OUTPUT FORMATTER] Guardando transcripción para job {job_id}: {audio_name}")
        # Usar ruta absoluta /app/transcripts que coincide con el volumen de Docker
        transcripts_dir = os.path.join(APP_BASE_DIR, "transcripts")
        path = os.path.join(transcripts_dir, f"{audio_name}.txt")

        os.makedirs(transcripts_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"[OUTPUT FORMATTER] Transcripción guardada en: {path}")

        return path

    def save_metrics(self, job_id: str, audio_name: str, summary: str, mode: str) -> Dict[str, Any]:
        """
        Save processing metrics.

        Args:
            job_id: Unique job identifier
            audio_name: Name of the audio file
            summary: Summary output
            mode: The summarization mode used

        Returns:
            dict: Saved metrics
        """
        metrics = {
            "job_id": job_id,
            "name": audio_name,
            "mode": mode,
            "length": len(summary),
            "summary_length": len(summary),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        # Usar ruta absoluta /app/outputs/metrics que coincide con el volumen de Docker
        metrics_dir = os.path.join(APP_BASE_DIR, "outputs", "metrics")
        path = os.path.join(metrics_dir, f"{audio_name}_{mode}.json")

        # Crear el directorio si no existe
        os.makedirs(metrics_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logger.info(f"[OUTPUT FORMATTER] Métricas guardadas en: {path}")
        return metrics
