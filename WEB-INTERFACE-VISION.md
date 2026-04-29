# Web Interface Vision — Synto Command Center

> Estado: visión inicial para discutir después de cerrar arquitectura del motor
> Fecha: 2026-04-28
> Objetivo: dejar prevista una interfaz web para operar el sistema multi-agente sin depender solo de CLI/Telegram.

---

## 1. Decisión

Sí, es posible crear una interfaz web para usar Synto.

Pero el orden correcto es:

1. Definir arquitectura del motor.
2. Implementar runtime mínimo LangGraph + SharedState + SkillRegistry.
3. Exponer una API local del runtime.
4. Construir la interfaz web encima.

Motivo: si diseñamos UI antes del contrato del motor, la UI queda acoplada a humo. La UI debe ser una ventana al estado real del sistema.

---

## 2. Qué problema resuelve la UI

La CLI sirve para conversar. La UI sirve para operar.

La interfaz web debería permitir:

- ver qué agentes están trabajando;
- aprobar gates;
- inspeccionar artefactos;
- ver el blackboard/shared state;
- importar y asignar skills;
- revisar logs/traces;
- gestionar design system;
- ver PRs y deploys;
- reanudar workflows pausados;
- entender por qué un agente tomó una decisión.

---

## 3. Concepto de producto

Nombre tentativo:

```text
Hermes Command Center
```

Idea:

Una interfaz tipo cockpit operativo para workflows agentic.

No debería parecer un chat genérico. Tiene que parecer un sistema profesional donde el usuario dirige equipos de agentes.

---

## 4. Pantallas principales

### 4.1 Dashboard

Objetivo:
- mostrar estado global.

Elementos:
- workflows activos;
- workflows esperando aprobación;
- errores críticos;
- agentes activos;
- costos/tokens aproximados;
- últimas ejecuciones;
- accesos rápidos.

### 4.2 Run Detail / Timeline

Objetivo:
- ver una ejecución completa.

Elementos:
- timeline de eventos;
- fase actual;
- nodos LangGraph ejecutados;
- agentes participantes;
- skills cargadas por agente;
- MCP tools usadas;
- errores/reintentos;
- checkpoints disponibles.

Vista conceptual:

```text
Discovery ── PRD ── Planning ── TDD ── Implementation ── Review ── Release
    ✓         ✓        ●          ○          ○              ○          ○
```

### 4.3 Gate Approval Center

Objetivo:
- aprobar o pedir cambios sin perder contexto.

Gates:
- PRD approval;
- spec/design approval;
- test plan approval;
- release approval;
- deploy approval.

Debe mostrar:
- artefacto a aprobar;
- cambios desde versión anterior;
- riesgos detectados;
- recomendaciones del agente;
- botones: aprobar, pedir cambios, rechazar, pausar.

### 4.4 Blackboard Viewer

Objetivo:
- visualizar el SharedState sin leer JSON crudo.

Secciones:
- meta/run;
- workflow;
- slots por agente;
- artifacts;
- gates;
- events;
- errors.

Regla:
- lectura primero;
- edición manual solo para campos seguros o modo avanzado.

### 4.5 Agent Team View

Objetivo:
- ver el equipo de agentes y qué puede hacer cada uno.

Por agente:
- rol;
- responsabilidades;
- restricciones;
- skills base;
- skills dinámicas asignadas;
- tools MCP permitidas;
- últimos runs;
- tasa de fallos;
- costo/tokens.

### 4.6 Skill Manager

Objetivo:
- que el usuario pueda agregar skills nuevas encontradas en internet y asignarlas a agentes.

Funciones:
- listar skills disponibles;
- importar desde carpeta local;
- importar desde URL/GitHub en modo inbox;
- ver trust status;
- validar skill;
- asignar a agentes;
- editar triggers;
- simular carga para una tarea;
- bloquear skill.

Flujo:

```text
Import skill → Quarantine → Validate → Approve → Assign to agent → Test trigger → Use
```

### 4.7 Design System Studio

Objetivo:
- operar el design system vivo del SystemDesigner.

Funciones:
- ver tokens;
- ver componentes;
- ver layouts;
- ver reglas UX;
- ver design reviews;
- comparar versiones;
- aprobar cambios visuales;
- inspeccionar componentes creados por FrontendImplementer.

### 4.8 Artifacts Center

Objetivo:
- acceder a los documentos generados.

Artefactos:
- discovery.md;
- prd.md;
- spec.md;
- design.md;
- design-system.json;
- test-plan.md;
- contract-report.md;
- qa-report.md;
- release-notes.md;
- PDFs;
- PR links;
- deploy reports.

### 4.9 Memory Center

Objetivo:
- inspeccionar y gobernar la memoria persistente del orchestrator.

Debe permitir:
- navegar árbol `Project -> Feature -> Topic -> MemoryItem`;
- buscar por texto, proyecto, feature, agente, tipo y status;
- ver qué memory pack recibió cada agente en un run;
- ver qué búsquedas hizo `MemoryContextAgent` y qué fuentes usó;
- auditar calls del `Memory MCP Server` sin exponer secretos;
- aprobar/rechazar memory candidates;
- resolver contradicciones;
- marcar memorias como superseded/deleted;
- ver links tipo `depends_on`, `fixes`, `affects_artifact`, `promoted_to_skill`;
- exportar/sincronizar vistas Markdown hacia Obsidian;
- ver timeline de sesiones, decisiones y bug resolutions.

No debe ser solo un listado de notas. Tiene que mostrar árbol + timeline + grafo liviano.

Referencia de diseño: `MEMORY-ARCHITECTURE-RESEARCH.md`.

### 4.10 Chat / Command Panel

Objetivo:
- mantener el punto de contacto conversacional.

No reemplaza al dashboard. Es un panel lateral para hablar con HermesOrchestrator.

Debe permitir:
- iniciar un nuevo workflow;
- responder preguntas del BusinessAnalyst;
- pedir cambios;
- consultar estado;
- aprobar gates desde conversación.

---

## 5. Arquitectura técnica posible

### Opción recomendada para discutir

```text
Frontend: React/Vite o Next.js
Backend API: FastAPI
Runtime worker: Python + LangGraph
DB: SQLite al inicio, Postgres después
Realtime: WebSocket o SSE
Observabilidad: Langfuse/Phoenix
Auth: local-first al inicio
```

### Por qué esta opción

- LangGraph está en Python, entonces FastAPI encaja naturalmente.
- React/Vite es simple para un dashboard local.
- Next.js suma si después queremos auth/routing más complejo.
- SQLite alcanza para local-first.
- Postgres entra cuando haya multiusuario o producción.

---

## 6. API backend inicial

Endpoints tentativos:

```http
GET  /api/runs
POST /api/runs
GET  /api/runs/{run_id}
POST /api/runs/{run_id}/resume
POST /api/runs/{run_id}/cancel

GET  /api/runs/{run_id}/events
GET  /api/runs/{run_id}/state
GET  /api/runs/{run_id}/artifacts
GET  /api/runs/{run_id}/artifacts/{artifact_id}

GET  /api/agents
GET  /api/agents/{agent_id}
PATCH /api/agents/{agent_id}/skills

GET  /api/skills
POST /api/skills/import
POST /api/skills/{skill_id}/validate
POST /api/skills/{skill_id}/approve
POST /api/skills/{skill_id}/block

GET  /api/design-system/{project_id}
PATCH /api/design-system/{project_id}

GET  /api/memory/projects/{project_id}/tree
GET  /api/memory/items
GET  /api/memory/items/{memory_id}
GET  /api/memory/search
POST /api/memory/build-pack
GET  /api/memory/mcp/audit
GET  /api/memory/candidates
POST /api/memory/candidates/{candidate_id}/approve
POST /api/memory/candidates/{candidate_id}/reject
POST /api/memory/items/{memory_id}/forget
POST /api/memory/items/{memory_id}/supersede
GET  /api/memory/runs/{run_id}/packs
POST /api/memory/export/obsidian

POST /api/approvals/{approval_id}/approve
POST /api/approvals/{approval_id}/request-changes
POST /api/approvals/{approval_id}/reject
```

Realtime:

```http
GET /api/runs/{run_id}/stream
```

Eventos SSE/WebSocket:

```json
{ "type": "agent.started", "agent": "Planner", "run_id": "..." }
{ "type": "gate.pending", "gate": "prd_gate", "run_id": "..." }
{ "type": "skill.loaded", "agent": "FrontendImplementer", "skill": "frontend-design" }
```

---

## 7. Datos que la UI necesita del motor

La UI no debe parsear logs sueltos. Debe leer contratos claros:

- `current-state.json` / API state;
- `events.jsonl` / event stream;
- `AGENT-REGISTRY.yaml`;
- `skill-registry-cache.json`;
- artifacts versionados;
- design-system.json;
- checkpoint metadata.

---

## 8. Modo local-first

Primera versión:

- corre en la máquina del usuario;
- se conecta al runtime local;
- no requiere SaaS;
- usa SQLite/filesystem;
- permite abrir `http://localhost:xxxx`;
- opcionalmente se expone por Cloudflare Tunnel si el usuario quiere verlo desde celular.

Esto respeta la preferencia de evitar servicios pagos y priorizar local/gratis.

---

## 9. Diseño visual — dirección inicial

No definir estética final todavía. Pero sí reglas:

- Evitar UI genérica de chat IA.
- Priorizar cockpit operativo.
- Timeline y estado por encima de bubbles de chat.
- Panel lateral para conversación, no pantalla completa de chat.
- Visualizar equipos de agentes como unidades de trabajo.
- Hacer que gates y decisiones sean obvios.
- Diseñar con densidad profesional, pero sin volverse enterprise pesado.

---

## 10. Roles de usuario futuros

MVP:
- single user local.

Futuro:
- owner;
- reviewer;
- viewer;
- agent admin;
- deploy approver.

No implementar multiusuario antes de necesitarlo.

---

## 11. Seguridad

La UI puede operar herramientas potentes, por eso:

- confirmación para acciones destructivas;
- no mostrar secretos completos;
- redacción de tokens;
- audit log;
- permisos por agente/tool;
- importación de skills en quarantine;
- deploy siempre con approval.

---

## 12. MVP de UI propuesto

Primera UI mínima útil:

1. Run dashboard.
2. Run detail con timeline.
3. Gate approval panel.
4. Artifacts viewer.
5. Agent list con skills asignadas.
6. Skill Manager básico.
7. Memory Center básico: búsqueda, árbol por proyecto/feature y candidates.

No incluir de entrada:

- edición visual avanzada del design system;
- multiusuario;
- analíticas complejas;
- marketplace de skills;
- A2A explorer.

---

## 13. Preguntas para definir más adelante

Cuando terminemos la documentación de arquitectura, charlar estos puntos:

1. ¿La UI será local-only o también remota?
2. ¿Preferís Vite/React simple o Next.js?
3. ¿Querés backend FastAPI o NestJS?
4. ¿La UI debe integrarse con Telegram o reemplazarlo parcialmente?
5. ¿Qué tan visual querés el grafo de agentes?
6. ¿Querés editor manual de `design-system.json` o solo viewer al principio?
7. ¿Querés importar skills desde GitHub URL directo?
8. ¿Querés aprobar gates desde web, Telegram, o ambos?
9. ¿Debe mostrar costos/tokens desde el día 1?
10. ¿La UI debería poder lanzar OpenCode/Codex/Claude manualmente o solo vía workflow?

---

## 14. Decisión de timing

No implementar UI antes de:

- tener AgentRegistry funcional;
- tener SkillRegistry funcional;
- tener SharedState serializable;
- tener un workflow mínimo que genere eventos reales.

Sí diseñarla/documentarla antes, para que el motor nazca UI-ready.

---

## 15. Criterio de listo para empezar UI

Podemos empezar UI cuando exista:

- `GET /api/runs` o equivalente local;
- un `current-state.json` estable;
- eventos JSONL consistentes;
- artifacts versionados;
- AgentRegistry parseable;
- SkillRegistry parseable;
- al menos un workflow Code corriendo de punta a punta en modo mock o real.
