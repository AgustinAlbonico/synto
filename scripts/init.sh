#!/bin/bash
# Script de inicialización del Sistema Hermes Orquestado

set -e

echo "🤖 Inicializando Sistema Hermes Orquestado..."
echo ""

# 1. Verificar Python 3.12
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Error: Python 3.12 no encontrado. Instalalo primero."
    exit 1
fi
echo "✅ Python 3.12 encontrado"

# 2. Verificar virtual environment
VENV_DIR="/home/agust/hermes-orchestrator/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creando virtual environment..."
    python3.12 -m venv "$VENV_DIR"
fi
echo "✅ Virtual environment listo"

# 3. Activar e instalar dependencias
source "$VENV_DIR/bin/activate"
echo "🔧 Instalando dependencias..."
pip install -q --upgrade pip agency-swarm pydantic langfuse python-dotenv

# 4. Verificar OpenCode
if ! command -v opencode &> /dev/null; then
    echo "⚠️  OpenCode no encontrado. Instalalo con: npm install -g opencode"
else
    echo "✅ OpenCode encontrado"
fi

# 5. Verificar .env
ENV_FILE="/home/agust/hermes-orchestrator/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Archivo .env no encontrado. Creando plantilla..."
    cat > "$ENV_FILE" << 'EOF'
# Configuración del Sistema Hermes Orquestado

# ⚠️  IMPORTANTE: Configurá tu API key antes de usar
# Registrate gratis en https://openrouter.ai/keys
# Después copiá tu key acá:
OPENROUTER_API_KEY=tu-api-key-aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenCode (debe estar instalado en el sistema)
OPENCODE_CMD=opencode

# Working Memory
HERMES_STATE_DIR=/home/agust/hermes-orchestrator/workspace/.hermes-state

# Modo debug
DEBUG=false
EOF
fi

# 6. Verificar que la key esté configurada
if grep -q "tu-api-key-aqui" "$ENV_FILE"; then
    echo ""
    echo "⚠️  ATENCIÓN: Todavía no configuraste tu OPENROUTER_API_KEY"
    echo "   1. Andá a https://openrouter.ai/keys"
    echo "   2. Creá una API key (es gratis)"
    echo "   3. Editá el archivo .env y reemplazá 'tu-api-key-aqui'"
    echo ""
fi

# 7. Crear estructura de working memory
mkdir -p /home/agust/hermes-orchestrator/workspace/.hermes-state/projects

echo ""
echo "✅ Sistema Hermes Orquestado inicializado correctamente!"
echo ""
echo "📚 Para usar:"
echo "   cd /home/agust/hermes-orchestrator"
echo "   source .venv/bin/activate"
echo "   python3.12 hermes_agency.py"
echo ""
