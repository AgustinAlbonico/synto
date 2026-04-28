#!/bin/bash
# run-planning.sh — Ejecuta la fase de Planning (PRD + Spec + Design)

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Proyecto no encontrado. Ejecutá primero: ./init-project.sh $PROJECT_NAME"
  exit 1
fi

if [[ ! -f "$PROJECT_PATH/01-discovery/discovery-document.md" ]]; then
  echo "⚠️  No se encontró el Discovery Document. Ejecutá primero: ./run-discovery.sh $PROJECT_NAME"
  exit 1
fi

echo "📋 Ejecutando fase PLANNING para '$PROJECT_NAME'"

# PRD
mkdir -p "$PROJECT_PATH/02-prd"
cp "$PROJECT_PATH/templates/prd-template.md" "$PROJECT_PATH/02-prd/prd.md"

# Spec
mkdir -p "$PROJECT_PATH/03-spec"
cp "$PROJECT_PATH/templates/spec-template.md" "$PROJECT_PATH/03-spec/specification.md"
cat > "$PROJECT_PATH/03-spec/task-breakdown.md" <<EOF
# Task Breakdown

Basado en el PRD y la especificación técnica.

## Tasks

### T001: Setup inicial
- **Descripción**: Configurar proyecto, dependencias, estructura de carpetas
- **Dependencias**: ninguna
- **Estimación**: S
- **Estado**: 🔲 Pendiente

### T002: Feature core
- **Descripción**: Implementar funcionalidad principal
- **Dependencias**: T001
- **Estimación**: M
- **Estado**: 🔲 Pendiente

### T003: Feature secundaria
- **Descripción**: Implementar funcionalidad secundaria
- **Dependencias**: T002
- **Estimación**: S
- **Estado**: 🔲 Pendiente

### T004: Testing
- **Descripción**: Escribir y ejecutar todos los tests
- **Dependencias**: T002, T003
- **Estimación**: M
- **Estado**: 🔲 Pendiente

## Diagrama de dependencias

```
T001 → T002 → T003
         ↓
        T004
```
EOF

# Design
mkdir -p "$PROJECT_PATH/04-design"
cat > "$PROJECT_PATH/04-design/architecture.md" <<EOF
# Architecture

## Diagrama de componentes

```
[Usuario] → [Web/App] → [API] → [Base de Datos]
```

## Decisiones
- Framework: ...
- Base de datos: ...
- Hosting: ...
EOF

cat > "$PROJECT_PATH/04-design/data-model.md" <<EOF
# Data Model

## Entidades

### Entidad 1
- id: UUID (PK)
- created_at: timestamp
- updated_at: timestamp

## Relaciones
- Entidad 1 1:N Entidad 2
EOF

# Actualizar estado
python3 -c "
import json, datetime
with open('$PROJECT_PATH/.hermes-state/state.json', 'r') as f:
    state = json.load(f)
state['phase'] = 'planning'
state['last_updated'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$PROJECT_PATH/.hermes-state/state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

echo "✅ Fase PLANNING completada. Artefactos en:"
echo "   - $PROJECT_PATH/02-prd/"
echo "   - $PROJECT_PATH/03-spec/"
echo "   - $PROJECT_PATH/04-design/"
