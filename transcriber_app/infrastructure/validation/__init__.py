"""
Infrastructure layer - audio validation implementations.
Concrete implementations of audio validation ports.
"""

from transcriber_app.domain.ports import AudioValidatorPort


class FFmpegAudioValidator(AudioValidatorPort):
    """FFmpeg-based audio validator implementation."""

    def validate(self, audio_path: str) -> dict:
        """Validate audio using FFmpeg."""
        # Real implementation would call FFmpeg
        # This is a stub for compatibility
        try:
            # Check if file exists
            import os
            if os.path.exists(audio_path):
                # Basic validation: file exists and has size
                size = os.path.getsize(audio_path)
                return {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "metadata": {"size_bytes": size}
                }
            return {"valid": False, "issues": ["File not found"], "warnings": [], "metadata": {}}
        except Exception as e:
            return {
                "valid": True,
                "issues": [],
                "warnings": [f"Validation check failed: {str(e)}"],
                "metadata": {}
            }
