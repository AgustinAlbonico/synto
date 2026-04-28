#!/bin/bash
# Ejecutar la Agencia Hermes

set -e

cd /home/agust/hermes-orchestrator
source .venv/bin/activate

# Cargar .env
export $(grep -v '^#' .env | xargs)

echo "🤖 Iniciando Agencia Hermes..."
python3.12 hermes_agency.py
