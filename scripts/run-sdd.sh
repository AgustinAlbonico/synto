#!/bin/bash
# run-sdd.sh — Orquesta todo el flujo SDD completo

set -euo pipefail

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Uso: $0 <nombre-del-proyecto>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Orquestando flujo SDD completo para '$PROJECT_NAME'"
echo "=============================================="

# 1. Init
$SCRIPT_DIR/init-project.sh "$PROJECT_NAME"
echo ""

# 2. Discovery
$SCRIPT_DIR/run-discovery.sh "$PROJECT_NAME"
echo ""

# 3. Planning
$SCRIPT_DIR/run-planning.sh "$PROJECT_NAME"
echo ""

# 4. Implementation
$SCRIPT_DIR/run-implementation.sh "$PROJECT_NAME"
echo ""

# 5. Testing
$SCRIPT_DIR/run-testing.sh "$PROJECT_NAME"
echo ""

# 6. Deploy
$SCRIPT_DIR/run-deploy.sh "$PROJECT_NAME"
echo ""

echo "=============================================="
echo "🎉 Flujo SDD completado para '$PROJECT_NAME'"
echo ""
echo "Próximos pasos:"
echo "  1. Completá los artefactos en cada fase"
echo "  2. Ejecutá los tests: pytest 07-tests/"
echo "  3. Seguí la guía de deploy en 08-deploy/"
