# transcriber_app/runner/orchestrator.py

import os
from transcriber_app.modules.logging.logging_config import setup_logging
from transcriber_app.modules.ai.ai_manager import AIManager, log_agent_result
from transcriber_app.modules.ffmpeg_client import validate_audio

# Logging
logger = setup_logging("transcribeapp")


class AudioValidationError(Exception):
    """Excepción cuando el audio no pasa la validación."""
    def __init__(self, message, validation_result=None):
        super().__init__(message)
        self.validation_result = validation_result


class Orchestrator:
    def __init__(self, receiver, transcriber, formatter, save_files=True):
        self.receiver = receiver
        self.transcriber = transcriber
        self.formatter = formatter
        self.save_files = save_files
        logger.info(f"[ORCHESTRATOR] Orchestrator inicializado con componentes (save_files={save_files}).")

    def run_audio(self, audio_path, mode="default"):
        logger.info(f"[ORCHESTRATOR] Ejecutando flujo de audio para: {audio_path} con modo: {mode}")

        # 1. Cargar audio
        audio_info = self.receiver.load(audio_path)

        # 2. Validar audio antes de transcripción
        logger.info(f"[ORCHESTRATOR] Validando audio: {audio_info['path']}")
        try:
            validation_result = validate_audio(audio_info["path"])
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Error al validar audio: {e}. Continuando con transcripción.")
            validation_result = {"valid": True, "issues": [], "warnings": []}

        if not validation_result.get("valid", False):
            issues = validation_result.get("issues", [])
            warnings = validation_result.get("warnings", [])
            error_msg = f"Audio no válido: {', '.join(issues)}" if issues else "Audio no válido"
            logger.error(f"[ORCHESTRATOR] {error_msg}")
            raise AudioValidationError(error_msg, validation_result)

        if validation_result.get("warnings"):
            logger.warning(f"[ORCHESTRATOR] Advertencias de validación: {validation_result['warnings']}")

        # 3. Transcribir
        text, metadata = self.transcriber.transcribe(audio_info["path"])
        logger.info(f"[ORCHESTRATOR] Metadata de transcripción: {metadata}")

        # 4. Guardar transcripción
        safe_name = audio_info["name"].lower()
        self.formatter.save_transcription(safe_name, text, enforce_save=self.save_files)

        # 5. Resumir con Gemini (nuevo sistema)
        summary_output = AIManager.summarize(text, mode)

        # 6. Log básico del agente
        log_agent_result(summary_output)

        # 7. Guardar métricas (SIEMPRE se guardan)
        self.formatter.save_metrics(audio_info["name"], summary_output, mode)

        # 8. Guardar salida final
        output_file = self.formatter.save_output(audio_info["name"], summary_output, mode, enforce_save=self.save_files)
        return (output_file, text, summary_output)

    def run_text(self, text_path, mode="default"):
        logger.info(f"[ORCHESTRATOR] Ejecutando flujo de texto para: {text_path} con modo: {mode}")

        name = os.path.splitext(os.path.basename(text_path))[0]

        # 1. Leer texto
        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read()

        # 2. Resumir con Gemini
        summary_output = AIManager.summarize(text, mode)

        # 3. Log del agente
        log_agent_result(summary_output)

        # 4. Guardar salida final
        output_file = self.formatter.save_output(name, summary_output, mode, enforce_save=self.save_files)
        return (output_file, text, summary_output)
