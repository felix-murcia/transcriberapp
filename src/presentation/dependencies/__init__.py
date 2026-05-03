"""
FastAPI dependency injection functions.
Provides use case instances from infrastructure configuration.
Presentation layer delegates DI to infrastructure layer.
"""

# Import use case factories from infrastructure config
from infrastructure.config import (
    get_process_audio_use_case,
    get_process_chunked_use_case,
    get_job_status_use_case,
    get_summarize_text_use_case,
)

# Re-export for FastAPI dependency injection
__all__ = [
    "get_process_audio_use_case",
    "get_process_chunked_use_case",
    "get_job_status_use_case",
    "get_summarize_text_use_case",
]


# TODO: Implement chat use case when needed