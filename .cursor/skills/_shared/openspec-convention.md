# OpenSpec Convention

OpenSpec define cómo especificar tareas atómicas, APIs y contratos en el sistema Hermes.

## Task Spec

```yaml
task:
  id: "T001"
  name: "Setup inicial"
  description: "..."
  inputs:
    - name: "repo_url"
      type: "string"
      required: true
  outputs:
    - name: "project_scaffold"
      type: "directory"
  dependencies: []
  acceptance_criteria:
    - "El proyecto compila sin errores"
    - "Los tests iniciales pasan"
```

## API Spec

```yaml
api:
  endpoint: "/api/v1/resource"
  method: "GET"
  request:
    query:
      limit: { type: "integer", default: 10 }
  response:
    200:
      body:
        items: { type: "array", items: "Resource" }
```

## Reglas

- Todo spec es YAML parseable.
- Los specs viven en `03-spec/`.
- Los specs son la fuente de verdad para implementation.
