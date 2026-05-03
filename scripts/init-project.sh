#!/usr/bin/env bash
set -e

echo "🔗 Enlazando estándares desde submodule..."

# 1. Enlazar reglas del agente (Cursor/Copilot)
ln -sf ../standards/.cursorrules .cursorrules
ln -sf ../standards/.github/copilot-instructions.md .github/copilot-instructions.md 2>/dev/null || true

# 2. Enlazar script de validación
ln -sf ../standards/scripts/validate-standards.sh scripts/validate-standards.sh
chmod +x scripts/validate-standards.sh

# 3. Copiar configuración MCP (porque requiere variables locales)
cp standards/mcp-configs/github/.mcp.json .mcp.json

echo "✅ Proyecto inicializado. Ejecuta './scripts/validate-standards.sh' para verificar."