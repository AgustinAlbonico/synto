# Synto

> Sistema de orquestación multi-agente para operar equipos de agentes especializados con SDD, PRD-first, TDD, LangGraph, MCP y Skill Registry dinámico.

Estado actual: **runtime LangGraph + memoria + MCP + CLI + Command Center web local-first + SkillLoader dinámico implementados**.

---

## Decisión actual

La versión anterior apuntaba a Agency Swarm. Esa decisión quedó reemplazada.

La arquitectura vigente es:

- **LangGraph** como runtime de orquestación.
- **MCP** como protocolo agent-to-tool.
- **SharedState / Blackboard** para coordinación entre agentes propios dentro de un run.
- **PersistentMemory / MemoryStore** para memoria cross-session y rehidratación automática de contexto.
- **Skill Registry dinámico** para cargar skills por agente y permitir skills nuevas agregadas por el usuario.
- **A2A** queda como capa futura, no como dependencia del MVP.
- **Web Interface** queda prevista como fase posterior, una vez estable el motor.

---

## Documentos principales

| Documento | Para qué sirve |
|---|---|
| `LANGGRAPH-ARCHITECTURE.md` | Arquitectura principal, capas, workflow, decisiones y roadmap. |
| `AGENT-REGISTRY.yaml` | Contrato de agentes: roles, restricciones, skills, tools MCP, inputs/outputs. |
| `SKILL-LOADING-SYSTEM.md` | Diseño del sistema de carga dinámica de skills. |
| `SHARED-STATE-SPEC.md` | Especificación del blackboard, slots, gates, artifacts y concurrencia. |
| `PERSISTENT-MEMORY-SPEC.md` | Memoria cross-session, MemoryStore, rehidratación automática y MemoryManager. |
| `MEMORY-ARCHITECTURE-RESEARCH.md` | Investigación comparativa: Engram, Obsidian, vector DB, graph/tree memory y decisión recomendada. |
| `MEMORY-MCP-ARCHITECTURE.md` | Capa aprobada de acceso a memoria: Memory MCP Server + MemoryContextAgent + control anti-compactación. |
| `DOCUMENTATION-AUDIT.md` | Auditoría de documentación y huecos cerrados antes de implementar. |
| `IMPLEMENTATION-PLAN.md` | Plan de implementación memory-first con tareas, archivos y verificaciones. |
| `WEB-INTERFACE-VISION.md` | Visión inicial de la interfaz web futura. |
| `GUIA-MAESTRA.md` | Documento histórico/base del proyecto. Mantiene decisiones previas y referencia general. |
| `DEFINICION-AGENTES.md` | Definición original de agentes. Reemplazada parcialmente por `AGENT-REGISTRY.yaml`. |
| `USER-GUIDE.md` | Guía de uso para el usuario final. Cómo instalar, operar, configurar y resolver problemas de Synto. |

---

## Equipo Code Domain actual

El MVP del dominio Code incluye:

- HermesOrchestrator
- CodeOrchestrator
- BusinessAnalyst
- ProductManager
- Planner
- CodebaseExplorer
- Architect
- SystemDesigner
- Tester
- BackendImplementer
- FrontendImplementer
- ContractAligner
- Reviewer
- SecurityReviewer
- QAGatekeeper
- DependencyChecker
- TechnicalWriter
- ReleaseManager
- Builder

Además del equipo Code Domain, se agrega un agente/servicio cross-cutting:

- MemoryContextAgent / MemoryRetriever
- MemoryManager

`MemoryContextAgent` es un agente liviano: busca contexto relevante vía Memory MCP y arma memory packs chicos por agente para evitar consumo excesivo de contexto.

`MemoryManager` no es un implementador ni un agente de producto: es la capa encargada de consolidar aprendizajes, deduplicar, redactar secretos y persistir memoria canónica entre sesiones.

Cada agente tiene:

- rol específico;
- responsabilidades;
- restricciones;
- inputs/outputs;
- slots de escritura;
- skills base;
- skills dinámicas permitidas;
- tools MCP permitidas.

El contrato vivo está en `AGENT-REGISTRY.yaml`.

---

## Workflow previsto

```text
Intake
  → Discovery
  → PRD approval
  → Technical Planning paralelo
  → Spec/Design consolidation
  → TDD/Test Plan
  → Backend + Frontend implementation paralelo
  → SystemDesigner review loop
  → Contract alignment
  → Review + Security + Tests
  → QA + Dependency + Docs
  → Release/PR
  → Deploy opcional
  → Delivery
```

---

## Skill Registry dinámico

Objetivo:

- No cargar todas las skills siempre.
- Cada agente carga solo su repertorio útil.
- El usuario puede agregar skills nuevas encontradas en internet.
- Las skills externas pasan por inbox/quarantine/validación antes de asignarse.
- Se soportan base skills, skills manuales, triggers y carga lazy.

Estado implementado:

- `SkillRegistry` descubre metadata de `SKILL.md` sin cargar todo el contenido.
- `SkillRegistry` clasifica automáticamente tags básicos cuando la skill no declara tags.
- `SkillLoader.resolve(agent, state)` selecciona skills por agente/invocación usando:
  - `base_skills.required` y `base_skills.optional` desde `AGENT-REGISTRY.yaml`;
  - overrides manuales desde `config/agent-skill-map.yaml`;
  - `dynamic_skill_policy.allowed_tags` / `denied_tags`;
  - `allowed_agents` en el frontmatter de cada skill para skills dedicadas o compartidas;
  - triggers por keyword, phase, regex o file glob.
- El contenido completo se carga lazy, solo para las skills seleccionadas y bajo presupuesto.
- La ejecución de agentes inyecta el contexto en el system prompt bajo `--- Loaded Skills ---`.
- Cada carga queda auditada en `state/skill-load-events.jsonl` y expuesta por la API web.

Ver: `SKILL-LOADING-SYSTEM.md`.

---

## SharedState / Blackboard

Objetivo:

- permitir agentes paralelos sin pisarse;
- versionar artefactos;
- pausar y retomar workflows;
- registrar eventos;
- exponer estado a una futura UI web.

Regla central:

> Los workers escriben en su slot. Los orquestadores/consolidadores escriben artefactos canónicos.

Ver: `SHARED-STATE-SPEC.md`.

---

## PersistentMemory / MemoryStore

Objetivo:

- recordar contexto útil entre sesiones;
- rehidratar automáticamente cada run con memoria relevante;
- construir memory packs por agente sin cargar toda la historia;
- guardar decisiones, preferencias, resúmenes de artifacts y aprendizajes;
- mantener provenance, auditoría, redacción de secretos y derecho a olvidar.

Regla central:

> SharedState coordina el presente. PersistentMemory trae contexto del pasado y consolida aprendizajes para el futuro.

Ver: `PERSISTENT-MEMORY-SPEC.md`.

Investigación comparativa y decisión de diseño:

- `MEMORY-ARCHITECTURE-RESEARCH.md`

Decisión operativa actual:

> La memoria no será un árbol puro ni una DB plana. Será un híbrido: árbol primario `Project -> Feature -> Topic`, grafo liviano de relaciones, SQLite/FTS5 como fuente canónica, embeddings opcionales y export a Obsidian como espejo humano-readable.

Decisión de acceso:

> Los agentes no consultan SQLite ni cargan toda la memoria. La memoria se expone mediante `Memory MCP Server`/tool layer; `MemoryContextAgent` arma memory packs chicos por rol/fase/tarea; `MemoryManager` consolida y guarda aprendizajes.

---

## Herramientas de Agentes (Tools)

Los agentes de Synto tienen acceso a **37 herramientas** en 8 categorías para trabajar de forma 100% autónoma:

| Categoría | Herramientas |
|---|---|
| **Filesystem** | `read_file`, `write_file`, `create_directory`, `list_directory`, `search_files`, `move_file`, `delete_file`, `get_file_info` |
| **Terminal** | `terminal` (ejecuta cualquier comando shell) |
| **Git** | `git_status`, `git_diff`, `git_log`, `git_branch`, `git_checkout`, `git_commit`, `git_push`, `git_clone` |
| **Web** | `web_search`, `web_extract` |
| **GitHub** | `github_search_code`, `github_search_issues`, `github_get_file_contents`, `github_create_issue`, `github_create_pull_request` |
| **Code** | `patch` (find-and-replace en archivos) |
| **Process** | `process_start`, `process_poll`, `process_kill`, `process_list` |
| **Memory** | `memory_search`, `memory_build_pack`, `memory_add_candidate`, etc. |

### Tool calling loop

Los agentes de implementación (BackendImplementer, FrontendImplementer, Builder, Tester, Reviewer, etc.) tienen herramientas habilitadas por defecto. El LLM puede:

1. Recibir tool definitions en su prompt
2. Responder con tool calls en formato JSON
3. Ejecutar las herramientas y obtener resultados
4. Continuar trabajando con los resultados
5. Repetir hasta completar la tarea (máx 20 iteraciones)

### MCP Server

Todas las herramientas están expuestas como MCP server:

```bash
# Via stdio (para conectar con clientes MCP)
.venv/bin/python -m synto.tools.mcp_server

# Via HTTP
.venv/bin/python -m synto.tools.mcp_server --transport sse --port 8765
```

---

## Interfaz web

Ya existe una primera versión local-first del **Synto Command Center**.

Arranque rápido:

```bash
synto web --port 8787
# abrir http://127.0.0.1:8787
```

También se puede ejecutar desde el repo:

```bash
.venv/bin/python -m synto.cli web --port 8787
```

Incluye:

- dashboard de runs;
- lanzamiento de workflows;
- detalle con timeline, eventos y SharedState;
- centro de aprobación de gates;
- artifacts viewer;
- vista del equipo de agentes desde `AGENT-REGISTRY.yaml`;
- Skill Manager básico;
- Memory Center básico;
- Design System Studio inicial;
- API FastAPI en `/api/*` y documentación en `/docs`.

Endpoints base:

```http
GET  /api/health
GET  /api/runs
POST /api/runs
GET  /api/runs/{run_id}
POST /api/runs/{run_id}/resume
GET  /api/runs/{run_id}/events
GET  /api/runs/{run_id}/artifacts
GET  /api/agents
GET  /api/skills
GET  /api/memory/search
GET  /api/memory/candidates
GET  /api/llm/providers
GET  /api/llm/models
GET  /api/llm/profiles
GET  /api/tools
```

Ver: `WEB-INTERFACE-VISION.md`.

---

## Estado actual

**Todo el plan de implementación (Fases 0-9) está completo.**

| Componente | Estado |
|---|---|
| MemoryStore SQLite/FTS5 | ✅ |
| MemoryContextAgent + MemoryManager | ✅ |
| Memory MCP Server (14 tools) | ✅ |
| Obsidian export | ✅ |
| AgentRegistry (19 agentes) | ✅ |
| SkillRegistry + SkillLoader dinámico | ✅ |
| LangGraph runtime (13 fases con gates) | ✅ |
| LLM Router (múltiples proveedores) | ✅ |
| Web API + Command Center | ✅ |
| LLM Provider Manager (UI) | ✅ |
| Agent Tools (37 tools, 8 categorías) | ✅ |
| Tool calling loop autónomo | ✅ |
| CLI (`synto run/web/memory/registry`) | ✅ |
| Tests (150 passing, incluye E2E) | ✅ |

## Próximo paso recomendado

El motor está completo con herramientas autónomas. Las siguientes mejoras son opcionales:

1. **Ejecución real end-to-end**: Configurar API keys reales en la UI de LLM Providers y ejecutar un workflow completo con LLMs de verdad. Los agentes ya tienen todas las herramientas (filesystem, terminal, git, web, github) — solo falta el LLM real.
2. **Vector embeddings**: Agregar embeddings opcionales al MemoryStore para búsqueda semántica (hoy usa FTS5 keyword search).
3. **A2A protocol**: Implementar Agent-to-Agent communication para orquestación distribuida.
4. **Deploy**: Empaquetar como servicio Docker o systemd.
5. **Agentes de dominio adicionales**: Equipos para análisis de negocio, research, data science, etc.

---

## Nota importante

El código existente (`hermes_agency.py`) pertenece al prototipo anterior basado en Agency Swarm y no representa la arquitectura vigente. Debe considerarse legacy/prototipo hasta migrarlo o reemplazarlo.
