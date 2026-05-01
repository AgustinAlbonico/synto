# Synto — Code Agents + Skill Injection + OpenCode Runner

Estado: diseño operativo inicial
Fecha: 2026-04-30

## Regla de activación

Este flujo SOLO se activa cuando `HermesOrchestrator` clasifica el prompt como dominio `code`.

Ejemplos que SÍ activan Code:
- "creá una app..."
- "agregá esta feature..."
- "arreglá este bug..."
- "inicializá un proyecto..."
- "implementá backend/frontend/tests..."

Ejemplos que NO activan Code:
- investigación general
- ideas de negocio
- preguntas conceptuales
- comparación de herramientas
- contenido / marketing
- data analysis sin implementación

Flujo de routing:

```txt
User prompt
  -> HermesOrchestrator.intent_classifier
      -> domain=code      -> CodeOrchestrator + flujos SDD/TDD/OpenCode
      -> domain=research  -> ResearchOrchestrator
      -> domain=business  -> BusinessIdeasAgent
      -> domain=content   -> ContentOrchestrator
      -> domain=devops    -> DevOpsOrchestrator
      -> unclear          -> pregunta de clarificación, NO ejecuta Code todavía
```

La detección de proyecto nuevo (`.synto/config.yaml`) ocurre recién DESPUÉS de confirmar `domain=code`.

---

## Principio central

Synto no debe ser "un chatbot que codea".

Synto debe ser un sistema de coordinación:

```txt
Orchestrator decide y consolida
Agentes especialistas producen artefactos
OpenCode ejecuta sesiones aisladas para tareas de código/escritura en repo
SharedState guarda outputs y gates
MemoryManager persiste aprendizajes
```

---

## Tipos de agentes

### 1. Agentes conversacionales / estratégicos

No necesitan OpenCode por defecto. Producen decisiones, preguntas o artefactos.

- `HermesOrchestrator`
- `CodeOrchestrator`
- `InterviewAgent`
- `RequirementsAgent`
- `TechStackAdvisorAgent`
- `PlannerAgent`
- `Architect`
- `SystemDesigner`

### 2. Agentes ejecutores sobre workspace

Usan OpenCode porque necesitan tocar archivos, correr comandos o revisar repo real.

- `ProjectInitializerAgent`
- `TDDAgent`
- `BackendImplementer`
- `FrontendImplementer`
- `ContractAligner`
- `Reviewer`
- `SecurityReviewer`
- `QAGatekeeper`
- `DependencyChecker`
- `TechnicalWriter`
- `ReleaseManager`
- `Builder`

NO todos escriben código de producción. OpenCode es el ejecutor de sesión, pero el prompt y permisos definen si puede escribir o solo leer.

---

## Agentes del dominio Code

### HermesOrchestrator

Rol: punto único de contacto con el usuario.

Responsabilidades:
- clasificar intención;
- enrutar al dominio correcto;
- hacer preguntas al usuario cuando un agente interno necesita input;
- pedir aprobaciones de gates;
- mostrar estado y resultado final.

Skills fijas:
- `writing-plans`
- `subagent-driven-development`
- `obsidian`

No usa OpenCode.

---

### CodeOrchestrator

Rol: engineering lead del dominio Code.

Responsabilidades:
- decidir si el proyecto es nuevo o existente;
- coordinar fases;
- consolidar artefactos;
- lanzar sesiones OpenCode cuando corresponda;
- aplicar gates.

Skills fijas:
- `test-driven-development`
- `writing-plans`
- `codebase-inspection`
- `systematic-debugging`

Skills dinámicas:
- `github-pr-workflow` si hay repo remoto/PR;
- `architecture-diagram` si hay diseño técnico complejo.

No implementa código directamente. Puede invocar `OpenCodeSessionRunner` como herramienta.

---

### ProjectInitAgent

Rol: detector de proyecto nuevo.

Responsabilidades:
- revisar si existe `.synto/config.yaml` en el workspace;
- detectar si el prompt pide crear/inicializar software;
- activar flujo de proyecto nuevo si corresponde.

Skills fijas:
- `codebase-inspection`

OpenCode: no por defecto. Solo lee estado del workspace.

Output:

```yaml
new_project: true|false
reason: "..."
workspace_status:
  has_synto_config: true|false
  has_git_repo: true|false
  detected_stack: []
```

---

### InterviewAgent

Rol: entrevista de descubrimiento.

Responsabilidades:
- hacer preguntas generales sobre qué se va a construir;
- entender usuario, problema, contexto, alcance y riesgos;
- NO preguntar todavía detalles finos de implementación.

Skills fijas:
- `writing-plans`
- `obsidian`

OpenCode: no.

Output:
- `01-discovery/context.md`
- preguntas pendientes si falta información crítica.

---

### RequirementsAgent

Rol: convierte discovery en requisitos.

Responsabilidades:
- requisitos funcionales;
- requisitos no funcionales de alto nivel;
- reglas de negocio;
- criterios de aceptación;
- fuera de alcance.

Skills fijas:
- `writing-plans`
- `obsidian`

OpenCode: no, salvo que deba escribir archivos en repo. En ese caso usa `opencode run --agent build` en modo documentación controlada.

Output:
- `02-requirements/requirements.md`

---

### TechStackAdvisorAgent

Rol: asesor de stack tecnológico para proyecto nuevo.

Responsabilidades:
- guiar al usuario con preguntas concretas;
- proponer stack con tradeoffs;
- detectar restricciones: deploy, presupuesto, equipo, performance, realtime, auth, DB;
- generar `stack.md` y parte de `.synto/config.yaml`.

Skills fijas:
- `writing-plans`
- `codebase-inspection`
- `web-research-workflow` cuando tenga que comparar herramientas actuales.

Skills dinámicas:
- `llm-provider-discovery` si el proyecto involucra proveedores LLM;
- `cloudflare-tunnel-local-dev` si el usuario prioriza deploy local/demo;
- stack-specific skills cuando existan.

OpenCode: no por defecto.

Output:

```yaml
stack:
  backend: NestJS|FastAPI|Go|None
  frontend: React|Next|Vue|None
  database: PostgreSQL|MongoDB|SQLite|None
  auth: JWT|OAuth|Session|None
  deploy: Docker|Vercel|Railway|VPS|None
  testing: Jest|Vitest|Pytest|Go test|Playwright
  package_manager: pnpm|npm|uv|poetry|go
rationale:
  - decision: "..."
    why: "..."
    tradeoff: "..."
```

---

### ProjectInitializerAgent

Rol: inicializa el proyecto físico.

Responsabilidades:
- crear carpetas;
- inicializar repo si hace falta;
- crear archivos base;
- instalar dependencias;
- crear `.synto/config.yaml`;
- dejar test runner mínimo funcionando.

Skills fijas:
- `opencode`
- `github-repo-management`
- `test-driven-development`

Skills dinámicas:
- `node-inspect-debugger` para Node/Nest/React;
- `python-debugpy` para Python/FastAPI;
- `go-testing` para Go;
- `frontend-design` si hay UI.

OpenCode: sí, modo escritura.

MVP: correr secuencialmente, NO paralelo, porque crea estructura global.

---

### PlannerAgent

Rol: convierte requirements/spec/design en tareas atómicas.

Responsabilidades:
- ordenar trabajo por dependencia;
- separar backend/frontend/tests/review;
- producir tareas pequeñas y testeables;
- marcar qué agente ejecuta cada tarea.

Skills fijas:
- `writing-plans`
- `codebase-inspection`

OpenCode: opcional read-only si necesita inspeccionar repo real.

Output:
- `05-tasks/tasks.md`
- `task_graph` en SharedState

---

### TDDAgent

Rol: escribe tests ANTES de implementación.

Responsabilidades:
- leer PRD/spec/design/tasks;
- escribir tests de backend/frontend/contract según task graph;
- correr tests para demostrar que fallan por la razón correcta cuando aplique;
- NO escribir código de producción.

Skills fijas que casi no cambian:
- `test-driven-development`
- `systematic-debugging`
- `codebase-inspection`
- `opencode`

Skills dinámicas:
- `node-inspect-debugger` si stack Node/TS;
- `python-debugpy` si stack Python;
- `go-testing` si stack Go;
- `frontend-design` solo si tests cubren UI/comportamiento visual.

OpenCode: sí, modo escritura restringida a tests.

Regla dura:

```txt
PlannerAgent -> TDDAgent -> Backend/Frontend
```

Nunca:

```txt
PlannerAgent -> Backend/Frontend -> TDDAgent
```

Output:
- tests creados;
- `07-tests/test-plan.md`;
- `07-tests/red-results.md` si se corren y fallan como esperado.

---

### BackendImplementer

Rol: implementa backend para hacer pasar tests.

Skills fijas:
- `opencode`
- `test-driven-development`
- `systematic-debugging`

Skills dinámicas:
- `node-inspect-debugger` para NestJS/Express/Node;
- `python-debugpy` para FastAPI/Django;
- `go-testing` para Go;
- DB-specific cuando existan.

OpenCode: sí, modo escritura.

Input obligatorio:
- spec;
- design backend;
- task asignada;
- test plan/tests escritos por TDDAgent;
- límites de archivos permitidos.

Output:
- files_changed;
- tests ejecutados;
- API contract actual;
- riesgos.

---

### FrontendImplementer

Rol: implementa frontend para hacer pasar tests y respetar diseño.

Skills fijas:
- `opencode`
- `frontend-design`
- `test-driven-development`

Skills dinámicas:
- `node-inspect-debugger` para React/Vite/Next;
- `popular-web-designs` si hay diseño visual fuerte;
- `claude-design` solo para artefactos HTML/prototipos;
- `react-doctor` si está instalado en OpenCode y el stack es React.

OpenCode: sí, modo escritura.

Input obligatorio:
- spec;
- frontend design/design-system;
- task asignada;
- tests escritos por TDDAgent;
- API contract draft/actual.

---

### ContractAligner

Rol: verifica que frontend y backend hablen el mismo idioma.

Skills fijas:
- `codebase-inspection`
- `test-driven-development`

OpenCode: sí, preferentemente read-only o escritura limitada a tests de contrato/tipos compartidos.

Output:
- `contract_report`
- lista de incompatibilidades;
- propuesta de corrección.

---

### Reviewer

Rol: revisión general de código.

Skills fijas:
- `requesting-code-review`
- `github-code-review`
- `codebase-inspection`

OpenCode: sí, read-only para revisar diff y generar reporte.

No corrige salvo instrucción explícita.

---

### SecurityReviewer

Rol: revisión de seguridad.

Skills fijas:
- `requesting-code-review`
- `systematic-debugging`

OpenCode: sí, read-only.

Output:
- findings por severidad;
- evidencia;
- recomendación.

---

### QAGatekeeper

Rol: gate final antes de release.

Skills fijas:
- `codebase-inspection`
- `systematic-debugging`
- `test-driven-development`

OpenCode: sí, read-only + ejecución de comandos seguros de validación.

No escribe código.

---

## Política de skills

### Skills fijas

Son parte del contrato del agente. Se cargan siempre.

Ejemplos:
- TDDAgent: `test-driven-development`, `systematic-debugging`, `codebase-inspection`, `opencode`
- BackendImplementer: `opencode`, `test-driven-development`, `systematic-debugging`
- FrontendImplementer: `opencode`, `frontend-design`, `test-driven-development`
- Reviewer: `requesting-code-review`, `github-code-review`

### Skills dinámicas

Se inyectan por contexto:

```txt
stack detectado + archivos tocados + tipo de tarea + tags permitidos del agente
```

Ejemplos:
- Si `stack.backend = FastAPI` -> `python-debugpy`
- Si `stack.backend = NestJS` -> `node-inspect-debugger`
- Si `stack.frontend = React` -> `frontend-design`, `node-inspect-debugger`
- Si `task.type = deploy` -> `cloudflare-tunnel-local-dev`, `levantar-app`, pero solo Builder/DevOps
- Si `task.type = review` -> `requesting-code-review`

### Skills prohibidas por rol

- Interview/Requirements/TechStackAdvisor no cargan skills de code execution.
- Reviewer/SecurityReviewer/QAGatekeeper no cargan skills de escritura salvo instrucción explícita.
- BackendImplementer no carga UI/marketing.
- FrontendImplementer no carga DB/deploy.

---

## OpenCode Runner en la app

### Objetivo

Cada agente ejecutor debe poder lanzar una sesión OpenCode independiente, con:

- título trazable;
- contexto propio;
- skills inyectadas en el prompt/context file;
- workdir aislado cuando haya paralelismo;
- output estructurado;
- logs persistidos;
- diff verificado con git, no solo con stdout del LLM.

### Comando base verificado

OpenCode instalado:

```txt
/home/agust/.opencode/bin/opencode
version: 1.14.28
```

Comando recomendado para MVP:

```bash
opencode run \
  --format json \
  --agent build \
  --title "synto:{run_id}:{agent_id}:{task_id}" \
  -f .synto/runs/{run_id}/context/{agent_id}.md \
  "{task_prompt}"
```

Para revisión/read-only:

```bash
opencode run \
  --format json \
  --agent build \
  --title "synto:{run_id}:{agent_id}:{task_id}" \
  -f .synto/runs/{run_id}/context/{agent_id}.md \
  "Read-only review. Do not modify files. {task_prompt}"
```

No usar `--dangerously-skip-permissions` por defecto.

### Por qué `opencode run` y no TUI

MVP:
- `opencode run` es bounded;
- termina solo;
- se puede ejecutar desde subprocess;
- `--format json` permite eventos parseables;
- más fácil de integrar con LangGraph.

TUI/background queda para modo interactivo futuro.

---

## Workdir isolation

### Regla

Nunca correr dos sesiones OpenCode que escriben sobre el mismo workdir al mismo tiempo.

### MVP recomendado

1. TDDAgent corre primero en workdir principal y escribe tests.
2. Backend/Frontend pueden correr en paralelo SOLO si usan worktrees separados.
3. El orquestador mergea patches al final.

Estructura:

```txt
project/
  .synto/
    runs/{run_id}/
      context/{agent_id}.md
      opencode/{agent_id}/events.jsonl
      opencode/{agent_id}/stdout.txt
      opencode/{agent_id}/stderr.txt
      patches/{agent_id}.patch
      sessions.yaml
    worktrees/{run_id}/
      BackendImplementer/
      FrontendImplementer/
```

Flujo paralelo seguro:

```txt
main workdir has tests from TDDAgent
  -> git worktree add .synto/worktrees/{run}/BackendImplementer HEAD
  -> git worktree add .synto/worktrees/{run}/FrontendImplementer HEAD
  -> run OpenCode in each worktree
  -> git diff --binary > patches/{agent}.patch
  -> apply patches to main in deterministic order
  -> run contract alignment + tests
```

Si hay conflicto:
- `ContractAligner` o `CodeOrchestrator` decide rework;
- no se auto-mergea a ciegas.

### Modo simple inicial

Mientras el runner madura, se puede empezar secuencial:

```txt
TDDAgent -> BackendImplementer -> FrontendImplementer -> ContractAligner
```

Pero la arquitectura debe quedar lista para paralelo con worktrees.

---

## OpenCodeSessionRunner propuesto

Ubicación:

```txt
src/synto/runtime/opencode_runner.py
```

API:

```python
@dataclass
class AgentExecutionSpec:
    run_id: str
    agent_id: str
    task_id: str
    task_prompt: str
    workdir: Path
    context_markdown: str
    opencode_agent: str = "build"
    model: str | None = None
    mode: Literal["read_only", "write", "test_only"] = "write"
    timeout_seconds: int = 900
    allowed_paths: list[str] = field(default_factory=list)

@dataclass
class AgentRunResult:
    run_id: str
    agent_id: str
    task_id: str
    status: Literal["success", "failed", "timeout"]
    exit_code: int | None
    files_changed: list[str]
    tests_reported: list[str]
    stdout_path: Path
    stderr_path: Path
    events_path: Path | None
    patch_path: Path | None
    summary: str

class OpenCodeSessionRunner:
    def run(self, spec: AgentExecutionSpec) -> AgentRunResult: ...
    async def run_async(self, spec: AgentExecutionSpec) -> AgentRunResult: ...
```

Runner responsibilities:

1. Crear context file:
   `.synto/runs/{run_id}/context/{agent_id}.md`
2. Ejecutar `opencode run --format json`.
3. Guardar stdout/stderr/events.
4. Consultar `git status --short` antes/después.
5. Generar patch con `git diff --binary`.
6. Retornar `AgentRunResult`.
7. Nunca confiar solamente en el resumen textual de OpenCode.

---

## Prompt envelope para OpenCode

Cada sesión recibe un envelope uniforme:

```md
# Synto Agent Session

Agent: BackendImplementer
Run ID: ...
Task ID: ...
Mode: write

## Role Contract
[identity, mission, must_do, must_not_do]

## Fixed Skills
- opencode
- test-driven-development
- systematic-debugging

## Dynamic Skills
- node-inspect-debugger

## Inputs
- PRD: path
- Spec: path
- Design: path
- Test plan: path
- Existing tests: path/glob

## Allowed Scope
- backend/**
- shared/contracts/**
- tests/backend/**

## Forbidden
- Do not modify frontend/**
- Do not modify PRD/spec
- Do not commit
- Do not push

## Task
[atomic task from PlannerAgent]

## Required Final Output
Return a JSON summary at the end:

```json
{
  "status": "success|blocked|failed",
  "summary": "...",
  "files_changed": [],
  "tests_run": [],
  "risks": [],
  "needs_rework": false
}
```
```

---

## LangGraph integration

Cada nodo ejecutor puede usar el runner:

```txt
tdd_node
  -> builds AgentExecutionSpec(agent_id="TDDAgent", mode="test_only")
  -> OpenCodeSessionRunner.run
  -> writes test_plan + test_results to SharedState

implementation_node
  -> creates BackendImplementer spec
  -> creates FrontendImplementer spec
  -> run_async both specs in worktrees
  -> collects patches/results
  -> merge/apply patches
  -> writes implementation_slots

review_node
  -> Reviewer/SecurityReviewer OpenCode read-only sessions
  -> writes reports

qa_node
  -> QAGatekeeper OpenCode read-only/test execution session
  -> gate_status pass|warn|block
```

---

## UI/App integration

La app debería mostrar cada sesión como una card:

```txt
Run: synto-20260430-001
Phase: implementation
Agent: BackendImplementer
OpenCode title: synto:run:BackendImplementer:TASK-004
Status: running|success|failed|blocked
Files changed: 8
Tests: 14 passed / 1 failed
Logs: open stdout/events
Patch: open patch
```

Backend API mínimo:

```txt
POST /api/runs/{run_id}/agents/{agent_id}/execute
GET  /api/runs/{run_id}/agents/{agent_id}/sessions
GET  /api/runs/{run_id}/agents/{agent_id}/logs
GET  /api/runs/{run_id}/agents/{agent_id}/patch
POST /api/runs/{run_id}/agents/{agent_id}/cancel
```

---

## Orden de implementación recomendado

1. Crear `AgentExecutionSpec` + `AgentRunResult`.
2. Crear `OpenCodeSessionRunner.run()` sin worktrees.
3. Integrar TDDAgent secuencial.
4. Integrar Backend/Frontend secuencial.
5. Persistir logs en `.synto/runs`.
6. Agregar worktrees para Backend/Frontend paralelo.
7. Exponer sesiones en API/UI.
8. Agregar cancel/poll/resume.

---

## Decisión importante

TDD no es "una fase de verificación posterior".

En Synto queda definido así:

```txt
PlannerAgent produce tasks
TDDAgent produce tests
Backend/Frontend implementan contra esos tests
Reviewer/QA verifican evidencia
```

Esto evita el falso TDD de escribir tests al final para justificar código ya escrito.
