"""
FFmpeg Health Adapter - Handles FFmpeg API health checking and status monitoring.
"""

import time
import logging
from typing import Tuple, Optional, Dict, Any

from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient

logger = logging.getLogger("transcribeapp")


class FfmpegHealthAdapter:
    """Adapter for FFmpeg API health monitoring and status checks."""

    def __init__(self, api_client: Optional[FfmpegApiClient] = None):
        self.api_client = api_client or FfmpegApiClient()

    def check_api_health(self) -> Tuple[bool, Optional[str]]:
        """
        Check if FFmpeg API is healthy.
        Returns (is_healthy, error_message)
        """
        try:
            logger.info(f"[FFMPEG HEALTH] Checking API health: {self.api_client.base_url}/health")
            response = self.api_client.get("/health", timeout=self.api_client._get_timeout("health"))
            data = response.json()

            logger.info(f"[FFMPEG HEALTH] API healthy: {data}")
            return True, None

        except Exception as e:
            error_msg = f"FFmpeg API health check failed: {str(e)}"
            logger.error(f"[FFMPEG HEALTH] {error_msg}")
            return False, error_msg

    def check_gpu_status(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check GPU status in FFmpeg API.
        Returns (is_available, gpu_info)
        """
        try:
            logger.info(f"[FFMPEG HEALTH] Checking GPU status: {self.api_client.base_url}/gpu-status")
            response = self.api_client.get("/gpu-status", timeout=self.api_client._get_timeout("gpu_status"))
            data = response.json()

            if data.get("gpu_available"):
                logger.info(f"[FFMPEG HEALTH] GPU available: {data.get('gpu_name')}")
                return True, data
            else:
                logger.warning("[FFMPEG HEALTH] GPU not available, will use CPU")
                return False, data

        except Exception as e:
            logger.warning(f"[FFMPEG HEALTH] Error checking GPU status: {e}")
            return False, None

    def check_chunked_endpoint_available(self) -> bool:
        """
        Check if chunked conversion endpoint is available.
        Returns True if available, False otherwise.
        """
        import requests

        try:
            logger.info(f"[FFMPEG HEALTH] Checking chunked endpoint: {self.api_client.base_url}/audio/convert-to-mp3-chunked")

            # Usar una ruta que sabemos que no existe pero que el servidor pueda "verificar"
            # El servidor intentará acceder al archivo y devolverá un error específico si existe el endpoint
            test_path = "/tmp/nonexistent_test_file_for_endpoint_check.webm"

            url = f"{self.api_client.base_url}/audio/convert-to-mp3-chunked"
            timeout = self.api_client._get_timeout("endpoint_check")

            logger.debug(f"[FFMPEG HEALTH] Testing endpoint with non-existent file: {test_path}")

            response = requests.post(
                url,
                json={"path": test_path, "max_size_mb": 22},
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            logger.info(f"[FFMPEG HEALTH] Response status: {response.status_code}")
            logger.debug(f"[FFMPEG HEALTH] Response content: {response.text}")

            # Si el servidor devuelve 404 con "NOT FOUND", significa que el endpoint no existe
            if response.status_code == 404 and "NOT FOUND" in response.text.upper():
                logger.info("[FFMPEG HEALTH] Endpoint does not exist (404 NOT FOUND)")
                return False

            # Si devuelve 404 con mensaje de archivo no encontrado, significa que el endpoint existe
            # pero el archivo no está disponible (lo cual es esperado para la verificación)
            if response.status_code == 404 and "archivo no encontrado" in response.text.lower():
                logger.info("[FFMPEG HEALTH] Endpoint exists (file not found error)")
                return True

            # Cualquier otro código significa que el endpoint existe
            logger.info(f"[FFMPEG HEALTH] Endpoint exists (status: {response.status_code})")
            return True

        except Exception as e:
            logger.error(f"[FFMPEG HEALTH] Error checking chunked endpoint: {e}")
            return False

        except Exception as e:
            logger.error(f"[FFMPEG HEALTH] Error checking chunked endpoint: {e}")
            return False

    def wait_for_api_ready(self, timeout: int = None) -> bool:
        """
        Wait for FFmpeg API to be ready.
        Returns True if ready within timeout, False otherwise.
        """
        timeout = timeout or self.api_client._get_timeout("ready")

        logger.info(f"[FFMPEG HEALTH] Waiting for API ready (timeout={timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            is_healthy, error = self.check_api_health()
            if is_healthy:
                logger.info("[FFMPEG HEALTH] API is ready")
                return True
            logger.info(f"[FFMPEG HEALTH] API not ready yet, retrying... ({error})")
            time.sleep(2)

        logger.error(f"[FFMPEG HEALTH] API not ready after {timeout} seconds")
        return False