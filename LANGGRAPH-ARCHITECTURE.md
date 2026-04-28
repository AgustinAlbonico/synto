# Arquitectura LangGraph + MCP + Skill Registry Dinámico

> Estado: propuesta base congelada para implementación
> Fecha: 2026-04-28
> Decisión principal: reemplazar el prototipo Agency Swarm por una arquitectura productizable basada en LangGraph, MCP y carga dinámica de skills.

---

## 1. Objetivo

Construir un sistema de orquestación multi-agente para Hermes que funcione como un equipo de desarrollo real:

- Un único punto de contacto con el usuario.
- Agentes con roles estrictamente definidos.
- Skills cargadas por agente, no globalmente.
- Skills dinámicas agregables después por el usuario.
- Agentes paralelos coordinados por un blackboard/shared state.
- Memoria persistente cross-session para rehidratar contexto automáticamente.
- Gates humanos para PRD, diseño, implementación, QA y release.
- Soporte futuro para interfaz web.

La meta NO es crear otro chatbot. La meta es tener un sistema operativo de trabajo agentic: análisis, PRD, planificación, diseño, implementación, testing, review, documentación, PR y deploy.

---

## 2. Decisiones de arquitectura

| Decisión | Elección | Motivo |
|---|---|---|
| Framework principal | LangGraph | Stateful, checkpointing, sub-grafos, human-in-the-loop, recuperación de errores. |
| Herramientas externas | MCP | Estándar para agent-to-tool. Evita integraciones custom por agente. |
| Comunicación entre agentes propios | SharedState / Blackboard | Más simple y controlable que A2A para agentes dentro del mismo sistema. |
| Memoria cross-session | PersistentMemory / MemoryStore | Rehidrata contexto entre sesiones sin cargar toda la historia en el prompt. |
| Acceso a memoria | Memory MCP Server + MemoryContextAgent | Los agentes reciben memory packs chicos; no consultan SQLite ni cargan toda la memoria. |
| A2A | Futuro / opcional | Útil para agentes externos o cross-framework, no necesario para el MVP. |
| Skills | Skill Registry dinámico | Cada agente carga solo lo necesario y puede recibir nuevas skills después. |
| Observabilidad | Langfuse o Phoenix self-hosted | No construir tracing/evals desde cero. |
| UI Web | Fase posterior documentada | Primero motor estable, después interfaz. |
| Modelo base | Multi-provider | Evitar lock-in. Preferidos actuales: GLM 5.1 vía Z.AI para máxima complejidad, Kimi K2.6 vía Moonshot para pesado intermedio. |

---

## 3. Principios no negociables

1. No se implementa sin PRD aprobado.
2. No se codea sin Test Plan.
3. Ningún agente carga todo el repertorio de skills.
4. Cada agente escribe solo en su slot asignado del blackboard.
5. Los artefactos canónicos los escribe un consolidador/orquestador, no los workers paralelos.
6. El usuario habla con un punto de contacto: HermesOrchestrator.
7. Los agentes funcionales pueden proponer preguntas al usuario, pero HermesOrchestrator las presenta.
8. El diseño visual vive en un artefacto persistente: `design-system.json`.
9. La memoria cross-session vive en `PersistentMemory`, no en prompts gigantes ni en el SharedState de un run.
10. Los agentes no consultan SQLite directo: piden memoria vía `Memory MCP Server` y reciben packs del `MemoryContextAgent`.
11. Frontend y Backend no se asumen compatibles: ContractAligner lo valida explícitamente.
12. Toda skill nueva entra por validación antes de poder asignarse.

---

## 4. Vista general

```text
Usuario
  │
  ▼
HermesOrchestrator
  │
  ├── CodeOrchestrator
  │     ├── Discovery & Product
  │     │     ├── BusinessAnalyst
  │     │     └── ProductManager
  │     ├── Planning & Design
  │     │     ├── Planner
  │     │     ├── CodebaseExplorer
  │     │     ├── Architect
  │     │     └── SystemDesigner
  │     ├── TDD
  │     │     └── Tester
  │     ├── Implementation
  │     │     ├── BackendImplementer
  │     │     ├── FrontendImplementer
  │     │     └── SystemDesigner review loop
  │     ├── Alignment
  │     │     └── ContractAligner
  │     ├── Review
  │     │     ├── Reviewer
  │     │     ├── SecurityReviewer
  │     │     └── Tester
  │     ├── QA & Docs
  │     │     ├── QAGatekeeper
  │     │     ├── DependencyChecker
  │     │     └── TechnicalWriter
  │     └── Release & Deploy
  │           ├── ReleaseManager
  │           └── Builder
  │
  └── Otros domain orchestrators futuros:
        Research, Content, Business, UX, Data, DevOps standalone

MCP Layer:
  filesystem, github, terminal, web/search, browser, database, memory-mcp, etc.

Memory Layer:
  MemoryContextAgent -> Memory MCP Server -> MemoryStore(SQLite/FTS5)
  MemoryManager consolida candidatos y exporta a Obsidian

SharedState / Blackboard:
  artifacts, slots, gates, approvals, events, checkpoints, memory_context.by_agent
```

---

## 5. Capas

### Capa 0: HermesOrchestrator

Responsabilidad:
- Recibir la intención del usuario.
- Mantener el hilo conversacional.
- Decidir qué domain orchestrator activar.
- Presentar preguntas, gates y resultados.
- Nunca codear, nunca hacer research técnico profundo, nunca ejecutar deploy directamente.

### Capa 1: Domain Orchestrators

Para el MVP se implementa primero `CodeOrchestrator`.

Responsabilidad:
- Coordinar el sub-grafo del dominio.
- Activar agentes especializados.
- Consolidar resultados.
- Controlar gates.
- Manejar reintentos.

### Capa 2: Specialist Agents

Agentes con rol específico. No tienen permisos globales. Cada uno tiene:
- Inputs definidos.
- Outputs definidos.
- Skills base.
- Skills dinámicas permitidas.
- Tools MCP permitidas.
- Restricciones explícitas.
- Slot de escritura propio.

### Capa 3: Tools / MCP

Las tools no razonan. Ejecutan.

Ejemplos:
- filesystem MCP
- GitHub MCP
- terminal/shell wrapper
- web search/extract
- browser automation
- database MCP
- future: Figma, Linear, Notion, Slack/Telegram, etc.

---

## 6. Workflow SDD completo

```text
0. Intake
   HermesOrchestrator entiende la intención y crea run_id.

1. Discovery
   BusinessAnalyst analiza el problema, detecta huecos y genera preguntas.
   HermesOrchestrator pregunta al usuario.
   Output: discovery.md / discovery object.

2. PRD
   ProductManager convierte discovery en PRD.
   Gate: usuario aprueba PRD.
   Output: prd.md.

3. Technical Planning paralelo
   Planner: task graph y dependencias.
   CodebaseExplorer: mapa del repo.
   Architect: diseño técnico backend/API/datos.
   SystemDesigner: diseño UI/UX y design-system.json.
   Output: planning slots.

4. Consolidation
   CodeOrchestrator consolida spec.md, design.md, task-graph.json.
   Gate: usuario aprueba spec/diseño si corresponde.

5. TDD
   Tester escribe test-plan.md y tests iniciales.
   Gate: test plan existe y cubre criterios de aceptación.

6. Implementation paralelo
   BackendImplementer trabaja backend.
   FrontendImplementer trabaja frontend.
   SystemDesigner valida cada componente o pantalla.
   Output: backend_code slot, frontend_code slot, design_reviews.

7. Contract Alignment
   ContractAligner verifica endpoints, DTOs, schemas, hooks y tipos.
   Output: contract-report.md.

8. Review paralelo
   Reviewer: calidad y mantenibilidad.
   SecurityReviewer: OWASP, secrets, vulnerabilidades.
   Tester: ejecuta suite.
   Output: review reports.

9. QA Gate + Docs
   QAGatekeeper valida contra PRD/spec/design system.
   DependencyChecker valida impacto/breaking changes.
   TechnicalWriter genera docs, changelog y PDFs si aplica.

10. Release
   ReleaseManager arma branch/commit/PR/release notes.
   Builder despliega si hay aprobación.

11. Delivery
   HermesOrchestrator presenta resultado, links, archivos, estado y próximos pasos.
```

---

## 7. Paralelismo seguro

LangGraph permite fan-out/fan-in. El paralelismo se usa solo cuando los agentes pueden trabajar sin pisarse.

### Fan-out permitido

- Planner + CodebaseExplorer + Architect + SystemDesigner después del PRD.
- BackendImplementer + FrontendImplementer después del test plan.
- Reviewer + SecurityReviewer + Tester después de implementación.
- QAGatekeeper + DependencyChecker + TechnicalWriter después de reviews.

### Fan-in obligatorio

Todo fan-out vuelve a un nodo consolidador:

- PlanningConsolidator.
- ContractAligner.
- ReviewConsolidator.
- ReleaseManager.

### Regla anti-pisada

Un worker paralelo nunca escribe artefactos canónicos. Escribe su slot:

```text
planner_slot
explorer_slot
architect_slot
system_designer_slot
backend_slot
frontend_slot
reviewer_slot
security_slot
tester_slot
```

El orquestador consolida esos slots en artefactos canónicos:

```text
prd.md
spec.md
design.md
design-system.json
test-plan.md
contract-report.md
qa-report.md
release-notes.md
```

---

## 8. SystemDesigner como fuente viva de UI/UX

SystemDesigner no es un decorador visual. Es dueño del diseño del producto.

Artefacto principal:

```text
workspace/.hermes-state/projects/{project_id}/design/design-system.json
```

Contiene:
- tokens: colores, spacing, typography, radius, shadows.
- component library: Button, Modal, Table, Form, Card, Layout, etc.
- page patterns: dashboard, auth, forms, CRUD, detail pages.
- UX rules: loading, empty states, errors, confirmations.
- accessibility rules.
- visual API contracts: qué data alimenta cada componente.

Loop:

```text
FrontendImplementer propone/implementa componente
  ▼
SystemDesigner valida contra design-system.json
  ├── approved → sigue
  └── needs_fix → feedback concreto y vuelve a FrontendImplementer
```

SystemDesigner puede actualizar `design-system.json`, pero debe registrar cambio y razón.

---

## 9. Skill Registry dinámico

La arquitectura usa dos niveles:

1. Agent Registry: qué puede hacer cada agente.
2. Skill Registry: qué skills existen y bajo qué condiciones se cargan.

Carga:

```text
base_skills(agent)
+ manual_assignments(agent)
+ phase_required_skills(phase)
+ trigger_matched_skills(task_context)
- denied_skills(agent)
= candidate_skills

candidate_skills → ranking → budget → lazy load
```

No se inyecta el contenido completo de todas las skills. Primero se carga metadata. El contenido completo se carga solo cuando:

- la skill es base required;
- un trigger fuerte matchea;
- el agente la solicita y está permitida;
- el usuario la asignó manualmente.

Detalles en `SKILL-LOADING-SYSTEM.md`.

---

## 10. MCP

MCP se usa para tools externas. Los agentes no deberían conocer implementaciones concretas de APIs.

Ejemplo:

```text
FrontendImplementer necesita leer archivos
  → tool capability: filesystem.read
  → resuelto por MCP filesystem

ReleaseManager necesita crear PR
  → tool capability: github.pull_request.create
  → resuelto por MCP GitHub
```

Los permisos MCP se asignan por agente en `AGENT-REGISTRY.yaml`.

---

## 11. Observabilidad

Requerido para producción:

- trazas por run_id;
- eventos por nodo/agente;
- input/output truncado y seguro;
- costo/tokens por agente;
- errores y reintentos;
- decisiones de gates;
- feedback humano;
- snapshots de SharedState.

Opción inicial:
- LangGraph checkpointing + logs JSON locales.

Opción producción:
- Langfuse self-hosted o Phoenix.

---

## 12. Interfaz web futura

Sí, es posible y recomendable. No se implementa antes del motor, pero queda prevista como capa de operación.

La UI web debería permitir:

- iniciar workflows;
- ver agentes activos;
- aprobar gates;
- ver blackboard/shared state;
- inspeccionar artefactos;
- importar/asignar skills;
- editar design system;
- ver trazas, costos y errores;
- ver PRs/deploys;
- conversar con HermesOrchestrator.

La visión inicial está documentada en `WEB-INTERFACE-VISION.md`.

---

## 13. Roadmap recomendado

### Fase A — Documentación y contrato

- `LANGGRAPH-ARCHITECTURE.md`
- `AGENT-REGISTRY.yaml`
- `SKILL-LOADING-SYSTEM.md`
- `SHARED-STATE-SPEC.md`
- `WEB-INTERFACE-VISION.md`

### Fase B — Motor mínimo

- LangGraph runtime.
- AgentRegistry loader.
- SkillRegistry scanner.
- SharedState Pydantic models.
- Checkpointer local.

### Fase C — Code workflow MVP

- HermesOrchestrator.
- CodeOrchestrator.
- BusinessAnalyst.
- ProductManager.
- Planner.
- CodebaseExplorer.
- Architect.
- SystemDesigner.

### Fase D — Implementación completa

- Tester.
- BackendImplementer.
- FrontendImplementer.
- ContractAligner.
- Reviewer.
- SecurityReviewer.
- QAGatekeeper.
- TechnicalWriter.
- ReleaseManager.
- Builder.

### Fase E — UI Web

- Dashboard local.
- Skill manager.
- Gate approvals.
- Design system viewer/editor.
- Run timeline.

---

## 14. Pendientes abiertos

Estos puntos se definen antes de implementar UI o producción:

- Base de datos para checkpoints: SQLite local vs Postgres.
- UI stack: Next.js vs Vite/React.
- Backend de la UI: FastAPI vs Node/NestJS.
- Observabilidad: Langfuse vs Phoenix.
- Nivel de autonomía: automático vs confirmación por fase.
- Importación de skills externas: validación estricta y sandboxing.
- Política de commits/PR: auto-commit por task vs branch por feature.
