#!/bin/bash
# run-implementation.sh — Ejecuta la fase de Implementation

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"
IMPL_DIR="$PROJECT_PATH/06-implementation"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Proyecto no encontrado. Ejecutá primero: ./init-project.sh $PROJECT_NAME"
  exit 1
fi

if [[ ! -f "$PROJECT_PATH/02-prd/prd.md" ]]; then
  echo "⚠️  No se encontró el PRD. Ejecutá primero: ./run-planning.sh $PROJECT_NAME"
  exit 1
fi

echo "🚀 Ejecutando fase IMPLEMENTATION para '$PROJECT_NAME'"

mkdir -p "$IMPL_DIR"

cat > "$IMPL_DIR/README.md" <<EOF
# Implementation

Código fuente del proyecto $PROJECT_NAME.

## Estructura

```
src/
├── main.py          # Entry point
├── config.py        # Configuración
├── models/          # Modelos de datos
├── services/        # Lógica de negocio
└── utils/           # Utilidades
```

## Cómo correrlo localmente

```bash
pip install -r requirements.txt
python src/main.py
```
EOF

mkdir -p "$IMPL_DIR/src"
touch "$IMPL_DIR/src/__init__.py"

# Actualizar estado
python3 -c "
import json, datetime
with open('$PROJECT_PATH/.hermes-state/state.json', 'r') as f:
    state = json.load(f)
state['phase'] = 'implementation'
state['last_updated'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$PROJECT_PATH/.hermes-state/state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

echo "✅ Fase IMPLEMENTATION inicializada. Directorio: $IMPL_DIR"
echo "📝  Escribí el código en $IMPL_DIR/src/"
