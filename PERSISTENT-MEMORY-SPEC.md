# Persistent Memory Spec

> Estado: especificación para implementación
> Fecha: 2026-04-28
> Objetivo: definir cómo los agentes recuerdan información útil entre sesiones sin cargar contexto innecesario ni pedir todo de nuevo.

---

## 1. Decisión

Sí: el sistema debe tener una capa de memoria persistente cross-session.

El `SharedState / Blackboard` ya definido sirve para un run activo: coordinación, slots, artifacts, gates, eventos y checkpoints.

Pero eso no alcanza para el objetivo de que los agentes “recuerden” cosas importantes de sesiones anteriores. Para eso agregamos una capa separada:

```text
PersistentMemory / MemoryStore
```

Esta capa funciona como un cerebro durable del sistema: guarda conocimiento estable, decisiones, preferencias, contexto de proyectos, resúmenes de runs y aprendizajes reutilizables.

---

## 2. Diferencia entre SharedState y PersistentMemory

| Capa | Duración | Uso | Ejemplo |
|---|---|---|---|
| `SharedState` | Durante un run/proyecto activo | Coordinar agentes en paralelo | slot del Planner, gate PRD, evento de test fallido |
| `Checkpoint` | Durante/reanudación de un run | Pausar, retomar, retry | estado exacto antes de un gate humano |
| `Artifacts` | Durable por proyecto | Documentos fuente/versionados | PRD, spec, design-system.json, QA report |
| `PersistentMemory` | Cross-session / cross-run | Recordar lo importante sin pedir contexto | “este proyecto usa LangGraph + MCP”, “el usuario prefiere no usar servicios pagos”, “este repo usa pnpm/turbo” |

Regla central:

> SharedState coordina el presente. PersistentMemory trae contexto del pasado y consolida aprendizajes para el futuro.

---

## 3. Objetivos

1. Rehidratar contexto automáticamente al iniciar o retomar una tarea.
2. Evitar que el usuario tenga que repetir decisiones ya tomadas.
3. Dar a cada agente solo la memoria relevante para su rol.
4. Mantener trazabilidad: toda memoria debe tener fuente/provenance.
5. Evitar memoria basura, duplicada, contradictoria o sensible.
6. Soportar búsqueda híbrida: keyword + semántica + filtros por proyecto/agente/tags.
7. Exponer la memoria a la futura UI web.
8. Permitir olvidar, corregir, versionar y auditar memorias.

---

## 4. Principios no negociables

1. Ningún agente recibe toda la base de memoria.
2. Toda memoria inyectada debe venir con fuente o explicación de procedencia.
3. Los agentes no escriben memoria canónica directamente; generan candidatos.
4. Un `MemoryManager` consolida, deduplica, clasifica y persiste.
5. Los secretos nunca se guardan: tokens, API keys, cookies, passwords, claves privadas se redactan.
6. La memoria debe poder corregirse o eliminarse.
7. La memoria no reemplaza artifacts. Si algo es contrato del proyecto, vive como artifact y puede tener una memoria-resumen apuntando a ese artifact.
8. La memoria debe tener scope claro: global, proyecto, dominio, agente o usuario.
9. La memoria debe tener confianza/importancia para ranking.
10. Si una memoria contradice otra, se marca conflicto en vez de pisarla silenciosamente.

---

## 5. Tipos de memoria

### 5.1 Semantic memory

Hechos estables y reutilizables.

Ejemplos:

- “hermes-orchestrator usa LangGraph como runtime.”
- “A2A queda futuro/opcional, no dependencia del MVP.”
- “El usuario prefiere español rioplatense.”
- “El sistema odontológico es monorepo pnpm/turbo.”

Uso principal: rehidratar contexto factual.

### 5.2 Episodic memory

Resumen de sesiones/runs.

Ejemplos:

- “En el run X se creó el PRD de auth JWT y se aprobó con estas restricciones.”
- “La implementación falló por incompatibilidad de versión de Prisma.”

Uso principal: retomar historia sin cargar logs completos.

### 5.3 Project memory

Conocimiento estable asociado a un proyecto concreto.

Ejemplos:

- stack técnico;
- decisiones arquitectónicas;
- estructura del repo;
- convenciones de test;
- endpoints definidos;
- riesgos conocidos;
- design system vigente.

### 5.4 Agent memory

Memoria filtrada por rol.

Ejemplos:

- `SystemDesigner`: tokens, componentes, decisiones UX.
- `BackendImplementer`: convenciones de API, ORM, auth, servicios.
- `FrontendImplementer`: estructura de componentes, librerías UI, estado global.
- `ContractAligner`: contratos API/schema y desalineaciones previas.
- `SecurityReviewer`: riesgos históricos y decisiones de seguridad.

Importante: no es “memoria privada” opaca. Es una vista filtrada de memoria con trazabilidad.

### 5.5 Procedural memory

Procedimientos reutilizables.

Ejemplos:

- cómo levantar un proyecto local;
- cómo correr tests;
- cómo deployar;
- cómo validar un workflow.

Regla: si es un procedimiento estable, eventualmente debería convertirse en skill o runbook, no quedar solo como texto suelto.

### 5.6 Artifact memory

Resumen/indexación de artifacts.

Ejemplos:

- resumen de `PRD.md`;
- decisiones principales de `design-system.json`;
- resumen de `qa-report.md`;
- snapshot de estructura del repo.

La memoria apunta al artifact real, no lo reemplaza.

### 5.7 Cache memory

Resultados reutilizables pero de baja confianza o con expiración.

Ejemplos:

- búsqueda web reciente;
- versión detectada de un paquete;
- resultado de introspección de repo.

Debe tener TTL.

---

## 6. Scopes

```text
global
  Preferencias del usuario, reglas generales, convenciones comunes.

project:{project_id}
  Decisiones y contexto de un proyecto específico.

domain:{domain_id}
  Conocimiento reusable por dominio: code, research, business, UX, devops.

agent:{agent_id}
  Vista especializada por agente.

run:{run_id}
  Resumen de un run específico. No se carga salvo que sea relevante.
```

Un memory item puede tener múltiples scopes, pero debe tener un scope primario.

---

## 7. Arquitectura conceptual

```text
                    ┌────────────────────────────┐
                    │        User / UI / CLI      │
                    └──────────────┬─────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │    HermesOrchestrator      │
                    └──────────────┬─────────────┘
                                   │ asks context
                                   ▼
┌────────────────────────────────────────────────────────────────┐
│                     Memory Layer                               │
│                                                                │
│  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐ │
│  │ MemoryRetriever │──▶│ MemoryPackBuilder│──▶│ Memory Pack  │ │
│  └─────────────────┘   └─────────────────┘   └──────────────┘ │
│           ▲                         │                          │
│           │                         ▼                          │
│  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────┐ │
│  │  MemoryStore    │◀──│ MemoryManager   │◀──│ Candidates   │ │
│  └─────────────────┘   └─────────────────┘   └──────────────┘ │
│           ▲                         ▲                          │
│           │                         │                          │
│  ┌─────────────────┐   ┌─────────────────┐                    │
│  │ Vector/FTS idx  │   │ Conflict/Redact │                    │
│  └─────────────────┘   └─────────────────┘                    │
└────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │ SharedState / Blackboard   │
                    │ memory_context per agent   │
                    └────────────────────────────┘
```

---

## 7.1 Capa de acceso aprobada: Memory MCP + MemoryContextAgent

Decisión agregada el 2026-04-28:

```text
Agentes especializados
  ↓
MemoryContextAgent / MemoryRetriever liviano
  ↓
Memory MCP Server / Memory API interna
  ↓
MemoryStore SQLite + FTS5
```

Los agentes no deben consultar SQLite directamente ni cargar memoria completa.

Motivo:

- reduce consumo de contexto;
- evita compactaciones tempranas;
- centraliza permisos y auditoría;
- evita duplicación de lógica de búsqueda;
- permite memory packs por rol/fase/tarea;
- mantiene las operaciones de DB como tools determinísticas.

Separación de responsabilidades:

| Componente | Responsabilidad |
|---|---|
| `MemoryStore` | Persistencia durable, schema, FTS5, links, candidatos, audit log |
| `Memory MCP Server` | Puerta oficial de acceso: tools chicas, validadas y auditadas |
| `MemoryContextAgent` | Busca, filtra y resume contexto en memory packs chicos por agente |
| `MemoryManager` | Consolida aprendizajes, redacta secretos, deduplica y persiste memoria canónica |

Regla:

> El MemoryContextAgent puede leer más mediante tools, pero siempre entrega poco. MemoryManager puede consolidar más información, pero no inyecta memoria masiva en los agentes.

Ver detalle operativo en `MEMORY-MCP-ARCHITECTURE.md`.

---

## 8. Componentes

### 8.1 MemoryStore

Base durable local.

MVP recomendado:

```text
SQLite + FTS5 + embeddings locales opcionales
```

Ruta:

```text
workspace/.hermes-memory/memory.sqlite
workspace/.hermes-memory/audit.jsonl
workspace/.hermes-memory/exports/obsidian/
```

Producción futura:

```text
Postgres + pgvector
```

Motivo:

- SQLite alcanza para MVP local/offline.
- FTS5 permite búsqueda textual rápida.
- Embeddings agregan búsqueda semántica.
- Postgres/pgvector queda listo para multiusuario/web/producción.

### 8.2 MemoryRetriever

Busca memoria relevante para una tarea.

Inputs:

- `task_summary`
- `project_id`
- `domain_id`
- `agent_id`
- `phase`
- `tags`
- `current_artifacts`
- `token_budget`

Outputs:

- lista rankeada de memory items;
- citas/fuentes;
- score de relevancia;
- razón de inclusión.

### 8.3 MemoryPackBuilder

Convierte resultados en un bloque compacto por agente.

Ejemplo:

```yaml
memory_pack:
  agent_id: BackendImplementer
  project_id: sistema-odontologico
  max_tokens: 1800
  items:
    - id: mem_0182
      kind: project_decision
      content: "El backend usa NestJS y Prisma."
      source: "repo-scan:2026-04-20"
      confidence: 0.92
    - id: mem_0191
      kind: convention
      content: "No modificar endpoints sin pasar por ContractAligner."
      source: "PERSISTENT-MEMORY-SPEC.md"
      confidence: 0.95
```

### 8.4 MemoryManager

Agente/servicio cross-cutting.

Responsabilidades:

- extraer candidatos desde artifacts, eventos y conversaciones;
- redaccionar secretos;
- deduplicar;
- detectar contradicciones;
- asignar scope, tags, confianza e importancia;
- persistir memoria canónica;
- generar resúmenes de run;
- exponer búsqueda a agentes;
- auditar lecturas/escrituras.

### 8.5 MemoryExtractor

Corre al final de fases importantes y al final del run.

Extrae candidatos como:

- decisiones aprobadas;
- restricciones nuevas;
- errores resueltos;
- convenciones descubiertas;
- cambios de arquitectura;
- preferencias del usuario;
- comandos/verificaciones estables;
- referencias a artifacts.

### 8.6 MemoryConsolidator

Transforma candidatos en memoria durable.

Reglas:

- merge si duplica;
- update si reemplaza versión anterior;
- conflict si contradice;
- expire si es temporal;
- reject si es ruido o secreto.

### 8.7 MemoryPolicyEngine

Decide qué puede guardarse automáticamente y qué requiere revisión.

Auto-commit permitido:

- decisiones de proyecto aprobadas;
- resúmenes de artifacts versionados;
- convenciones técnicas observadas y verificadas;
- errores solucionados con causa clara;
- preferencias explícitas del usuario.

Requiere revisión o quarantine:

- información sensible;
- datos personales no necesarios;
- credenciales/secretos;
- inferencias débiles;
- contradicciones;
- decisiones de alto impacto no aprobadas;
- información externa no verificada.

---

## 9. Modelo de datos MVP

```sql
CREATE TABLE memory_items (
  id TEXT PRIMARY KEY,
  scope_primary TEXT NOT NULL,
  scopes_json TEXT NOT NULL,
  project_id TEXT,
  run_id TEXT,
  agent_id TEXT,
  domain_id TEXT,
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  tags_json TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  importance REAL NOT NULL DEFAULT 0.5,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  expires_at TEXT
);

CREATE VIRTUAL TABLE memory_fts USING fts5(
  id UNINDEXED,
  content,
  summary,
  tags
);

CREATE TABLE memory_links (
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE memory_candidates (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  proposed_by TEXT NOT NULL,
  content TEXT NOT NULL,
  suggested_scope TEXT,
  suggested_kind TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  reason TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE memory_audit_log (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  memory_id TEXT,
  run_id TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

Embeddings pueden agregarse luego con:

- `sqlite-vec` / `sqlite-vss` en MVP local;
- `pgvector` en producción;
- LanceDB/Chroma si se prefiere DB vectorial separada.

---

## 10. Flujo de rehidratación automática

Al iniciar una tarea:

```text
1. HermesOrchestrator recibe pedido del usuario.
2. Crea task_summary inicial.
3. Detecta o crea project_id.
4. MemoryRetriever busca memoria relevante:
   - global;
   - proyecto;
   - dominio;
   - agente;
   - artifacts indexados.
5. MemoryPackBuilder arma memory_pack global y por agente.
6. SharedState recibe:
   - memory_context.global;
   - memory_context.by_agent;
   - memory_context.sources;
7. Cada agente recibe solo su memory_pack filtrado.
```

Ejemplo:

```text
Usuario: "sigamos con la UI del orchestrator"

HermesOrchestrator rehidrata:
- arquitectura vigente LangGraph + MCP;
- docs existentes;
- decisión de UI posterior al motor;
- preferencia español rioplatense;
- que Agency Swarm quedó legacy;
- estado de PERSISTENT-MEMORY-SPEC.
```

---

## 11. Flujo de escritura automática

Durante el run:

```text
Agent output → SharedState slot → Event log → MemoryExtractor → Candidates
```

Al cerrar una fase o run:

```text
Candidates → Redaction → Dedup → Conflict Check → Policy → Commit/Quarantine
```

Los agentes NO escriben directamente memoria canónica. En su lugar hacen:

```text
memory.add_candidate(...)
```

MemoryManager decide si queda persistida.

---

## 12. Retrieval por agente

### HermesOrchestrator

Recibe:

- preferencias del usuario;
- estado del proyecto;
- decisiones de arquitectura;
- runs recientes relacionados;
- pendientes relevantes.

No recibe detalles técnicos profundos salvo que el pedido lo requiera.

### CodeOrchestrator

Recibe:

- decisiones técnicas vigentes;
- constraints del proyecto;
- estado de artifacts;
- workflows previos;
- riesgos abiertos.

### BusinessAnalyst / ProductManager

Reciben:

- preferencias del usuario;
- decisiones de producto previas;
- alcance/out-of-scope;
- feedback anterior.

### Planner / Architect

Reciben:

- arquitectura vigente;
- constraints técnicos;
- convenciones del repo;
- decisiones rechazadas previamente.

### BackendImplementer

Recibe:

- stack backend;
- scripts/comandos relevantes;
- patrones de API;
- ORM/DB/auth;
- errores conocidos.

### FrontendImplementer

Recibe:

- stack frontend;
- estructura de componentes;
- design-system vigente;
- patrones de estado;
- restricciones UX/accessibility.

### SystemDesigner

Recibe:

- design decisions;
- tokens/componentes;
- referencias visuales;
- feedback de UI anterior.

### ContractAligner

Recibe:

- contratos API;
- schemas;
- desalineaciones previas;
- acuerdos backend/frontend.

### Reviewer / SecurityReviewer / QAGatekeeper

Reciben:

- bugs históricos;
- riesgos conocidos;
- reglas de calidad;
- criterios de aceptación;
- decisiones de seguridad.

---

## 13. API conceptual

```python
class PersistentMemory:
    def search(self, query: str, scope: list[str], limit: int = 10) -> list[MemoryItem]: ...
    def probe(self, entity: str, project_id: str | None = None) -> list[MemoryItem]: ...
    def build_pack(self, task: TaskContext, agent_id: str, token_budget: int) -> MemoryPack: ...
    def add_candidate(self, candidate: MemoryCandidate) -> str: ...
    def commit_candidate(self, candidate_id: str, actor: str) -> str: ...
    def forget(self, memory_id: str, reason: str, actor: str) -> None: ...
    def mark_conflict(self, a: str, b: str, reason: str) -> None: ...
```

MCP tools futuras:

```text
memory.search
memory.get_item
memory.get_tree
memory.probe
memory.build_pack
memory.add_candidate
memory.list_candidates
memory.commit_candidate
memory.reject_candidate
memory.link_items
memory.forget
memory.list_conflicts
memory.export_obsidian
```

Regla de tool layer:

> Ningún tool devuelve memoria ilimitada. Toda respuesta debe tener `limit`, `scope`, `source` y formato compacto.

---

## 14. Ranking y budget de contexto

Ranking sugerido:

```text
score = semantic_similarity
      + keyword_match
      + project_scope_boost
      + agent_role_boost
      + importance
      + confidence
      + recency_decay
      - staleness_penalty
      - conflict_penalty
```

Budget inicial:

| Agente | Budget memoria sugerido |
|---|---:|
| HermesOrchestrator | 1200-2000 tokens |
| CodeOrchestrator | 2000-3500 tokens |
| Planner / Architect | 1500-3000 tokens |
| Implementers | 1000-2500 tokens |
| Reviewers | 1000-2500 tokens |
| MemoryContextAgent | puede consultar más vía tools, pero entrega packs chicos |
| MemoryManager | puede leer más, pero resume antes de entregar |

---

## 15. Obsidian y fact_store

El vault de Obsidian y `fact_store` pueden integrarse, pero no deberían ser la única base interna del orchestrator.

Uso recomendado:

| Sistema | Rol |
|---|---|
| `PersistentMemory` | DB primaria operativa del orchestrator |
| `fact_store` de Hermes | memoria global actual del asistente, útil para seed/sync |
| Obsidian vault | espejo humano-readable y segundo cerebro navegable |
| `session_search` | recall histórico de chats pasados, útil para bootstrap |
| Artifacts del proyecto | fuente de verdad para contratos del proyecto |

Regla:

> Obsidian es excelente como espejo y lectura humana. La DB operativa debe ser estructurada, auditable y consultable por agentes.

---

## 16. UI futura: Memory Center

La interfaz web debería incluir una sección:

```text
Memory Center
```

Funciones:

- buscar memorias por proyecto/agente/tag;
- ver memoria inyectada en cada run;
- ver fuentes/provenance;
- aprobar/rechazar candidatos;
- resolver contradicciones;
- editar o olvidar memorias;
- exportar a Obsidian;
- ver grafo de entidades/proyectos/decisiones;
- ver qué agente leyó qué memoria.

---

## 17. Seguridad

### 17.1 Redacción de secretos

Antes de guardar:

- API keys;
- bearer tokens;
- cookies;
- private keys;
- passwords;
- `.env` completo;
- credenciales de servicios.

Se reemplazan por:

```text
[REDACTED]
```

### 17.2 Memory poisoning

Riesgo: un documento externo o web page intenta insertar instrucciones persistentes maliciosas.

Mitigación:

- marcar memoria por fuente;
- no auto-commit de instrucciones provenientes de fuentes no confiables;
- separar facts de instrucciones;
- detectar frases tipo “ignore previous instructions”;
- no permitir que contenido externo modifique políticas del sistema.

### 17.3 Derecho a olvidar

Debe existir operación:

```text
memory.forget(memory_id, reason)
```

No basta con ocultar: debe marcar como deleted/tombstoned y dejar audit trail.

---

## 18. MVP propuesto

### Fase A — MemoryStore local

- Crear `workspace/.hermes-memory/memory.sqlite`.
- Crear tablas base.
- Crear FTS5.
- Crear audit log JSONL.

### Fase B — Rehidratación simple

- Buscar por keyword/tags/project_id.
- Armar memory pack por agente.
- Insertarlo en SharedState.

### Fase C — Extracción post-run

- Extraer candidatos desde:
  - user messages;
  - artifacts canónicos;
  - decisions;
  - errors/resolutions.
- Auto-commit de candidatos seguros.
- Quarantine de sensibles/conflictivos.

### Fase D — UI-ready

- Endpoint/API para listar, buscar, aprobar y olvidar.
- Eventos de memoria en timeline.
- Export a Obsidian.

### Fase E — Búsqueda semántica

- Agregar embeddings locales o provider configurable.
- Híbrido keyword + vector.

---

## 19. Cambios al contrato de agentes

Agregar agente/servicio cross-cutting:

```text
MemoryManager
```

No es un worker de code. Es infraestructura cognitiva del sistema.

Responsabilidades:

- rehidratar contexto antes de cada run;
- construir memory packs por agente;
- consolidar aprendizajes después de cada run;
- mantener memoria limpia, trazable y segura;
- exportar resúmenes a Obsidian;
- detectar contradicciones.

Restricciones:

- no habla directamente con el usuario;
- no decide producto/arquitectura por sí mismo;
- no guarda secretos;
- no inyecta memoria sin fuente;
- no carga toda la memoria a un agente.

---

## 20. Actualización por investigación Engram/Obsidian/vector/graph

Se investigó `Gentleman-Programming/engram` y alternativas de memoria persistente para agentes: Obsidian-first, Basic Memory, vector-memory MCP, mcp-memory-service, Letta/MemGPT-style hierarchical memory, Graphiti/Zep y GraphRAG.

Documento completo:

```text
MEMORY-ARCHITECTURE-RESEARCH.md
```

Decisión refinada:

```text
Hybrid Hermes Project Memory
```

No se usará un árbol puro ni una DB plana.

La memoria tendrá:

- árbol primario para navegación y scope:
  - Project
  - Feature
  - Topic
  - MemoryItem
- grafo liviano de relaciones vía `memory_links`:
  - `depends_on`
  - `supersedes`
  - `contradicts`
  - `fixes`
  - `affects_artifact`
  - `belongs_to_feature`
  - `promoted_to_skill`
- SQLite + FTS5 como fuente canónica local del MVP;
- embeddings opcionales en fase posterior;
- Obsidian como export/sync humano-readable, no como DB operativa primaria;
- `topic_key` estable inspirado en Engram para temas que evolucionan;
- estructura What/Why/Where/Learned para memories accionables.

Principio de guardado:

> Guardar lo que un futuro agente no podría inferir fácilmente leyendo el código o los artifacts actuales.

Tipos principales a guardar:

- decisiones;
- problemas resueltos con causa raíz;
- contexto de feature;
- convenciones/patrones del proyecto;
- contratos frontend/backend/API;
- decisiones de diseño/UX;
- riesgos/gotchas/restricciones;
- resúmenes de sesión/run;
- preferencias explícitas del usuario;
- resúmenes de artifacts.

No guardar:

- secretos;
- logs enormes sin resumir;
- hechos obvios del código;
- TODOs efímeros;
- contenido externo no verificado como instrucción persistente;
- duplicados;
- hechos temporales sin TTL.

---

## 21. Decisión final

La arquitectura queda así:

```text
LangGraph Runtime
  ├── SharedState / Blackboard        # estado del run
  ├── Checkpointer                    # pausa/retoma/retry
  ├── Artifact Store                  # documentos/versiones
  ├── Skill Registry                  # skills dinámicas por agente
  └── PersistentMemory / MemoryStore  # memoria cross-session
```

Esto cumple el objetivo: los agentes pueden arrancar cada sesión con contexto relevante, sin que el usuario tenga que repetir todo, pero evitando el problema de meter toda la historia en el prompt.
