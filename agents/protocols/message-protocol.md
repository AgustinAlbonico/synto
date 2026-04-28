# Protocolo de Mensajes entre Agentes

## Formato base

Todo mensaje entre agentes es un objeto JSON con la siguiente estructura:

```json
{
  "version": "1.0.0",
  "message_id": "uuid-v4",
  "timestamp": "2026-04-27T18:00:00Z",
  "from": "agent-id",
  "to": "agent-id",
  "type": "task",
  "payload": {},
  "metadata": {}
}
```

## Campos obligatorios

| Campo | Tipo | Descripción |
|-------|------|-------------|
| version | string | Versión del protocolo (siempre "1.0.0") |
| message_id | string | UUID v4 único |
| timestamp | string | ISO 8601 UTC |
| from | string | ID del agente emisor |
| to | string | ID del agente receptor |
| type | string | Tipo de mensaje (ver abajo) |
| payload | object | Contenido específico del mensaje |
| metadata | object | Contexto adicional |

## Tipos de mensaje

### 1. task
Delega una tarea a otro agente.

```json
{
  "type": "task",
  "payload": {
    "task_id": "t-123",
    "phase": "discovery",
    "description": "Investigar tecnologías para landing page",
    "inputs": {
      "discovery_doc": "path/to/doc.md"
    },
    "expected_outputs": ["tech-research.md", "risk-analysis.md"],
    "deadline": "2026-04-28T18:00:00Z"
  },
  "metadata": {
    "project": "landing-python",
    "priority": "high"
  }
}
```

### 2. review
Pide revisión de un artefacto.

```json
{
  "type": "review",
  "payload": {
    "artifact_path": "02-prd/prd.md",
    "artifact_type": "prd",
    "checklist": [
      "Tiene objetivo claro",
      "Tiene criterios de aceptación",
      "Tiene restricciones"
    ]
  },
  "metadata": {
    "project": "landing-python"
  }
}
```

### 3. question
Pregunta o pide clarificación.

```json
{
  "type": "question",
  "payload": {
    "question": "¿Qué framework CSS preferís?",
    "options": ["Bootstrap", "Tailwind", "Bulma"],
    "blocking": true
  },
  "metadata": {
    "phase": "planning"
  }
}
```

### 4. result
Entrega resultado de una tarea.

```json
{
  "type": "result",
  "payload": {
    "task_id": "t-123",
    "status": "completed",
    "artifacts": [
      {
        "path": "01-discovery/tech-research.md",
        "type": "markdown"
      }
    ],
    "summary": "Se compararon 3 frameworks. Recomendación: Tailwind.",
    "next_steps": ["Definir arquitectura"]
  },
  "metadata": {
    "duration_seconds": 120
  }
}
```

### 5. error
Reporta un error o bloqueo.

```json
{
  "type": "error",
  "payload": {
    "task_id": "t-123",
    "severity": "critical",
    "code": "DEPENDENCY_NOT_FOUND",
    "message": "No se encontró la dependencia flask en el entorno",
    "stack_trace": "...",
    "suggested_fix": "Instalar flask con pip install flask"
  },
  "metadata": {
    "phase": "implementation"
  }
}
```

## Reglas de routing

```
Usuario → Orchestrator Main
Orchestrator Main → Orchestrator Domain
Orchestrator Domain → Specialist
Specialist → Orchestrator Domain
Orchestrator Domain → Orchestrator Main
Orchestrator Main → Usuario
```

### Reglas
1. Ningún specialist habla directamente con el usuario.
2. Los cross-cutting agents pueden recibir mensajes de cualquier agente.
3. Todos los mensajes se loguean en `workspace/.hermes-state/messages/`.
4. Un mensaje `error` con `severity: critical` detiene el flujo hasta resolución.

## IDs de agentes

```
orchestrator-main
orchestrator-code
orchestrator-research
orchestrator-content
orchestrator-devops
orchestrator-data
specialist-planner
specialist-explorer
specialist-implementer
specialist-reviewer
specialist-tester
specialist-architect
specialist-builder
specialist-validator
specialist-sourcer
specialist-analyst
specialist-synthesizer
specialist-strategist
specialist-writer
specialist-editor
specialist-seo
cross-security
cross-documentation
cross-qa-gatekeeper
cross-dependency-checker
cross-context-manager
```
