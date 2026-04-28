#!/bin/bash
# Ejemplo: Agregar autenticación JWT al sistema odontológico

cd /home/agust/hermes-orchestrator
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

echo "🚀 Ejemplo: Feature de autenticación JWT"
echo ""
echo "Este ejemplo muestra cómo se activa el flujo completo SDD:"
echo "   HermesOrchestrator -> CodeOrchestrator -> Planner -> Implementer -> Tester -> Reviewer"
echo ""
echo "En la práctica, ejecutarías desde Python:"
echo ""
cat << 'PYEOF'
import asyncio
from hermes_agency import agency, hermes_orchestrator

async def main():
    # Fase 1: Discovery (HermesOrchestrator te hace preguntas)
    response = await agency.get_response(
        message="Quiero agregar autenticación JWT al sistema odontológico",
        recipient_agent=hermes_orchestrator
    )
    print(response)
    
    # Fase 2-3: Planning (CodeOrchestrator crea PRD + Spec)
    # Fase 4: TDD (Tester escribe tests)
    # Fase 5: Implementation (Implementer usa OpenCode)
    # Fase 6: Review (Reviewer revisa)
    # Fase 7: Deploy (DevOpsOrchestrator)

asyncio.run(main())
PYEOF
