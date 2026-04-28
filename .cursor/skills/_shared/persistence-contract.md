# Persistence Contract

Contrato de persistencia para la Working Memory compartida.

## Ubicación

`workspace/.hermes-state/`

## Archivos obligatorios

- `state.json`: estado global del proyecto
- `messages/`: log de mensajes entre agentes
- `engrams/`: artefactos de memoria

## Formato de state.json

```json
{
  "project": "nombre",
  "phase": "discovery",
  "status": "active",
  "created_at": "2026-04-27T18:00:00Z",
  "last_updated": "2026-04-27T18:00:00Z",
  "agents_active": ["specialist-explorer"],
  "artifacts": [
    { "path": "01-discovery/discovery-document.md", "phase": "discovery" }
  ]
}
```

## Reglas

- Todo agente lee state.json antes de actuar.
- Todo agente actualiza state.json después de actuar.
- Nunca se borra state.json, solo se actualiza.
