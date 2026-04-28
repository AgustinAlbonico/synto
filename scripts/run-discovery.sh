#!/bin/bash
# run-discovery.sh — Ejecuta la fase de Discovery

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"
DISCOVERY_DIR="$PROJECT_PATH/01-discovery"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Proyecto no encontrado. Ejecutá primero: ./init-project.sh $PROJECT_NAME"
  exit 1
fi

echo "🔍 Ejecutando fase DISCOVERY para '$PROJECT_NAME'"

mkdir -p "$DISCOVERY_DIR"

# Crear artefactos de discovery basados en el template
cp "$PROJECT_PATH/templates/discovery-template.md" "$DISCOVERY_DIR/discovery-document.md"

cat > "$DISCOVERY_DIR/user-personas.md" <<EOF
# User Personas

## Persona 1: Usuario Principal
- **Nombre**: ...
- **Rol**: ...
- **Objetivos**: ...
- **Frustraciones**: ...
EOF

cat > "$DISCOVERY_DIR/tech-constraints.md" <<EOF
# Restricciones Técnicas

- Stack sugerido: ...
- Limitaciones: ...
- Requisitos de compliance: ...
EOF

# Actualizar estado
python3 -c "
import json, datetime
with open('$PROJECT_PATH/.hermes-state/state.json', 'r') as f:
    state = json.load(f)
state['phase'] = 'discovery'
state['last_updated'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$PROJECT_PATH/.hermes-state/state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

echo "✅ Fase DISCOVERY completada. Artefactos en: $DISCOVERY_DIR"
echo "📝  Editá los archivos para completar la investigación."
