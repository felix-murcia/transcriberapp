"""
Gemini AI adapter for summarization services.
Implements AISummarizerPort using Gemini API.
"""

import os
import logging
from typing import List, Dict, Any

from domain.ports import AISummarizerPort
from domain.exceptions import ExternalServiceError, SummarizationError

logger = logging.getLogger(__name__)


class GeminiSummarizerAdapter(AISummarizerPort):
    """Adapter for Gemini AI summarization service."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = int(os.getenv("GEMINI_TIMEOUT", "120"))

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Import here to avoid hard dependency
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
        except ImportError:
            raise ImportError("google-generativeai package is required for Gemini adapter")

    def _get_agent_config(self, mode: str) -> Dict[str, Any]:
        """Get agent configuration for the specified mode."""
        # This would load agent configurations from somewhere
        # For now, return basic configs
        configs = {
            "default": {"temperature": 0.7, "max_tokens": 1000},
            "tecnico": {"temperature": 0.3, "max_tokens": 1500},
            "refinamiento": {"temperature": 0.5, "max_tokens": 1200},
            "ejecutivo": {"temperature": 0.6, "max_tokens": 800},
            "bullet": {"temperature": 0.4, "max_tokens": 600}
        }
        return configs.get(mode, configs["default"])

    def summarize(self, text: str, mode: str) -> str:
        """Summarize text using Gemini AI with specified mode."""
        logger.info(f"Starting Gemini summarization with mode: {mode}")

        try:
            # Get agent for the mode
            agent = self._get_agent_for_mode(mode)

            # Generate summary
            prompt = f"Please summarize the following text using the {mode} style:\n\n{text}"
            response = agent.generate_content(prompt)

            summary = response.text.strip()
            logger.info(f"Gemini summarization completed: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.error(f"Gemini summarization failed for mode {mode}: {e}")
            raise SummarizationError(f"Gemini summarization failed: {e}", mode=mode) from e

    def get_available_modes(self) -> List[str]:
        """Get list of available summarization modes."""
        return ["default", "tecnico", "refinamiento", "ejecutivo", "bullet"]

    def _get_agent_for_mode(self, mode: str):
        """Get configured Gemini model for the specified mode."""
        config = self._get_agent_config(mode)

        model = self.genai.GenerativeModel(
            self.model,
            generation_config=self.genai.types.GenerationConfig(
                temperature=config["temperature"],
                max_output_tokens=config["max_tokens"],
            )
        )

        return model