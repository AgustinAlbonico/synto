#!/bin/bash
# run-deploy.sh — Ejecuta la fase de Deploy

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"
DEPLOY_DIR="$PROJECT_PATH/08-deploy"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Proyecto no encontrado. Ejecutá primero: ./init-project.sh $PROJECT_NAME"
  exit 1
fi

echo "🚀 Ejecutando fase DEPLOY para '$PROJECT_NAME'"

mkdir -p "$DEPLOY_DIR"

cat > "$DEPLOY_DIR/deployment-guide.md" <<EOF
# Guía de Despliegue

## Pre-requisitos

- [ ] Variables de entorno configuradas
- [ ] Dependencias instaladas
- [ ] Tests pasando

## Pasos

### 1. Build
\`\`\`bash
# Comandos de build
\`\`\`

### 2. Deploy a staging
\`\`\`bash
# Comandos de deploy staging
\`\`\`

### 3. Validación en staging
- [ ] Smoke tests pasan
- [ ] No hay errores en logs

### 4. Deploy a producción
\`\`\`bash
# Comandos de deploy prod
\`\`\`

### 5. Post-deploy
- [ ] Monitoreo activo
- [ ] Rollback plan listo

## Rollback

\`\`\`bash
# Comandos de rollback
\`\`\`

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| ... | ... | ... |
EOF

cat > "$DEPLOY_DIR/release-notes.md" <<EOF
# Release Notes

## Versión 1.0.0 — $(date +%Y-%m-%d)

### Nuevas funcionalidades
- ...

### Mejoras
- ...

### Bug fixes
- ...

### Dependencias
- ...

### Notas para ops
- ...
EOF

# Actualizar estado
python3 -c "
import json, datetime
with open('$PROJECT_PATH/.hermes-state/state.json', 'r') as f:
    state = json.load(f)
state['phase'] = 'deploy'
state['last_updated'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$PROJECT_PATH/.hermes-state/state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

echo "✅ Fase DEPLOY completada. Artefactos en: $DEPLOY_DIR"
