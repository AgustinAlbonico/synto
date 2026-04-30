# Synto — Roadmap

> Estado al 29/04/2026. Este documento es la **fuente de verdad** para saber qué está implementado y qué falta.

---

## Implementado ✅

### Core
- [x] **Agentes** — 25+ agentes definidos (`src/synto/agents/all_agents.py`) con system prompts y MCP tool permissions
- [x] **Orchestrator** — Workflow LangGraph completo con 10+ fases: intake → discovery → prd → spec → planning → implementation → testing → review → qa → release → deploy (`src/synto/workflows/orchestrator.py`)
- [x] **Tool Layer** — filesystem, terminal, git, patch, process, web extract (`src/synto/tools/tool_layer.py`)
- [x] **Memory System** — SQLite FTS5, context building, obsidian export, redaction, pack builder, ranking (`src/synto/memory/`)
- [x] **Skill Loader** — Carga skills dinámicamente por agente según `agent-skill-map.yaml` (`src/synto/registry/skill_loader.py`)
- [x] **Agent Registry** — YAML registry con 25+ agentes, phases, gates (`AGENT-REGISTRY.yaml`)
- [x] **LLM Router** — Multi-provider (OpenCode Zen, OpenRouter, etc.) (`src/synto/config/llm_router.py`)
- [x] **Checkpointing** — SqliteSaver para pause/resume de workflows
- [x] **Tests** — 150 tests passing
- [x] **Web API** — FastAPI con endpoints de health, skills, runs, artifacts

### Services
- [x] **Prompt Improver** — Evaluación de calidad de prompts en 6 dimensiones (clarity, efficiency, structure, completeness, actionability, specificity) (`services/prompt_improver/`)

---

## Pendiente ❌

### Workspace & Contexto
- [ ] **Workspace** — Selección de carpetas de proyecto como unidad de trabajo
- [ ] **Stack Detection** — Detección automática del stack tecnológico (frameworks, lenguajes, DB, tools)
- [ ] **Workspace-Orchestrator Integration** — Inyectar contexto del workspace en prompts de agentes

### UI / Frontend
- [ ] **Web Interface** — Frontend web para el orchestrator (planificado en `WEB-INTERFACE-VISION.md`)
- [ ] **TUI / CLI interactivo** — Interfaz de línea de comandos para usar Synto

### Runtime de Agentes
- [ ] **Agent Runner** — Ejecutar agentes reales (Claude Code, OpenCode, Codex CLI) en terminals PTY
- [ ] **PTY Integration** — node-pty / ptyproceso para terminales reales
- [ ] **Tauri Desktop App** — App desktop con terminal, editor, browser integrado

### Integración
- [ ] **Hermes Gateway Integration** — Conectar Synto con el gateway de Hermes para recibir requests
- [ ] **MCP Server** — Exponer herramientas de Synto como MCP server
- [ ] **Webhook Subscriptions** — Event-driven agent runs via webhooks

### Orchestrator SDD
- [ ] **Supervisor UI** — Panel de control con input de goals, task breakdown visible, activity feed
- [ ] **Manual Mode completo** — Generar plan y que el usuario apruebe antes de ejecutar
- [ ] **Autonomous Mode** — Ejecución sin intervención (Level 3-5 autonomy)

---

## Roadmap por prioridad

### Inmediato (lo que sigue)
1. **Workspace + Stack Detection** — Docs en `docs/plans/01_workspace-stack-detection.md`
2. **CLI interactivo** — Poder usar Synto desde terminal con workspaces

### Corto plazo
3. Integrar Workspace en el Orchestrator (inyectar contexto en prompts)
4. Web Interface básica

### Medio plazo
5. Agent Runner con PTY
6. Tauri Desktop App

### Largo plazo
7. Autonomous Mode
8. MCP Server

---

## Notas

- Synto actualmente corre como CLI Python en un directorio fijo — **no tiene noción de proyectos ni workspaces**
- La documentación en `GUIA-MAESTRA.md` (~950 líneas) describe una arquitectura de 4 capas que está **parcialmente implementada** — los agentes existen pero el runtime de ejecución real (PTY, terminals) no
- El proyecto AgentDock (`Desktop/proy/`) tiene implementaciones de Tauri + NestJS que podrían servir como referencia para la desktop app
