#!/bin/bash
# run-testing.sh — Ejecuta la fase de Testing (TDD)

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

PROJECTS_DIR="${HERMES_PROJECTS_DIR:-/mnt/c/Users/agust/Desktop/projects}"
PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"
TESTS_DIR="$PROJECT_PATH/07-tests"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "❌ Proyecto no encontrado. Ejecutá primero: ./init-project.sh $PROJECT_NAME"
  exit 1
fi

echo "🧪 Ejecutando fase TESTING para '$PROJECT_NAME'"

mkdir -p "$TESTS_DIR"/{unit-tests,integration-tests}

cp "$PROJECT_PATH/templates/test-plan-template.md" "$TESTS_DIR/test-plan.md"

cat > "$TESTS_DIR/unit-tests/__init__.py" <<EOF
# Unit tests
EOF

cat > "$TESTS_DIR/integration-tests/__init__.py" <<EOF
# Integration tests
EOF

cat > "$TESTS_DIR/test-results.md" <<EOF
# Test Results

## Última ejecución: $(date -u +%Y-%m-%dT%H:%M:%SZ)

| Tipo | Total | Pasados | Fallidos | Skipped |
|------|-------|---------|----------|---------|
| Unit | 0 | 0 | 0 | 0 |
| Integration | 0 | 0 | 0 | 0 |

## Cobertura

| Módulo | Cobertura % |
|--------|-------------|
| ... | 0% |

## Notas

- Tests escritos siguiendo TDD
- Framework: pytest
EOF

# Actualizar estado
python3 -c "
import json, datetime
with open('$PROJECT_PATH/.hermes-state/state.json', 'r') as f:
    state = json.load(f)
state['phase'] = 'testing'
state['last_updated'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$PROJECT_PATH/.hermes-state/state.json', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true

echo "✅ Fase TESTING inicializada. Directorio: $TESTS_DIR"
echo "🧪  Escribí los tests en $TESTS_DIR/ (TDD: tests antes o durante implementation)"
