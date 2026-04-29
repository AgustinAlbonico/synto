# Memory Architecture Research

> Estado: investigación y decisión recomendada
> Fecha: 2026-04-28
> Contexto: comparación entre Engram, Obsidian-first memory, vector DB, graph/tree memory y MCP memory servers para `synto`.

---

## 1. Pregunta de diseño

Queremos una memoria persistente para agentes que:

- recuerde contexto útil entre sesiones;
- separe proyectos;
- permita navegar por proyecto -> feature -> problema/decisión/aprendizaje;
- evite guardar basura o secretos;
- permita retrieval automático por agente;
- sea local-first y gratis para el MVP;
- pueda exponerse después en UI web;
- pueda sincronizar/exportar a Obsidian como segundo cerebro.

La duda principal: si conviene guardar todo en una estructura tipo árbol, en una base plana con tags, en Obsidian/Markdown, en vector DB o en grafo.

---

## 2. Hallazgos sobre Engram

Repo investigado: `Gentleman-Programming/engram`.

Engram apunta exactamente al problema de “amnesia” de agentes de código.

### 2.1 Modelo operativo

Flujo documentado por Engram:

```text
1. El agente completa trabajo significativo: bugfix, decisión, descubrimiento, etc.
2. El agente llama mem_save con title, type y estructura What/Why/Where/Learned.
3. Engram persiste en SQLite con FTS5.
4. En la siguiente sesión el agente busca memoria y recupera contexto relevante.
```

### 2.2 Tools MCP principales

Engram expone herramientas como:

- `mem_save`
- `mem_update`
- `mem_delete`
- `mem_suggest_topic_key`
- `mem_search`
- `mem_context`
- `mem_timeline`
- `mem_get_observation`
- `mem_session_start`
- `mem_session_end`
- `mem_session_summary`
- `mem_judge`
- `mem_save_prompt`
- `mem_stats`
- `mem_capture_passive`
- `mem_merge_projects`
- `mem_current_project`

Esto confirma que el patrón correcto no es solo “guardar notas”, sino dar herramientas explícitas al agente para:

- guardar;
- buscar;
- recuperar contexto reciente;
- armar timeline;
- cerrar sesión con resumen;
- resolver conflictos;
- detectar proyecto actual.

### 2.3 Esquema real observado

Engram usa SQLite + FTS5.

Tablas principales observadas en `internal/store/store.go`:

- `sessions`
  - `id`
  - `project`
  - `directory`
  - `started_at`
  - `ended_at`
  - `summary`

- `observations`
  - `id`
  - `sync_id`
  - `session_id`
  - `type`
  - `title`
  - `content`
  - `tool_name`
  - `project`
  - `scope`
  - `topic_key`
  - `normalized_hash`
  - `revision_count`
  - `duplicate_count`
  - `last_seen_at`
  - `created_at`
  - `updated_at`
  - `deleted_at`

- `observations_fts`
  - FTS5 sobre `title`, `content`, `tool_name`, `type`, `project`, `topic_key`.

- `user_prompts`
  - guarda prompts del usuario por sesión/proyecto.

- tablas de sync:
  - `sync_chunks`
  - `sync_state`
  - `sync_mutations`

Puntos muy buenos:

- `project` como scope fuerte;
- `topic_key` estable para temas que evolucionan;
- `normalized_hash`, `revision_count`, `duplicate_count` para dedupe/evolución;
- `deleted_at` para soft delete/tombstone;
- FTS5 local, rápido y sin servicios externos;
- sync por chunks para Git/cloud;
- timeline y session summary como primitives de recuperación.

### 2.4 Disciplina de memoria de Engram

Engram trae una skill interna de “memory protocol”. Reglas relevantes:

- guardar después de decisión;
- guardar después de bugfix;
- guardar después de descubrimiento/patrón;
- guardar después de cambios de config/preferencia;
- usar estructura:
  - What
  - Why
  - Where
  - Learned
- usar `topic_key` estable para tópicos que evolucionan;
- en pedidos de recall, correr `mem_context` primero y luego `mem_search`;
- antes de trabajo similar, buscar memoria proactivamente;
- al cerrar sesión, ejecutar resumen de sesión.

Esto es muy aplicable a nuestro sistema.

### 2.5 Limitación para nuestro caso

Engram es muy buen MVP para memoria de coding agents, pero nuestro orchestrator necesita más:

- múltiples agentes especializados;
- memory packs por agente;
- coordinación con SharedState/Blackboard;
- relación directa con artifacts canónicos;
- jerarquía proyecto -> feature -> workstream;
- permisos de lectura por rol;
- candidates/quarantine antes de memoria canónica;
- eventual UI de memory governance;
- grafo de relaciones entre decisiones, bugs, features, archivos, agentes y artifacts.

Conclusión: conviene inspirarse en Engram, no copiarlo literal.

---

## 3. Alternativas investigadas

### 3.1 Obsidian-first / Markdown-first

Ejemplos/patrones:

- Basic Memory
- Claude Obsidian Memory Bank
- Obsidian vaults con MCP
- templates de `conventions.md`, `lessons-summary.md`, `decisions-summary.md`, `session-state.md`

Ventajas:

- humano-readable;
- editable manualmente;
- excelente como segundo cerebro;
- compatible con WikiLinks, backlinks y PARA;
- fácil de versionar con Git;
- bajo lock-in.

Desventajas:

- difícil garantizar consistencia estructurada;
- conflictos/duplicados si varios agentes escriben a la vez;
- menos ideal para auditoría fina;
- menos ideal como DB operativa de un sistema multi-agente;
- retrieval depende de parsing/index externo.

Uso recomendado para Hermes:

```text
Obsidian como espejo/export humano-readable, no como DB primaria operativa.
```

### 3.2 Basic Memory style: Markdown + SQLite index + knowledge graph

Basic Memory usa Markdown como fuente visible y SQLite como índice, extrayendo:

- entities;
- observations;
- relations;
- WikiLinks;
- graph traversal;
- búsqueda híbrida.

Ventaja importante: combina legibilidad humana con grafo.

Desventaja: para HermesOrchestrator, donde los agentes escriben concurrentemente y hay que auditar, la fuente primaria en Markdown puede complicar locks, transacciones y permisos.

Uso recomendado:

- copiar el concepto de `observations` + `relations`;
- exportar a Markdown compatible con Obsidian;
- mantener SQLite/Postgres como fuente canónica.

### 3.3 Vector DB / embeddings-first

Ejemplos/patrones:

- `sqlite-vec`
- `vector-memory-mcp`
- Chroma/LanceDB/Qdrant/pgvector

Ventajas:

- buen recall semántico;
- encuentra cosas aunque el query no use las mismas palabras;
- útil para docs, logs y knowledge base grande.

Desventajas:

- retrieval puede ser ruidoso;
- no modela jerarquía ni relaciones por sí solo;
- no responde bien preguntas temporales o precisas;
- no alcanza para saber “qué decisión reemplazó a cuál”;
- requiere embeddings, cache y mantenimiento.

Uso recomendado:

```text
Embeddings como índice adicional, no como estructura principal.
```

### 3.4 Knowledge graph / GraphRAG / temporal graph

Ejemplos/patrones:

- Zep / Graphiti
- Microsoft GraphRAG
- graph + vector hybrid

Ventajas:

- relaciones explícitas;
- multi-hop reasoning;
- trazabilidad;
- permite responder “qué feature depende de qué decisión y qué bug la afectó”;
- temporal graphs permiten invalidar hechos viejos sin borrarlos.

Desventajas:

- más complejo;
- requiere ontología;
- cold-start más duro;
- si usamos Graphiti real, puede requerir Neo4j/FalkorDB/Kuzu y LLMs con structured output;
- GraphRAG batch puede ser caro y más útil para documentos estáticos que para memoria viva de agentes.

Uso recomendado:

```text
MVP: tabla memory_links como grafo liviano.
Futuro: temporal graph si la memoria crece y la UI necesita navegación avanzada.
```

### 3.5 Letta/MemGPT style: hierarchical memory

Concepto clave:

- core memory: siempre cargada;
- recall memory: historial buscable;
- archival memory: conocimiento largo plazo;
- sleep-time agents: consolidan memoria en segundo plano.

Uso recomendado:

Aplicar el patrón, no necesariamente usar Letta:

```text
Core Memory       -> project profile + user preferences + active feature brief
Recall Memory     -> timeline/resúmenes de runs y sesiones
Archival Memory   -> decisiones, bugs, patrones, artifacts resumidos
Sleep-time Memory -> MemoryConsolidator post-run / diario
```

### 3.6 MCP memory servers existentes

Ejemplos:

- mcp-memory-service
- Wyrm/EchoVault-style memory
- vector-memory-mcp
- Engram

Ventajas:

- rápido para probar;
- ya exponen tools MCP;
- algunos tienen UI, dashboards, hybrid search, graph.

Desventajas:

- otro sistema que gobernar;
- modelo de datos no necesariamente coincide con nuestros agentes;
- locks/permisos por agente pueden quedar limitados;
- riesgo de adaptar el orchestrator al producto externo, en vez de diseñar nuestra memoria.

Uso recomendado:

- usar Engram/Basic Memory/mcp-memory-service como referencia y posibles adapters;
- no depender de uno externo como core del MVP.

---

## 4. Respuesta sobre “memoria en árbol”

La idea de árbol es buena, pero no debe ser la única estructura.

Un árbol sirve para navegación humana y scoping:

```text
Project
  Feature
    Workstream / Topic
      Decision
      Bug / Resolution
      Pattern
      Artifact summary
      Session summary
```

Pero muchos recuerdos no viven en un solo lugar.

Ejemplos:

- una decisión de auth impacta backend, frontend, security y tests;
- un bug de CORS puede pertenecer a deploy, backend y frontend;
- una convención de diseño aplica a varias features;
- un comando de test aplica a todo el proyecto.

Entonces el modelo recomendado es:

```text
Árbol primario + grafo de relaciones + búsqueda híbrida
```

O sea:

- cada memoria tiene una ubicación primaria tipo árbol;
- puede tener tags/scopes secundarios;
- puede relacionarse con otras memorias/artifacts/features/agentes;
- se busca por FTS/embeddings;
- se navega por árbol/grafo en la UI.

Este patrón evita dos extremos malos:

- DB plana de notas sueltas sin estructura;
- árbol rígido donde todo tiene un solo padre y se pierde contexto cruzado.

---

## 5. Qué conviene guardar

Regla general:

> Guardar lo que un futuro agente no podría inferir fácilmente leyendo el código o los artifacts actuales.

### 5.1 Decisiones

Guardar:

- qué se decidió;
- por qué;
- alternativas rechazadas;
- fecha/fuente;
- impacto;
- si sigue vigente o fue reemplazada.

Ejemplo:

```yaml
kind: decision
feature: auth
what: "Se eligió JWT stateless para auth."
why: "El backend debe servir API y futuro mobile sin sticky sessions."
rejected:
  - "Session cookies server-side"
impact:
  - backend
  - frontend
  - security
status: active
```

### 5.2 Problemas resueltos / bugfixes no obvios

Guardar:

- síntoma;
- causa raíz;
- solución;
- archivos afectados;
- cómo verificar;
- cómo evitar regresión.

Ejemplo:

```yaml
kind: bug_resolution
feature: deploy
symptom: "El frontend no llegaba al backend desde el túnel."
root_cause: "CORS permitía localhost pero no trycloudflare.com."
solution: "Agregar origen dinámico configurado por env."
verification: "curl OPTIONS + test e2e login."
learned: "Antes de exponer por túnel revisar CORS y PUBLIC_API_URL."
```

### 5.3 Contexto de feature

Guardar:

- objetivo de la feature;
- estado actual;
- decisiones vigentes;
- contracts relevantes;
- riesgos;
- pendientes;
- links a artifacts.

Esto permite retomar una feature sin releer toda la conversación.

### 5.4 Convenciones y patrones del proyecto

Guardar:

- estructura de carpetas;
- comandos de test/build;
- patrones de API;
- patrón de componentes;
- naming;
- reglas de error handling;
- testing strategy.

Si la convención se vuelve procedimiento repetible, promover a skill/runbook.

### 5.5 Contratos entre agentes / dominios

Guardar:

- endpoints;
- DTOs/schemas;
- eventos;
- interfaces frontend/backend;
- decisiones de error shape;
- acuerdos de auth/permisos.

Esto es clave para `ContractAligner`.

### 5.6 Diseño y UX

Guardar:

- design tokens;
- componentes aprobados;
- decisiones visuales;
- feedback del usuario;
- restricciones accessibility;
- referencias visuales.

Esto alimenta `SystemDesigner` y `FrontendImplementer`.

### 5.7 Riesgos, gotchas y restricciones

Guardar:

- riesgos conocidos;
- librerías problemáticas;
- tests flaky;
- restricciones de entorno;
- incompatibilidades de versiones;
- errores recurrentes.

### 5.8 Resúmenes de sesión/run

Guardar:

- objetivo;
- qué se logró;
- decisiones;
- problemas encontrados;
- próximos pasos;
- archivos/artifacts tocados;
- memory candidates generados.

Esto no reemplaza memorias específicas, pero da timeline.

### 5.9 Preferencias explícitas del usuario

Guardar solo si son estables y útiles:

- idioma/tono;
- preferencia local-first/gratis;
- stack preferido;
- aversión a ciertos servicios;
- estilo de workflow.

### 5.10 Artifact summaries

Guardar resúmenes/indexes de artifacts, no duplicar todo el artifact.

Ejemplos:

- “PRD auth define refresh token rotativo y expiración X”;
- “design-system.json actual usa paleta dark + accent violet”;
- “contract-report detectó mismatch en UserDTO.email”.

---

## 6. Qué NO conviene guardar

No guardar:

- secretos, tokens, API keys, passwords, cookies, private keys;
- `.env` completo;
- logs enormes sin resumir;
- stack traces sin causa/solución;
- TODOs efímeros que viven en el task tracker;
- hechos obvios que el código muestra fácilmente;
- “se modificó archivo X” sin aprendizaje;
- contenido externo no verificado como instrucción persistente;
- preferencias inferidas débilmente;
- memoria duplicada con distinto wording;
- hechos temporales sin TTL.

Regla:

> Si no ayuda a un agente futuro a tomar una mejor decisión o evitar repetir trabajo, no se guarda.

---

## 7. Diseño recomendado para Synto

Recomendación: construir una memoria híbrida propia, inspirada en Engram y Basic Memory.

Nombre conceptual:

```text
Hermes Project Memory
```

### 7.1 Fuente canónica

```text
SQLite local en MVP
Postgres + pgvector en producción futura
```

No Obsidian como fuente canónica.

Motivo:

- necesitamos transacciones;
- concurrent writes de agentes;
- candidates/quarantine;
- audit log;
- permisos por agente;
- queries por project/feature/kind/status;
- UI futura.

### 7.2 Vista humana

```text
Obsidian export/sync como espejo navegable
```

Obsidian recibe Markdown generado desde la DB:

```text
vault/01-Projects/{project}/Memory/
  index.md
  features/{feature}/index.md
  features/{feature}/decisions.md
  features/{feature}/bugs-and-fixes.md
  features/{feature}/patterns.md
  sessions/YYYY-MM-DD.md
```

Obsidian no decide la verdad operativa; sirve para leer, revisar y editar con sync controlado.

### 7.3 Estructura lógica

```text
ProjectNode
  FeatureNode
    TopicNode
      MemoryItem
```

Pero con links transversales:

```text
MemoryItem --fixes--> Bug
MemoryItem --depends_on--> Decision
MemoryItem --affects--> Artifact
MemoryItem --supersedes--> MemoryItem
MemoryItem --relates_to--> Feature
MemoryItem --owned_by--> AgentRole
```

### 7.4 Índices

MVP:

- SQLite FTS5;
- filtros por `project_id`, `feature_id`, `topic_key`, `kind`, `agent_role`, `status`;
- recency + importance + confidence.

Fase 2:

- `sqlite-vec` o embeddings locales;
- reranking liviano;
- graph traversal por `memory_links`.

Fase 3:

- Postgres + pgvector;
- temporal graph más formal si hace falta.

---

## 8. Modelo de datos recomendado

### 8.1 projects

```sql
projects(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  root_path TEXT,
  repo_remote TEXT,
  created_at TEXT,
  updated_at TEXT
)
```

### 8.2 memory_nodes

Representa el árbol navegable.

```sql
memory_nodes(
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  parent_id TEXT,
  node_type TEXT NOT NULL, -- project, feature, topic, area
  key TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT,
  updated_at TEXT
)
```

Ejemplo de `path`:

```text
project:synto/feature:persistent-memory/topic:engram-research
```

### 8.3 memory_items

```sql
memory_items(
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  node_id TEXT,
  feature_key TEXT,
  topic_key TEXT,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  content_md TEXT NOT NULL,
  structured_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', -- active, superseded, conflicted, deleted, quarantined
  confidence REAL NOT NULL DEFAULT 0.5,
  importance REAL NOT NULL DEFAULT 0.5,
  source_type TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  created_by TEXT,
  created_at TEXT,
  updated_at TEXT,
  valid_from TEXT,
  valid_to TEXT,
  expires_at TEXT,
  normalized_hash TEXT,
  revision_count INTEGER DEFAULT 1,
  duplicate_count INTEGER DEFAULT 1
)
```

### 8.4 memory_links

```sql
memory_links(
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,
  source_ref TEXT,
  created_at TEXT,
  PRIMARY KEY(from_id, to_id, relation)
)
```

Relaciones iniciales:

- `relates_to`
- `depends_on`
- `supersedes`
- `contradicts`
- `fixes`
- `caused_by`
- `affects_file`
- `affects_artifact`
- `belongs_to_feature`
- `derived_from_session`
- `promoted_to_skill`

### 8.5 memory_candidates

Los agentes escriben candidatos; `MemoryManager` consolida.

```sql
memory_candidates(
  id TEXT PRIMARY KEY,
  run_id TEXT,
  proposed_by_agent TEXT,
  project_id TEXT,
  suggested_node_id TEXT,
  suggested_kind TEXT,
  title TEXT,
  content_md TEXT,
  structured_json TEXT,
  policy_status TEXT DEFAULT 'pending',
  reason TEXT,
  created_at TEXT
)
```

---

## 9. Formato canónico de un memory item

Cada memoria importante debería poder renderizarse como Markdown/JSON.

```yaml
id: mem_...
project_id: synto
path: project/synto/feature/persistent-memory/topic/engram-research
kind: bug_resolution | decision | convention | feature_context | artifact_summary | session_summary | risk | preference | skill_candidate
title: "..."
summary: "Resumen de 1-2 líneas"
status: active
confidence: 0.9
importance: 0.8
source:
  type: session | artifact | code_scan | user_message | test_output | web_research
  ref: "..."
structured:
  what: "..."
  why: "..."
  where: ["archivo/ruta", "feature", "agente"]
  learned: "..."
  verification: "..."
  next_time: "..."
links:
  - relation: affects_artifact
    target: artifact:PRD.md
  - relation: belongs_to_feature
    target: feature:persistent-memory
```

---

## 10. Retrieval recomendado

### 10.1 Al iniciar un run

`MemoryManager` debe buscar:

- project profile;
- active feature brief;
- decisiones vigentes;
- bugs/riesgos relevantes;
- conventions por agente;
- session summaries recientes;
- artifacts resumidos;
- open questions.

### 10.2 Por agente

Cada agente recibe un memory pack distinto.

Ejemplos:

- `BackendImplementer`: bugs backend, comandos test, contracts API, DB/ORM/auth.
- `FrontendImplementer`: design decisions, componentes, estado, hooks, contracts frontend.
- `SystemDesigner`: tokens, feedback UI, design-system, referencias.
- `ContractAligner`: endpoints, DTOs, mismatchs históricos.
- `SecurityReviewer`: auth, secrets, threat model, riesgos previos.
- `Planner`: decisiones, blockers, feature state, open questions.

### 10.3 Ranking

Combinar:

- match exacto FTS;
- scope de proyecto;
- feature/topic;
- rol del agente;
- kind compatible con fase;
- importance;
- confidence;
- recency;
- links desde artifacts activos;
- penalización por status `superseded`, `conflicted`, `expired`.

---

## 11. Soluciones posibles

### Opción A — Engram-like simple

SQLite + FTS5 + sessions + observations + topic_key.

Pros:

- rápido;
- local-first;
- simple;
- probado por un repo real;
- suficiente para primer MVP.

Contras:

- menos expresivo para multi-agente enterprise;
- árbol/grafo limitado;
- governance más básica.

Cuándo elegirla:

- si queremos implementar rápido y aprender con uso real.

### Opción B — Obsidian-first

Markdown en vault como fuente primaria + índice auxiliar.

Pros:

- excelente para vos como segundo cerebro;
- muy visible;
- simple de inspeccionar.

Contras:

- menos robusto para concurrencia y auditoría;
- difícil de gobernar automáticamente;
- riesgo de inconsistencias.

Cuándo elegirla:

- si priorizás lectura humana/manual por encima de robustez de agentes.

### Opción C — Vector-first

SQLite-vec/Chroma/LanceDB como memoria principal.

Pros:

- muy buen fuzzy recall;
- rápido de consultar por significado.

Contras:

- estructura pobre;
- difícil representar árbol, status, superseded, conflictos;
- retrieval ruidoso.

Cuándo elegirla:

- nunca como core para este caso; sí como índice complementario.

### Opción D — Temporal graph-first

Graphiti/Zep-style temporal graph.

Pros:

- muy potente;
- temporalidad y contradicciones mejor modeladas;
- ideal para memoria grande y multi-hop.

Contras:

- complejidad alta;
- dependencias extra;
- demasiado para MVP.

Cuándo elegirla:

- futuro, cuando la memoria tenga volumen y la UI necesite navegación temporal/relacional avanzada.

### Opción E — Hybrid Hermes Project Memory

SQLite canónica + árbol primario + links/grafo liviano + FTS5 + Obsidian export + embeddings opcionales.

Pros:

- balance correcto;
- local-first;
- auditable;
- soporta multi-agente;
- soporta UI futura;
- compatible con Obsidian;
- evoluciona a Postgres/pgvector/graph después.

Contras:

- más trabajo que copiar Engram;
- hay que diseñar bien policies y memory extraction.

Elección recomendada:

```text
Opción E: Hybrid Hermes Project Memory
```

---

## 12. Decisión recomendada

Para `synto` conviene implementar:

```text
Hybrid Hermes Project Memory
```

Con estas reglas:

1. DB canónica: SQLite local en MVP.
2. Búsqueda inicial: FTS5 + filtros estructurados.
3. Organización: árbol primario `Project -> Feature -> Topic`.
4. Relaciones: tabla `memory_links` como grafo liviano.
5. Escritura: agentes generan candidates; `MemoryManager` consolida.
6. Formato: memory items estructurados con What/Why/Where/Learned.
7. Obsidian: export/sync humano-readable, no fuente primaria.
8. Embeddings: fase 2 con `sqlite-vec` o provider local/configurable.
9. UI futura: Memory Center con árbol, búsqueda, timeline, candidates, conflicts y graph view.
10. Seguridad: redacción de secretos antes de persistir.

---

## 13. Roadmap sugerido

### Fase 1 — Engram-compatible core

- `projects`
- `sessions`
- `memory_items`
- `memory_candidates`
- `memory_fts`
- `memory_links` simple
- tools internas:
  - `memory.context`
  - `memory.search`
  - `memory.save_candidate`
  - `memory.session_summary`

### Fase 2 — Árbol de proyecto/features

- `memory_nodes`
- `feature_key`
- `topic_key`
- navegación project -> feature -> topic -> item
- memory packs por agente.

### Fase 3 — Obsidian export

- export Markdown por proyecto/feature;
- index pages;
- backlinks/WikiLinks;
- sync al vault.

### Fase 4 — Hybrid semantic

- embeddings locales opcionales;
- hybrid rank FTS + vector + role/scope score.

### Fase 5 — UI Memory Center

- browser de árbol;
- timeline;
- candidates approval;
- conflict resolver;
- graph view;
- “qué memoria recibió este agente”.

### Fase 6 — Temporal graph avanzado

- si hace falta, migrar `memory_links` a graph backend o usar Graphiti-like temporal graph.

---

## 14. Decisión corta

No usaría un árbol puro.

Usaría:

```text
árbol para organizar + grafo para relacionar + FTS/vector para encontrar
```

Y guardaría solo memoria accionable:

```text
decisiones, problemas resueltos, contexto de feature, convenciones, contracts, diseño, riesgos, resúmenes de sesión y artifact summaries.
```

Ese diseño se adapta mejor a Hermes que copiar Engram literal, pero toma de Engram lo más valioso: SQLite local, FTS5, sessions, observations, topic_key, timeline, session summary y disciplina What/Why/Where/Learned.
