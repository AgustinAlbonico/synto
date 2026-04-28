# Hermes Orchestrator Implementation Plan

> **For Hermes:** Use `subagent-driven-development` to implement this plan task-by-task when execution starts.

**Goal:** construir el primer MVP funcional de `hermes-orchestrator` sin perder contexto, arrancando por la memoria persistente y su capa MCP antes de implementar el swarm completo.

**Architecture:** implementación memory-first sobre Python, con `MemoryStore` SQLite/FTS5, una capa determinística `Memory MCP Server`/tool layer, `MemoryContextAgent` liviano para memory packs, `MemoryManager` para consolidación y luego integración con `SharedState` y LangGraph.

**Tech Stack inicial:** Python 3.12, SQLite/FTS5, Pydantic, pytest, LangGraph, MCP SDK, YAML, Markdown/Obsidian export posterior.

---

## Decisión de arranque

Sí conviene arrancar por memoria, pero no por toda la memoria completa.

Conviene arrancar por una base mínima, testeable y útil:

```text
0. Scaffolding + tests
1. MemoryStore SQLite + FTS5
2. Memory MCP/tool layer
3. MemoryContextAgent liviano
4. MemoryManager básico
5. Integración con SharedState mock
6. AgentRegistry + SkillRegistry
7. LangGraph workflow mock
```

Motivo:

- La memoria resuelve el problema de contexto/compactación.
- Se puede implementar y testear aislada.
- Después todos los agentes se benefician de la misma capa.
- Evita construir un swarm que después haya que rearmar para agregar memoria.

---

## Fase 0 — Preparación del proyecto

### Task 0.1: Inicializar repo Git

**Objective:** versionar cambios antes de empezar a implementar.

**Files:**
- Modifica metadata Git del directorio.

**Steps:**

1. Ejecutar:

```bash
git init
```

2. Crear `.gitignore`.

**Create:** `.gitignore`

Contenido recomendado:

```gitignore
.venv/
__pycache__/
*.pyc
.env
workspace/.hermes-memory/*.sqlite
workspace/.hermes-memory/*.sqlite-*
workspace/.hermes-memory/audit.jsonl
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
```

3. Verificar:

```bash
git status --short
```

Expected:

```text
?? .gitignore
?? docs/code files...
```

4. Commit:

```bash
git add .gitignore README.md *.md AGENT-REGISTRY.yaml config/agent-skill-map.yaml
 git commit -m "docs: freeze orchestrator architecture"
```

---

### Task 0.2: Crear package layout moderno

**Objective:** separar código nuevo del prototipo legacy `hermes_agency.py`.

**Files:**
- Create: `src/hermes_orchestrator/__init__.py`
- Create: `src/hermes_orchestrator/memory/__init__.py`
- Create: `src/hermes_orchestrator/mcp/__init__.py`
- Create: `src/hermes_orchestrator/shared_state/__init__.py`
- Create: `src/hermes_orchestrator/registry/__init__.py`
- Create: `tests/__init__.py`

**Steps:**

1. Crear carpetas.
2. Crear archivos `__init__.py` vacíos.
3. Verificar import básico:

```bash
python -c "import hermes_orchestrator; print('ok')"
```

Expected:

```text
ok
```

---

### Task 0.3: Crear `pyproject.toml`

**Objective:** declarar dependencias y comandos de test.

**Files:**
- Create: `pyproject.toml`

**Contenido inicial:**

```toml
[project]
name = "hermes-orchestrator"
version = "0.1.0"
description = "Multi-agent orchestration runtime with persistent memory"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.7",
  "PyYAML>=6.0",
  "langgraph>=0.2",
  "mcp>=1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "ruff>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]
```

**Verify:**

```bash
python -m pytest -q
```

Expected:

```text
no tests ran
```

---

## Fase 1 — Memory models + schema

### Task 1.1: Crear modelos Pydantic de memoria

**Objective:** definir los contratos de datos antes de tocar SQLite.

**Files:**
- Create: `src/hermes_orchestrator/memory/models.py`
- Create: `tests/memory/test_models.py`

**Modelos mínimos:**

- `MemoryKind`
- `MemoryStatus`
- `MemoryItem`
- `MemoryCandidate`
- `MemoryLink`
- `MemoryPackItem`
- `MemoryPack`
- `TaskContext`

**Test cases:**

- crea un `MemoryItem` válido;
- falla si falta `project_id`;
- `MemoryPack` respeta `agent_id` y `token_budget`;
- `MemoryCandidate` puede representar una decisión o problema resuelto.

**Verify:**

```bash
python -m pytest tests/memory/test_models.py -q
```

Expected:

```text
4 passed
```

---

### Task 1.2: Crear schema SQLite + FTS5

**Objective:** crear la estructura durable del `MemoryStore`.

**Files:**
- Create: `src/hermes_orchestrator/memory/schema.sql`
- Create: `src/hermes_orchestrator/memory/store.py`
- Create: `tests/memory/test_schema.py`

**Tablas MVP:**

```text
projects
features
topics
memory_items
memory_items_fts
memory_links
memory_candidates
sessions
memory_access_log
```

**Important:** usar FTS5 para `summary`, `content`, `tags`.

**Test cases:**

- inicializa DB en path temporal;
- existen todas las tablas;
- FTS5 está habilitado;
- migración es idempotente.

**Verify:**

```bash
python -m pytest tests/memory/test_schema.py -q
```

Expected:

```text
4 passed
```

---

### Task 1.3: Implementar operaciones CRUD básicas

**Objective:** poder crear proyecto, feature, topic y memory item.

**Files:**
- Modify: `src/hermes_orchestrator/memory/store.py`
- Create: `tests/memory/test_store_crud.py`

**API mínima:**

```python
class MemoryStore:
    def create_project(self, slug: str, name: str) -> str: ...
    def create_feature(self, project_id: str, slug: str, name: str) -> str: ...
    def create_topic(self, project_id: str, feature_id: str | None, slug: str, name: str) -> str: ...
    def add_memory_item(self, item: MemoryItem) -> str: ...
    def get_memory_item(self, memory_id: str) -> MemoryItem | None: ...
```

**Test cases:**

- crea proyecto;
- crea feature;
- crea topic;
- guarda y recupera memory item;
- no duplica project slug.

**Verify:**

```bash
python -m pytest tests/memory/test_store_crud.py -q
```

---

### Task 1.4: Implementar búsqueda FTS5

**Objective:** recuperar memorias relevantes por texto.

**Files:**
- Modify: `src/hermes_orchestrator/memory/store.py`
- Create: `tests/memory/test_search.py`

**API mínima:**

```python
def search(self, query: str, project_id: str | None = None, limit: int = 10) -> list[MemorySearchResult]: ...
```

**Test cases:**

- busca por palabra exacta;
- filtra por proyecto;
- ordena por score básico;
- respeta `limit`;
- no devuelve soft-deleted.

---

### Task 1.5: Implementar redacción de secretos

**Objective:** evitar guardar credenciales o tokens.

**Files:**
- Create: `src/hermes_orchestrator/memory/redaction.py`
- Create: `tests/memory/test_redaction.py`

**Debe redactar:**

- `sk-...`
- `ghp_...`
- `Bearer ...`
- `password=...`
- `token=...`
- `api_key=...`
- private keys.

**Expected:** reemplazar por `[REDACTED]`.

---

## Fase 2 — MemoryPackBuilder y control de contexto

### Task 2.1: Crear ranker simple

**Objective:** ordenar resultados según relevancia inicial sin embeddings.

**Files:**
- Create: `src/hermes_orchestrator/memory/ranking.py`
- Create: `tests/memory/test_ranking.py`

**Score inicial:**

```text
score = keyword_match
      + project_scope_boost
      + agent_role_boost
      + importance
      + confidence
      - stale_penalty
      - conflict_penalty
```

**No implementar embeddings todavía.**

---

### Task 2.2: Crear MemoryPackBuilder

**Objective:** transformar resultados en paquetes chicos por agente.

**Files:**
- Create: `src/hermes_orchestrator/memory/pack_builder.py`
- Create: `tests/memory/test_pack_builder.py`

**API mínima:**

```python
class MemoryPackBuilder:
    def build_pack(self, task: TaskContext, agent_id: str, token_budget: int) -> MemoryPack: ...
```

**Test cases:**

- respeta token budget aproximado;
- prioriza memoria del mismo proyecto;
- filtra por rol;
- incluye fuentes;
- no incluye contenido eliminado/conflictivo salvo que se pida.

---

## Fase 3 — Memory MCP / tool layer

### Task 3.1: Crear tool layer determinística

**Objective:** exponer operaciones como funciones seguras antes de envolverlas como MCP.

**Files:**
- Create: `src/hermes_orchestrator/mcp/memory_tools.py`
- Create: `tests/mcp/test_memory_tools.py`

**Tools iniciales:**

```text
memory.search
memory.get_item
memory.get_tree
memory.build_pack
memory.add_candidate
memory.list_candidates
memory.commit_candidate
memory.reject_candidate
memory.link_items
memory.forget
```

**Regla:** ningún tool devuelve memoria ilimitada.

---

### Task 3.2: Crear servidor MCP stdio mínimo

**Objective:** permitir que otros agentes/clientes llamen tools de memoria vía MCP.

**Files:**
- Create: `src/hermes_orchestrator/mcp/memory_server.py`
- Create: `tests/mcp/test_memory_server_contract.py`

**Verify:**

- server lista tools;
- tool `memory.search` responde JSON estructurado;
- tool `memory.build_pack` respeta budget;
- errores redactan secretos.

---

## Fase 4 — MemoryContextAgent y MemoryManager

### Task 4.1: Implementar MemoryContextAgent liviano

**Objective:** construir contexto por agente al inicio de un run.

**Files:**
- Create: `src/hermes_orchestrator/memory/context_agent.py`
- Create: `tests/memory/test_context_agent.py`

**API mínima:**

```python
class MemoryContextAgent:
    def hydrate(self, task: TaskContext, agent_ids: list[str]) -> dict[str, MemoryPack]: ...
```

**Reglas:**

- no habla con usuario;
- no guarda memoria;
- no lee SQLite directo;
- usa tool layer / MemoryStore interface;
- devuelve packs chicos.

---

### Task 4.2: Implementar MemoryManager básico

**Objective:** consolidar candidatos al final de un run.

**Files:**
- Create: `src/hermes_orchestrator/memory/manager.py`
- Create: `tests/memory/test_manager.py`

**API mínima:**

```python
class MemoryManager:
    def add_candidate(self, candidate: MemoryCandidate) -> str: ...
    def commit_candidate(self, candidate_id: str, actor: str) -> str: ...
    def reject_candidate(self, candidate_id: str, reason: str, actor: str) -> None: ...
```

**Reglas:**

- redactar antes de guardar;
- deduplicar básico;
- guardar audit log;
- no auto-commitear contenido inseguro.

---

## Fase 5 — SharedState mock e integración

### Task 5.1: Crear modelos de SharedState mínimos

**Objective:** poder pasar memory packs a agentes mock sin tener LangGraph todavía.

**Files:**
- Create: `src/hermes_orchestrator/shared_state/models.py`
- Create: `tests/shared_state/test_models.py`

**Campos mínimos:**

```text
run_id
project_id
task_summary
memory_context.global
memory_context.by_agent
agent_slots
events
artifacts
```

---

### Task 5.2: Crear flujo mock end-to-end memory-first

**Objective:** demostrar que la memoria ya sirve antes del swarm completo.

**Files:**
- Create: `src/hermes_orchestrator/workflows/memory_first_mock.py`
- Create: `tests/workflows/test_memory_first_mock.py`

**Flow:**

```text
TaskContext entra
→ MemoryContextAgent arma packs
→ BackendAgent mock recibe pack
→ genera output mock
→ MemoryManager crea candidato
→ candidato se commitea
→ búsqueda futura lo encuentra
```

**Verify:**

```bash
python -m pytest tests/workflows/test_memory_first_mock.py -q
```

Expected:

```text
1 passed
```

---

## Fase 6 — AgentRegistry + SkillRegistry

### Task 6.1: Loader de AgentRegistry

**Objective:** leer y validar `AGENT-REGISTRY.yaml`.

**Files:**
- Create: `src/hermes_orchestrator/registry/agent_registry.py`
- Create: `tests/registry/test_agent_registry.py`

**Debe validar:**

- todos los agentes tienen role;
- restrictions;
- reads/writes;
- model_profile;
- mcp_capabilities;
- no capability desconocida.

---

### Task 6.2: SkillRegistry scanner

**Objective:** descubrir skills disponibles sin cargarlas completas.

**Files:**
- Create: `src/hermes_orchestrator/registry/skill_registry.py`
- Create: `tests/registry/test_skill_registry.py`

**Reglas:**

- metadata always available;
- full skill lazy;
- skills externas en quarantine;
- nunca cargar todas las skills a todos los agentes.

---

## Fase 7 — LangGraph runtime mínimo

### Task 7.1: Crear grafo mínimo

**Objective:** ejecutar un workflow mock con nodos reales de orquestación.

**Files:**
- Create: `src/hermes_orchestrator/runtime/graph.py`
- Create: `tests/runtime/test_graph.py`

**Nodos iniciales:**

```text
intake
memory_rehydration
planning_mock
implementation_mock
memory_consolidation
delivery
```

**Acceptance:**

- el grafo ejecuta de punta a punta;
- SharedState conserva events;
- memory packs se inyectan;
- MemoryManager guarda candidato final.

---

## Fase 8 — Obsidian export básico

### Task 8.1: Exportar memoria a Markdown

**Objective:** generar espejo humano-readable.

**Files:**
- Create: `src/hermes_orchestrator/memory/obsidian_export.py`
- Create: `tests/memory/test_obsidian_export.py`

**No hacer bidireccional todavía.**

Output esperado:

```text
workspace/.hermes-memory/exports/obsidian/{project}/{feature}/{topic}.md
```

---

## Fase 9 — CLI mínima

### Task 9.1: CLI para probar memoria

**Objective:** poder probar sin UI ni swarm completo.

**Files:**
- Create: `src/hermes_orchestrator/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/test_cli.py`

**Comandos:**

```bash
hermes-orchestrator memory init
hermes-orchestrator memory add --project sistema-odontologico --kind decision --text "..."
hermes-orchestrator memory search "turnos utc"
hermes-orchestrator memory build-pack --agent BackendImplementer --task "..."
```

---

## Verificación global del MVP memory-first

Cuando terminen Fases 0-5, esto debería pasar:

```bash
python -m pytest -q
```

Expected:

```text
all tests passing
```

Demo manual esperada:

```bash
hermes-orchestrator memory init
hermes-orchestrator memory add --project sistema-odontologico --kind decision --text "Los turnos no se borran físicamente; se cancelan."
hermes-orchestrator memory search "turnos borran"
hermes-orchestrator memory build-pack --agent BackendImplementer --task "Agregar recordatorios WhatsApp a turnos"
```

Debe devolver un memory pack chico, con fuentes y sin traer toda la memoria.

---

## Qué NO implementar todavía

- UI web completa.
- Vector DB.
- GraphRAG.
- A2A.
- Multiusuario.
- Deploy.
- Agentes reales haciendo código.
- Auto-commit agresivo de memoria.
- Obsidian como fuente principal.

---

## Orden de commits sugerido

```text
chore: initialize project package and test scaffold
test: add memory model tests
feat: add memory models
feat: add sqlite memory schema
feat: add memory store crud
feat: add fts memory search
feat: add memory redaction
feat: add memory pack builder
feat: add memory tool layer
feat: add memory mcp server
feat: add memory context agent
feat: add memory manager
feat: add shared state memory integration mock
docs: add memory-first implementation notes
```

---

## Criterio para pasar a implementar agentes reales

No avanzar a agentes reales hasta que exista:

- test suite verde;
- MemoryStore operativo;
- Memory MCP/tool layer operativo;
- MemoryContextAgent arma packs;
- MemoryManager guarda candidatos;
- SharedState mock recibe `memory_context.by_agent`;
- workflow mock end-to-end funciona.

Recién ahí conviene construir:

```text
AgentRegistry → SkillRegistry → LangGraph runtime → agentes especializados reales
```
