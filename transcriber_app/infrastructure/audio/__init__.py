"""
Infrastructure layer - audio processing implementations.
Concrete implementations of audio-related ports.
"""

from .local_audio_reader import LocalAudioFileReader

__all__ = ['LocalAudioFileReader']