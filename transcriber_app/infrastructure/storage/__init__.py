"""
Infrastructure layer - output formatting implementations.
Concrete implementations of output formatting ports.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any
from transcriber_app.domain.ports import OutputFormatterPort
from transcriber_app.infrastructure.logging.logging_config import setup_logging

logger = setup_logging("transcribeapp")


def get_outputs_dir() -> Path:
    """Get outputs directory path (runtime lookup of env var)."""
    # Resolve at runtime to allow overrides in tests
    app_base = os.getenv("APP_BASE_DIR")
    if app_base:
        return Path(app_base) / "outputs"
    return Path.cwd() / "outputs"


def get_transcripts_dir() -> Path:
    """Get transcripts directory path (runtime lookup of env var)."""
    app_base = os.getenv("APP_BASE_DIR")
    if app_base:
        return Path(app_base) / "transcripts"
    return Path.cwd() / "transcripts"


class LocalOutputFormatter(OutputFormatterPort):
    """Local file system output formatter implementation."""

    def save_transcription(self, job_id: str, audio_name: str, text: str) -> str:
        """Save raw transcription text to file."""
        dir_path = get_transcripts_dir()
        dir_path.mkdir(parents=True, exist_ok=True)

        safe_name = audio_name.lower()
        path = dir_path / f"{safe_name}.txt"

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

        logger.info(f"[OUTPUT FORMATTER] Transcription saved to: {path}")
        return str(path)

    def save_output(self, job_id: str, audio_name: str, content: str, mode: str) -> str:
        """Save formatted output markdown to file."""
        dir_path = get_outputs_dir()
        dir_path.mkdir(parents=True, exist_ok=True)

        output_filename = f"{audio_name}_{mode}.md"
        output_path = dir_path / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[OUTPUT FORMATTER] Output saved to: {output_path}")
        return str(output_path)

    def save_metrics(self, job_id: str, audio_name: str, summary: str, mode: str) -> Dict[str, Any]:
        """Save processing metrics to JSON file."""
        metrics_dir = get_outputs_dir() / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        metrics = {
            "job_id": job_id,
            "name": audio_name,
            "audio_name": audio_name,
            "mode": mode,
            "length": len(summary),
            "summary_length": len(summary),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        path = metrics_dir / f"{audio_name}_{mode}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logger.info(f"[OUTPUT FORMATTER] Metrics saved to: {path}")
        return metrics
