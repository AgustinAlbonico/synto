# Configuración de Agentes

## Variables de entorno

```bash
# Directorio base del orquestador
export HERMES_ORCHESTRATOR_HOME=/home/agust/synto

# Directorio de proyectos
export HERMES_PROJECTS_DIR=/mnt/c/Users/agust/Desktop/projects

# Modelo LLM por defecto
export HERMES_LLM_MODEL=gpt-4o

# API Key (si aplica)
export HERMES_API_KEY=""

# Nivel de log: DEBUG, INFO, WARN, ERROR
export HERMES_LOG_LEVEL=INFO

# Modo dry-run (no ejecuta, solo planifica)
export HERMES_DRY_RUN=false
```

## Configuración por agente

### Orchestrator Main
- Prompt: `agents/prompts/orchestrator-main.md`
- Responsabilidad: Enrutar al dominio correcto
- Variables: `HERMES_DEFAULT_DOMAIN=code`

### Orchestrator Code
- Prompt: `agents/prompts/orchestrator-code.md`
- Responsabilidad: Gestionar proyectos de software
- Specialists por defecto: planner, explorer, architect, implementer, reviewer, tester

### Specialist Tester (TDD)
- Prompt: `agents/prompts/specialist-tester.md`
- Modo obligatorio: escribir tests ANTES del código
- Frameworks soportados: pytest, unittest, jest, vitest

## Cómo agregar un nuevo specialist

1. Crear el prompt en `agents/prompts/specialist-<nombre>.md`
2. Registrarlo en `agents/protocols/message-protocol.md`
3. Actualizar el orchestrator que lo usa
4. Agregar su fase en los scripts correspondientes

## Skills de Cursor

Para usar los skills en Cursor:
1. Copiar `.cursor/skills/` al proyecto de Cursor
2. Usar `@skill <nombre>` en el chat
3. Ejemplo: `@skill sdd-explore`

## Customización de templates

Los templates viven en `agents/templates/`:
- `prd-template.md` → Product Requirements Document
- `discovery-template.md` → Discovery Document
- `spec-template.md` → Technical Specification
- `test-plan-template.md` → Test Plan (TDD)

Podés sobreescribirlos por proyecto copiándolos a `<proyecto>/templates/`.
