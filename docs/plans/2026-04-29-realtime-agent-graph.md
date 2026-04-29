# Realtime Agent Graph + UI Simplification Implementation Plan

> **For Hermes:** Use `subagent-driven-development` skill to implement this plan task-by-task.

**Goal:** simplificar el Synto Command Center y agregar una vista en tiempo real tipo grafo para ver qué agentes se van llamando durante un workflow.

**Architecture:** mantener el enfoque local-first actual: FastAPI + frontend estático vanilla JS, sin sumar SaaS ni dependencias pesadas. La fuente de verdad para el grafo deben ser eventos persistidos del runtime (`state/events.jsonl`) y/o eventos emitidos por LangGraph durante la ejecución. La UI consume esos eventos por API/SSE, deriva nodos/aristas y permite clickear un agente para ver su resumen.

**Tech Stack:** Python 3.12, FastAPI, LangGraph runtime existente, `WorkflowStateStore`, `AGENT-REGISTRY.yaml`, HTML/CSS/JS vanilla, SVG para grafo interactivo.

---

## Contexto y feedback

El MVP web actual gusta, pero se siente demasiado cargado. La próxima iteración debería ir hacia una cabina más simple, menos decorativa y más operativa.

Feedback a incorporar:

- Hacer la UI más sencilla.
- Mejorar la estética general: menos “AI dashboard/Hawaii”, más herramienta seria de trabajo.
- Dar protagonismo al run actual y a lo que está pasando en vivo.
- Mostrar visualmente qué agente llama a cuál durante una feature/workflow.
- Permitir clickear un nodo/agente para ver un resumen de ese agente y su actividad en el run.
- Planificar primero; implementar después.

---

## Decisión de diseño

### Dirección visual

Pasar de “cockpit con muchas tarjetas” a “workbench operativo”.

Principios:

- Menos secciones visibles por defecto.
- Menos copy repetido.
- Menos cards anidadas.
- Paleta más sobria: papel claro, tinta, cobre suave/acento mínimo.
- La pantalla principal debe responder rápido: “qué está corriendo, quién está trabajando, qué necesita mi aprobación”.
- Agentes, skills, memoria y design system pasan a un modo avanzado o panel secundario.

### Layout objetivo

Pantalla principal:

1. Header compacto
   - Estado del sistema.
   - Run seleccionado.
   - Botón “Nuevo run”.

2. Columna izquierda: Runs
   - Historial breve.
   - Estado.
   - Filtro mínimo.

3. Centro: Agent Graph Live
   - Grafo SVG con agentes.
   - Nodo activo resaltado.
   - Aristas animadas cuando hay handoff/call.
   - Gates marcados como nodos especiales.

4. Columna derecha: Inspector
   - Si no hay nodo seleccionado: resumen del run.
   - Si hay agente seleccionado: resumen del agente + actividad en este run.
   - Si hay gate seleccionado: acciones aprobar / pedir cambios / rechazar.

5. Parte inferior opcional: Timeline compacto
   - Eventos recientes.
   - Colapsable.

---

## Modelo conceptual del grafo

### Nodo

Representa un agente o gate.

Campos mínimos:

```json
{
  "id": "Planner",
  "type": "agent",
  "label": "Planner",
  "domain": "planning",
  "layer": 2,
  "status": "idle|running|completed|failed|waiting",
  "started_at": "2026-04-29T...",
  "finished_at": "2026-04-29T...",
  "calls": 3,
  "failures": 0,
  "last_event": "agent.completed"
}
```

### Arista

Representa handoff, dependencia, llamada o transición entre agentes.

Campos mínimos:

```json
{
  "id": "HermesOrchestrator->Planner:1",
  "source": "HermesOrchestrator",
  "target": "Planner",
  "type": "handoff|langgraph_edge|gate|retry",
  "status": "active|completed|failed",
  "count": 1,
  "last_event_at": "2026-04-29T..."
}
```

### Inspector de agente

Al clickear un nodo agente, mostrar:

- nombre;
- rol desde `AGENT-REGISTRY.yaml`;
- dominio/layer/model profile;
- skills base;
- capabilities;
- cantidad de veces llamado en el run;
- duración aproximada;
- estado actual;
- último evento;
- artifacts producidos, si aplica;
- errores/fallbacks, si aplica;
- resumen corto generado de forma local/derivada, sin llamar LLM por defecto.

No mostrar prompts completos, secrets, tokens, auth, API keys ni payloads sensibles.

---

## Eventos necesarios

Agregar o normalizar eventos del runtime con estos tipos:

- `run.started`
- `run.completed`
- `run.failed`
- `agent.started`
- `agent.completed`
- `agent.failed`
- `agent.handoff`
- `agent.retry`
- `gate.waiting`
- `gate.approved`
- `gate.changes_requested`
- `gate.rejected`
- `artifact.created`
- `llm.fallback`

Formato recomendado:

```json
{
  "event_id": "uuid",
  "ts": "2026-04-29T13:00:00Z",
  "run_id": "...",
  "thread_id": "...",
  "type": "agent.started",
  "agent": "Planner",
  "source_agent": "HermesOrchestrator",
  "target_agent": "Planner",
  "phase": "planning",
  "status": "running",
  "summary": "Planner started implementation plan",
  "metadata": {
    "node": "planner",
    "attempt": 1
  }
}
```

---

## API objetivo

### `GET /api/runs/{run_id}/graph`

Devuelve snapshot derivado desde eventos + registry.

Respuesta:

```json
{
  "run_id": "...",
  "thread_id": "...",
  "updated_at": "...",
  "nodes": [],
  "edges": [],
  "selected": null,
  "stats": {
    "agents_called": 5,
    "edges": 7,
    "active_agents": 1,
    "waiting_gates": 0,
    "failures": 0
  }
}
```

### `GET /api/runs/{run_id}/agent-summary/{agent_id}`

Devuelve resumen seguro del agente en contexto del run.

Respuesta:

```json
{
  "agent_id": "Planner",
  "registry": {},
  "run_activity": {
    "calls": 1,
    "status": "completed",
    "duration_ms": 3200,
    "events": []
  },
  "artifacts": [],
  "safe_summary": "Planner transformed the PRD into implementation tasks."
}
```

### `GET /api/runs/{run_id}/stream`

SSE para eventos nuevos.

Evento ejemplo:

```text
event: agent.completed
data: {"run_id":"...","agent":"Planner"}
```

Si SSE ya existe o hay endpoint similar, extenderlo en vez de duplicar.

---

## Tasks de implementación

### Task 1: Crear tests del builder de grafo

**Objective:** definir el contrato antes de tocar UI.

**Files:**
- Create: `tests/web/test_agent_graph.py`
- Modify: ninguno todavía

**Steps:**

1. Crear fixtures con eventos `agent.started`, `agent.handoff`, `agent.completed`, `gate.waiting`.
2. Testear que el builder devuelve nodos únicos.
3. Testear que las aristas agregan `count` cuando se repite un handoff.
4. Testear que un agente activo queda `status=running`.
5. Testear que un gate aparece como nodo `type=gate`.

**Command:**

```bash
.venv/bin/python -m pytest tests/web/test_agent_graph.py -q
```

**Expected:** falla porque el builder todavía no existe.

---

### Task 2: Implementar builder puro de grafo

**Objective:** tener lógica testeable sin depender de FastAPI ni del DOM.

**Files:**
- Create: `src/synto/web/agent_graph.py`
- Test: `tests/web/test_agent_graph.py`

**Implementation outline:**

- Función `build_agent_graph(events, agents_registry) -> dict`.
- No leer archivos dentro del builder.
- No llamar LLM.
- Sanitizar todo string que venga de eventos.
- Derivar `nodes`, `edges`, `stats`.

**Command:**

```bash
.venv/bin/python -m pytest tests/web/test_agent_graph.py -q
```

**Expected:** tests pasan.

---

### Task 3: Agregar endpoint `/api/runs/{run_id}/graph`

**Objective:** exponer snapshot de grafo desde el backend web.

**Files:**
- Modify: `src/synto/web/app.py`
- Modify: `tests/web/test_app.py`

**Steps:**

1. Leer eventos actuales del run con la función existente usada por `/api/runs/{run_id}/events`.
2. Cargar registry con `AgentRegistry`.
3. Llamar `build_agent_graph(...)`.
4. Devolver JSON estable aunque el run no tenga eventos.
5. Agregar test con `TestClient`.

**Command:**

```bash
.venv/bin/python -m pytest tests/web/test_app.py tests/web/test_agent_graph.py -q
```

---

### Task 4: Instrumentar eventos de agente en el runtime

**Objective:** que el grafo represente ejecución real, no solo eventos genéricos.

**Files:**
- Modify: `src/synto/workflows/orchestrator.py`
- Possibly modify: `src/synto/state/store.py`
- Test: `tests/workflows/*` o nuevo `tests/workflows/test_agent_events.py`

**Steps:**

1. Identificar wrappers/nodos donde se ejecutan agentes especializados.
2. Antes de ejecutar cada agente, emitir `agent.started`.
3. Al completar, emitir `agent.completed` con duración y artifact ids si existen.
4. En excepción, emitir `agent.failed` con mensaje redactado.
5. Cuando el orquestador derive a otro agente, emitir `agent.handoff` con `source_agent` y `target_agent`.
6. Asegurar que `WorkflowStateStore.append_events()` redactie secrets como hoy.

**Verification:**

```bash
.venv/bin/python -m pytest tests/workflows -q
.venv/bin/python -m pytest tests/web/test_agent_graph.py -q
```

---

### Task 5: Normalizar gates como eventos de grafo

**Objective:** que los puntos de aprobación aparezcan en la misma visualización.

**Files:**
- Modify: `src/synto/workflows/orchestrator.py`
- Modify: `src/synto/web/app.py` si resume/approvals necesitan eventos extra
- Test: `tests/workflows/test_runtime_pause_resume.py`

**Steps:**

1. Emitir `gate.waiting` cuando el runtime interrumpe en un gate.
2. Emitir `gate.approved`, `gate.changes_requested` o `gate.rejected` al resumir desde API.
3. Builder debe crear nodo gate y edge desde el último agente relevante.

---

### Task 6: Agregar polling/SSE compatible para grafo vivo

**Objective:** tener actualización en tiempo real sin recargar toda la página.

**Files:**
- Modify: `src/synto/web/app.py`
- Test: `tests/web/test_app.py`

**Approach:**

- Preferir SSE con `StreamingResponse`.
- Mantener fallback por polling cada 2s desde frontend si SSE falla.
- Usar cursor simple por índice/event count, no inventar infraestructura pesada.

**Endpoint:**

```http
GET /api/runs/{run_id}/stream?cursor=0
```

---

### Task 7: Crear componente visual `AgentGraphView`

**Objective:** dibujar grafo interactivo en el frontend sin dependencia pesada.

**Files:**
- Modify: `src/synto/web/static/index.html`
- Modify: `src/synto/web/static/app.js`
- Modify: `src/synto/web/static/styles.css`

**Implementation outline:**

- Usar `<svg>`.
- Layout inicial determinístico por `layer` y orden del registry.
- Nodos como `<g>` con círculo/rect compacto y label.
- Aristas como `<path>` con marcador de flecha.
- Clase `.is-active`, `.is-completed`, `.is-failed`, `.is-waiting`.
- Click en nodo actualiza `state.selectedGraphNode` y renderiza inspector.
- No usar D3 en primera versión.

**Acceptance:**

- Si hay 0 eventos: mostrar empty state útil.
- Si hay eventos: grafo renderiza agentes conectados.
- Click en agente abre inspector.
- Click en gate muestra acciones si aplica.

---

### Task 8: Crear inspector de agente

**Objective:** mostrar contexto útil sin saturar.

**Files:**
- Modify: `src/synto/web/static/app.js`
- Modify: `src/synto/web/static/styles.css`
- Modify: `src/synto/web/app.py` para endpoint summary si hace falta

**Contenido del inspector:**

- Rol y descripción corta.
- Skills/capabilities más relevantes.
- Estado en el run.
- Cantidad de eventos.
- Últimos 5 eventos.
- Artifacts generados.
- Fallbacks/errores si existen.

---

### Task 9: Simplificar navegación y jerarquía de la UI

**Objective:** bajar complejidad visual sin perder funcionalidad.

**Files:**
- Modify: `src/synto/web/static/index.html`
- Modify: `src/synto/web/static/styles.css`
- Modify: `src/synto/web/static/app.js`

**Changes:**

- Dashboard pasa a “Runs”.
- Run detail + Gates + Artifacts se integran en una vista “Run”.
- Agents + Skills + Memory + Design System pasan a “Advanced”.
- Reducir cantidad de panels visibles al cargar.
- Usar progressive disclosure: avanzado colapsado.
- Hacer que el grafo sea el centro de la experiencia.

---

### Task 10: Rehacer visual polish hacia workbench sobrio

**Objective:** corregir la estética que hoy no termina de cerrar.

**Files:**
- Modify: `src/synto/web/static/styles.css`

**Design notes:**

- Menos gradientes y sombras.
- Más líneas finas, separadores y grilla tranquila.
- Tipografía más sobria; evitar sensación de landing page.
- Reducir border-radius excesivo.
- Botones con jerarquía clara: primary solo para acción principal.
- Estados visuales del grafo claros y accesibles.

**Acceptance:**

- La UI se siente como herramienta de ingeniería, no demo decorativa.
- En 5 segundos se entiende dónde iniciar un run y dónde mirar progreso.

---

### Task 11: Tests E2E livianos de frontend renderizado

**Objective:** asegurar que no se rompa el Command Center básico.

**Files:**
- Modify/Create: `tests/web/test_static_ui.py` o ampliar `tests/web/test_app.py`

**Tests:**

- `/` contiene contenedor del grafo.
- `/api/runs/{run_id}/graph` responde estable con run fixture.
- `/api/runs/{run_id}/agent-summary/{agent_id}` no filtra campos sensibles.
- Static assets responden 200.

---

### Task 12: Docs y verificación final

**Objective:** dejar documentado cómo usar la feature.

**Files:**
- Modify: `README.md`
- Modify: `WEB-INTERFACE-VISION.md`
- Possibly modify: `docs/plans/2026-04-29-realtime-agent-graph.md` marcando estado implementado

**Commands:**

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m synto.cli web --port 8788
```

Manual QA:

1. Abrir `http://127.0.0.1:8788`.
2. Crear run de prueba.
3. Ver nodos aparecer/actualizarse.
4. Clickear `Planner` o agente equivalente.
5. Validar inspector.
6. Aprobar/rechazar gate desde UI si aparece.
7. Confirmar que no se muestran secrets.

---

## Riesgos y mitigaciones

### Riesgo: LangGraph no expone todas las transiciones de forma simple

Mitigación: no depender de introspección interna. Emitir eventos propios en wrappers/nodos del runtime.

### Riesgo: SSE complica tests o servidores locales

Mitigación: implementar fallback por polling. SSE suma experiencia, polling garantiza funcionamiento.

### Riesgo: grafo se vuelve ilegible con 21 agentes

Mitigación: mostrar solo agentes involucrados en el run por defecto. Botón “mostrar equipo completo” opcional.

### Riesgo: mostrar datos sensibles en inspector

Mitigación: usar redacción existente de `WorkflowStateStore`; nunca renderizar prompts completos ni env/auth.

### Riesgo: sumar una librería de grafo pesada

Mitigación: primera versión con SVG propio. Si luego hace falta, evaluar Cytoscape.js o React Flow, pero no ahora.

---

## Criterios de aceptación final

- La UI inicial queda más simple y menos cargada.
- El run activo muestra un grafo vivo de agentes involucrados.
- Los nodos cambian de estado: idle/running/completed/failed/waiting.
- Las aristas muestran handoffs/calls entre agentes.
- Click en agente abre inspector con registry + actividad del run.
- Gates aparecen como nodos accionables o resaltados.
- La feature funciona sin servicios pagos ni tokens extra.
- Tests backend pasan.
- No se filtran secrets.
- El frontend mantiene fallback si SSE no está disponible.

---

## Implementación recomendada

Primera tanda:

1. Builder puro + endpoint `/graph`.
2. UI con SVG estático derivado de eventos existentes.
3. Inspector de agente.
4. Simplificación visual.

Segunda tanda:

1. Instrumentación fina del runtime.
2. SSE real.
3. Animaciones de handoff.
4. Gate nodes accionables.

Este orden permite mejorar rápido lo visual sin bloquearse con la parte más delicada del runtime.
