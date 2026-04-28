#!/bin/bash
# init-project.sh — Inicializa un nuevo proyecto con estructura SDD

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"

if [[ -d "$PROJECT_PATH" ]]; then
  echo "⚠️  El proyecto '$PROJECT_NAME' ya existe en $PROJECT_PATH"
  read -p "¿Sobreescribir estructura? (s/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 0
  fi
fi

echo "🚀 Inicializando proyecto SDD: $PROJECT_NAME"

mkdir -p "$PROJECT_PATH"/{01-discovery,02-prd,03-spec,04-design,05-tasks,06-implementation,07-tests,08-deploy,templates}

# Copiar templates
cp /home/agust/hermes-orchestrator/agents/templates/*.md "$PROJECT_PATH/templates/" 2>/dev/null || true

# Crear README del proyecto
cat > "$PROJECT_PATH/README.md" <<EOF
# $PROJECT_NAME

Proyecto gestionado con flujo SDD (Structured Design & Development).

## Fases

- 01-discovery/ — Investigación y descubrimiento
- 02-prd/ — Product Requirements Document
- 03-spec/ — Especificación técnica
- 04-design/ — Diseño y arquitectura
- 05-tasks/ — Plan de tareas
- 06-implementation/ — Código fuente
- 07-tests/ — Tests y resultados
- 08-deploy/ — Guía de despliegue

## Estado

| Fase | Estado |
|------|--------|
| Discovery | 🔲 Pendiente |
| PRD | 🔲 Pendiente |
| Spec | 🔲 Pendiente |
| Design | 🔲 Pendiente |
| Tasks | 🔲 Pendiente |
| Implementation | 🔲 Pendiente |
| Tests | 🔲 Pendiente |
| Deploy | 🔲 Pendiente |
EOF

# Crear state inicial
mkdir -p "$PROJECT_PATH/.hermes-state"
cat > "$PROJECT_PATH/.hermes-state/state.json" <<EOF
{
  "project": "$PROJECT_NAME",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "phase": "init",
  "status": "active"
}
EOF

echo "✅ Proyecto inicializado en: $PROJECT_PATH"
echo "📋  Templates copiados a: $PROJECT_PATH/templates/"
