# Synto — Guía de Uso

> Sistema de orquestación multi-agente con memoria persistente, skills dinámicas y runtime LangGraph.
> Este documento se actualiza a medida que se implementan nuevas funcionalidades.

---

## Índice

1. [Instalación y setup](#1-instalación-y-setup)
2. [Arquitectura general](#2-arquitectura-general)
3. [CLI básica](#3-cli-básica)
4. [Command Center web](#4-command-center-web)
5. [Agents y skills](#5-agents-y-skills)
6. [SharedState / Blackboard](#6-sharedstate--blackboard)
7. [PersistentMemory](#7-persistentmemory)
8. [MCP Servers](#8-mcp-servers)
9. [Ciclo de desarrollo con Synto](#9-ciclo-de-desarrollo-con-synto)
10. [Configuración de modelos LLM](#10-configuración-de-modelos-llm)
11. [FAQ y problemas comunes](#11-faq-y-problemas-comunes)

---

## 1. Instalación y setup

### Requisitos previos

- Python 3.11+
- Poetry o pip
- Git
- (Opcional) Docker Desktop para features de infra

### Instalación local

```bash
cd ~/hermes-orchestrator
poetry install
# o
pip install -e .
```

### Activación del virtualenv

```bash
poetry shell
# o
source .venv/bin/activate
```

### Verificación

```bash
synto --help
synto web --help
```

---

## 2. Arquitectura general

Synto opera como un **orquestador de agentes** que sigue este flujo:

```
User Input / Task
       │
       ▼
  Intake Agent
       │
       ▼
  Discovery → PRD approval
       │
       ▼
  Technical Planning (paralelo)
       │
       ▼
  Spec / Design consolidation
       │
       ▼
  TDD / Test Plan
       │
       ▼
  Implementation (Backend + Frontend en paralelo)
       │
       ▼
  Contract alignment + Review + Security + Tests
       │
       ▼
  QA + Dependency check + Docs
       │
       ▼
  Release / PR / Deploy
       │
       ▼
  Delivery
```

### Pilares de la arquitectura

| Pilar | Para qué |
|---|---|
| **LangGraph** | Runtime de orquestación. Define nodos (agentes) y aristas (transiciones). |
| **SharedState** | Blackboard compartido. Cada agente escribe en su slot; los orquestadores escriben artefactos canónicos. |
| **PersistentMemory** | Memoria cross-session. Recupera contexto pasado y rehidrata cada run automáticamente. |
| **SkillLoader** | Carga skills dinámicamente por agente, por fase y por contexto. No carga todo siempre. |
| **MCP** | Protocolo agent-to-tool. Cada agente tiene tools разрешенные via `AGENT-REGISTRY.yaml`. |

---

## 3. CLI básica

### Help general

```bash
synto --help
```

### Levantar el Command Center web

```bash
synto web --port 8787
# Abrir http://127.0.0.1:8787
```

### Llamar a la API directamente

```bash
# Health check
curl http://127.0.0.1:8787/api/health

# Listar runs
curl http://127.0.0.1:8787/api/runs

# Ver un run específico
curl http://127.0.0.1:8787/api/runs/<run_id>

# Reanudar un run pausado
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/resume

# Ver eventos de un run
curl http://127.0.0.1:8787/api/runs/<run_id>/events

# Listar agentes
curl http://127.0.0.1:8787/api/agents

# Listar skills disponibles
curl http://127.0.0.1:8787/api/skills

# Buscar en memoria
curl "http://127.0.0.1:8787/api/memory/search?q=autenticacion"

# Ver candidatos de memoria
curl http://127.0.0.1:8787/api/memory/candidates
```

---

## 4. Command Center web

Interfaz local disponible en `http://127.0.0.1:8787`.

### Secciones

- **Dashboard** — resumen de runs activos y recientes.
- **Runs** — lanzar, pausar, retomar y ver el detalle de cada workflow.
- **Agents** — visualiza el equipo de agentes definido en `AGENT-REGISTRY.yaml`.
- **Skills** — explora y gestiona skills disponibles.
- **Memory** — busca y revisa candidatos de memoria.
- **Design System** — herramientas de diseño token-driven (fase inicial).
- **Gates** — centro de aprobación para gates críticos del workflow.

### Detail de un run

Al hacer click en un run se ve:

- Timeline de eventos
- Estado del SharedState
- Artefactos generados
- Eventos de skill loading
- Capacidad de retomar / APPROVE / REJECT en gates

---

## 5. Agents y Skills

### Registro de agentes

El contrato vivo de los agentes está en:

```
AGENT-REGISTRY.yaml
```

Define por agente:

- `role` y `responsibilities`
- `restrictions` (qué NO debe hacer)
- `base_skills.required` y `base_skills.optional`
- `dynamic_skill_policy` (tags permitidos / denegados)
- `allowed_mcp_tools`
- `inputs` y `outputs` (slots del SharedState)

### Agregar una skill nueva

1. Crear el archivo con el naming correcto:

   ```
   ~/.hermes/skills/<nombre-de-skill>/SKILL.md
   ```

2. Definir el frontmatter:

   ```yaml
   ---
   name: nombre-de-skill
   description: Qué hace esta skill
   category: devops  # o: data-science, mlops, productivity, etc.
   tags: [docker, deploy, backend]   # tags que la clasifican
   triggers:
     keywords: [deploy, docker, container]
     phases: [release, deploy]
     file_globs: ["Dockerfile", "docker-compose*"]
   allowed_agents: [Builder, ReleaseManager]  # opcional:限定 a ciertos agentes
   ---
   ```

3. La skill se descubre automáticamente en el próximo scan.

4. (Opcional) Asignarla explícitamente a un agente en `config/agent-skill-map.yaml`:

   ```yaml
   overrides:
     ReleaseManager:
       manual:
         - nombre-de-skill
   ```

### Sistema de tags

| Tag | Qué incluye |
|---|---|
| `python` | Python, pytest, fastapi, etc. |
| `typescript` | TypeScript, React, Node.js |
| `docker` | Docker, docker-compose, containers |
| `git` | Git, GitHub, PRs, branches |
| `bash` | Shell scripting, CLI |
| `testing` | pytest, unittest, coverage |
| `security` | Security review, hardening |
| `docs` | Documentación, READMEs |
| `refactor` | Refactoring, code quality |
| `debug` | Debugging, troubleshooting |
| `deploy` | Deployment, CI/CD |
| `infra` | Infrastructure, Terraform, k8s |
| `data-science` | Análisis de datos, Jupyter |
| `mlops` | ML pipelines, training, serving |
| `design` | Diseño, UI/UX, tokens |
| `database` | SQL, PostgreSQL, migrations |
| `api` | APIs REST/GraphQL, endpoints |

### SkillLoader — cómo funciona internamente

```
AgentRuntime._invoke_agent()
       │
       ▼
SkillLoader.resolve(agent, state)
       │
       ├── Busca base_skills del agente en AGENT-REGISTRY.yaml
       ├── Aplica overrides de config/agent-skill-map.yaml
       ├── Filtra por dynamic_skill_policy (tags)
       ├── Evalúa triggers (keywords, phase, regex, file_globs)
       ├── Verifica allowed_agents (si la skill lo especifica)
       ├── Verifica presupuesto máximo de skills
       ├── Quarantine check
       │
       ▼
  Lista de skills seleccionadas
       │
       ▼
  Carga lazy del contenido (solo metadata → contenido completo)
       │
       ▼
  Inyección en system prompt bajo "--- Loaded Skills ---"
       │
       ▼
  Registro en state/skill-load-events.jsonl
```

### Ver events de skill loading de un run

```bash
curl http://127.0.0.1:8787/api/runs/<run_id>/skill-events
```

O desde el archivo directamente:

```bash
cat state/skill-load-events.jsonl
```

---

## 6. SharedState / Blackboard

### Concepto

SharedState es el "pizarrón" compartido donde los agentes escriben durante un run.

### Regla central

> **Workers** escriben en su slot. **Orquestadores/Consolidadores** escriben artefactos canónicos.

### Slots por agente

Cada agente tiene slots de escritura definidos en `AGENT-REGISTRY.yaml`. Ejemplo:

```yaml
outputs:
  - slot: prd_draft
    artifact: prd
    phase: discovery
  - slot: spec_md
    artifact: spec
    phase: design
```

### Gates

Los gates son puntos de aprobación manual en el workflow. Se definen en el grafo de LangGraph y pausan el flujo hasta que un humano apruebe o rechace.

```python
# Ejemplo conceptual de un gate
if node == "prd_approval":
    state["gate_pending"] = "prd"
    return state  # pausa hasta POST /api/runs/{id}/resume
```

Para aprobar/rechazar desde la API:

```bash
# Aprobar
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/resume \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "gate": "prd"}'

# Rechazar
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/resume \
  -H "Content-Type: application/json" \
  -d '{"action": "reject", "gate": "prd", "reason": "falta incluir caso X"}'
```

---

## 7. PersistentMemory

### Objetivo

- Recordar contexto entre sesiones.
- Rehidratar runs automáticamente con memoria relevante.
- Guardar decisiones, preferencias, resúmenes de artefactos.
- Evitar que los agentes repitan errores o contradigan decisiones pasadas.

### Cómo funciona

```
MemoryStore (SQLite + FTS5)
      │
      ├── Project → Feature → Topic (árbol)
      ├── Relations (grafo liviano)
      └── Embeddings (opcional)

      │
      ▼
Memory MCP Server (tool layer)
      │
      ▼
MemoryContextAgent (armador de memory packs)
      │
      ▼
Agentes reciben solo el pack relevante
```

### Agregar un hecho a la memoria

Desde un agente, se escribe en SharedState → MemoryManager consolida → Persiste en SQLite.

Manualmente (vía API):

```bash
# Buscar en memoria
curl "http://127.0.0.1:8787/api/memory/search?q=autenticacion%20JWT"

# Ver candidatos
curl http://127.0.0.1:8787/api/memory/candidates
```

### Arquitectura de memoria (detalle)

- **Fuente canónica**: SQLite con FTS5.
- **Espejo humano-readable**: Export a Obsidian vault.
- **Sin embeddings por defecto**: Solo FTS5 con keywords.
- **Embeddings opcionales**: Activables por config.
- **Control anti-compactación**: MemoryContextAgent arma packs chicos; no se carga toda la historia.

### Memoria cross-session

Losmemory packs se rehidratan en cada nuevo run automáticamente. El agente recibe contexto relevante sin tener que preguntar todo de nuevo.

---

## 8. MCP Servers

### Qué es MCP

MCP (Model Context Protocol) es el protocolo por el cual los agentes acceden a tools externas.

### Configuración de tools por agente

En `AGENT-REGISTRY.yaml`:

```yaml
allowed_mcp_tools:
  - github
  - filesystem
  - web
  - searxng
```

### MCP servers disponibles

Los MCP servers se configuran en `config.yaml` o en la config del proyecto. Cada skill puede declarar qué MCP necesita.

### Agregar un MCP server

1. Instalar el servidor MCP del provider (ej: `npm install -g @modelcontextprotocol/server-github`).
2. Agregar la configuración al `config.yaml` de Synto.
3. Reiniciar el servicio.

---

## 9. Ciclo de desarrollo con Synto

### Flujo recomendado para un proyecto nuevo

```bash
# 1. Iniciar el Command Center
synto web --port 8787

# 2. Abrir http://127.0.0.1:8787

# 3. Crear un nuevo run desde el dashboard
#    - Ingresar: nombre del proyecto, descripción, repo URL

# 4. Synto ejecuta:
#    Intake → Discovery → PRD draft
#    El workflow se pausa en el gate de PRD para aprobación humana

# 5. Aprobar o rechazar el PRD desde la UI o la API

# 6. Synto continúa:
#    Technical Planning (paralelo) → Spec consolidation
#    → TDD / Test Plan
#    → Implementation (Backend + Frontend)

# 7. En cada gate, aprobar/rechazar

# 8. Al finalizar, Synto genera:
#    - PR link
#    - Docs
#    - Resumen del run
#    - Memoria consolidada
```

### Desde la CLI (sin UI)

```bash
# Lanzar un run nuevo
curl -X POST http://127.0.0.1:8787/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "mi-proyecto",
    "description": "Sistema de turnos médicos",
    "repo_url": "https://github.com/miusuario/mi-proyecto"
  }'

# Monitorear
curl http://127.0.0.1:8787/api/runs | jq
```

---

## 10. Configuración de modelos LLM

### Modelos soportados

Synto usa OpenCode Zen como provider principal y OpenRouter como fallback.

```yaml
# En config.yaml
llm:
  provider: opencode
  model: opencode/zen
  api_key: ${OPENCODE_API_KEY}

  fallback:
    provider: openrouter
    model: openrouter/anthropic/claude-sonnet-4
    api_key: ${OPENROUTER_API_KEY}
```

### Variables de entorno

```bash
export OPENCODE_API_KEY=sk-...
export OPENROUTER_API_KEY=sk-or-...
```

### Cambiar el modelo por defecto

```bash
synto config set llm.model openrouter/anthropic/claude-sonnet-4
```

---

## 11. FAQ y problemas comunes

### "synto: command not found"

```bash
# Verificar que está instalado
pip show synto

# Instalar si no
pip install -e ~/hermes-orchestrator

# O ejecutar directamente
python -m synto.cli --help
```

### "Docker Desktop no está corriendo"

Synto requiere Docker Desktop para features de infraestructura. Arrancarlo desde la aplicación o:

```bash
# En Windows (PowerShell)
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Verificar
docker ps
```

### "No me carga las skills"

1. Verificar que la skill tiene el `SKILL.md` con el frontmatter correcto.
2. Verificar que la categoría está en las tags o en `category`.
3. Correr el scanner a mano:

```bash
python -c "from synto.registry import SkillRegistry; sr = SkillRegistry(); sr.scan(); print(sr.list())"
```

### "El run quedó pausado en un gate"

```bash
# Reanudar
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/resume

# Aprobar gate específico
curl -X POST http://127.0.0.1:8787/api/runs/<run_id>/resume \
  -d '{"action": "approve", "gate": "prd"}'
```

### "La memoria no recupera contexto"

1. Verificar que existe state en SQLite:
```bash
ls -la state/*.db
```

2. Buscar hechos relevantes:
```bash
curl "http://127.0.0.1:8787/api/memory/search?q=mi-proyecto"
```

### "Los tests fallan"

```bash
cd ~/hermes-orchestrator
poetry run pytest -v
```

### "Quiero agregar un agente nuevo"

1. Agregar la definición en `AGENT-REGISTRY.yaml`.
2. Definir sus slots, skills, tools y restricciones.
3. (Opcional) Asignar skills dinámicas en `config/agent-skill-map.yaml`.

---

## Próximos pasos

Funcionalidades que se van agregando:

- [ ] MemoryManager completo (consolidación, deduplicación, redacción de secretos).
- [ ] Embeddings opcionales para memoria semántica.
- [ ] Export automático a Obsidian vault (ya está preparado).
- [ ] Skill inbox / quarantine para validación de skills externas.
- [ ] Workflow completo end-to-end con LangGraph runtime real.
- [ ] Integration con Telegram para notificaciones.
- [ ] A2A protocol para comunicar con agentes externos.

---

*Última actualización:跟着 implementación de SkillLoader dinámico (commit c26fbd1)*
