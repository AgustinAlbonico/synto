# Engram Convention

Los Engrams son artefactos de memoria persistente que los agentes usan para recordar decisiones, contexto y estado entre sesiones.

## Formato

```yaml
engram:
  id: "engram-uuid"
  type: "decision|context|state|artifact"
  project: "nombre-del-proyecto"
  created_at: "2026-04-27T18:00:00Z"
  updated_at: "2026-04-27T18:00:00Z"
  tags: ["sdd", "planning", "architecture"]
  content: |
    Contenido del engram en markdown
```

## Reglas

- Todo engram tiene un ID único.
- Los engrams se almacenan en `workspace/.hermes-state/engrams/`.
- Los agentes leen engrams relevantes antes de actuar.
- Los agentes escriben engrams después de tomar decisiones.
