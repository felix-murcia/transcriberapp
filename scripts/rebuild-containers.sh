#!/bin/bash
# Script para reconstruir contenedores con los cambios de arquitectura hexagonal

echo "🔄 Reconstruyendo contenedores con arquitectura hexagonal..."

# Detener contenedores existentes
echo "🛑 Deteniendo contenedores existentes..."
docker-compose down

# Limpiar imágenes y contenedores no utilizados (opcional)
echo "🧹 Limpiando contenedores e imágenes no utilizados..."
docker system prune -f

# Reconstruir imagen de la aplicación
echo "🏗️ Reconstruyendo imagen de la aplicación..."
docker-compose build --no-cache app

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker-compose up -d

# Verificar que los servicios estén corriendo
echo "✅ Verificando servicios..."
sleep 5
docker-compose ps

echo ""
echo "🎯 Arquitectura hexagonal aplicada correctamente!"
echo "📋 Cambios incluidos:"
echo "  - ✅ Eliminación del directorio transcriber_app/modules/"
echo "  - ✅ Puertos del dominio definidos correctamente"
echo "  - ✅ Adaptadores implementando puertos en infrastructure/"
echo "  - ✅ Endpoint chunked verificado antes de uso"
echo "  - ✅ Manejo robusto de errores en FFmpeg API"
echo ""
echo "🌐 La aplicación debería estar disponible en: http://localhost:9000"