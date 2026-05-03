#!/usr/bin/env python3
"""
Script para verificar el estado del servidor FFmpeg API.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from transcriber_app.infrastructure.validation.ffmpeg_health_adapter import FfmpegHealthAdapter
from transcriber_app.infrastructure.validation.ffmpeg_api_client import FfmpegApiClient

def check_url(url):
    """Verificar una URL específica"""
    print(f"\n🔍 Probando URL: {url}")
    try:
        api_client = FfmpegApiClient(url)
        health_adapter = FfmpegHealthAdapter(api_client)

        # Verificar salud
        is_healthy, error = health_adapter.check_api_health()
        if not is_healthy:
            print(f"   ❌ No disponible: {error}")
            return False

        print("   ✅ API saludable")

        # Verificar chunked
        chunked_available = health_adapter.check_chunked_endpoint_available()
        print(f"   📦 Chunked disponible: {'✅ Sí' if chunked_available else '❌ No'}")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("🔍 Verificando estado del servidor FFmpeg API...")

    # URLs posibles a probar
    urls_to_try = [
        os.getenv('FFMPEG_API_URL'),  # Variable de entorno
        "http://localhost:8080",      # Puerto estándar
        "http://localhost:8082",      # Puerto que vimos en docker ps
        "http://ffmpeg-api:8080",     # Nombre por defecto
        "http://ffmpeg-api-prod:8080", # Nombre del contenedor
        "http://host.docker.internal:8082", # Desde dentro de contenedor
    ]

    # Filtrar URLs válidas
    urls_to_try = [url for url in urls_to_try if url]

    working_url = None
    for url in urls_to_try:
        if check_url(url):
            working_url = url
            break

    print(f"\n{'='*60}")
    if working_url:
        print(f"✅ ¡ÉXITO! Servidor encontrado en: {working_url}")
        print("Configura esta URL en tu aplicación:")
        print(f"export FFMPEG_API_URL='{working_url}'")
        print("\nO actualiza tu archivo de configuración.")
        print("\n⚠️  NOTA: El endpoint de chunking no está disponible.")
        print("   Los archivos grandes (>25MB) pueden fallar.")
        print("   Verifica que tu servidor FFmpeg soporte chunking.")
    else:
        print("❌ No se pudo conectar a ningún servidor FFmpeg")
        print("\nPosibles soluciones:")
        print("1. Verifica que el contenedor esté corriendo: docker ps")
        print("2. Verifica el puerto correcto: docker port ffmpeg-api-prod")
        print("3. Si estás dentro de un contenedor, usa host.docker.internal")
        print("4. Configura FFMPEG_API_URL manualmente")

if __name__ == "__main__":
    main()