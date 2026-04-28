# Memory MCP Architecture

> Estado: decisión aprobada para implementación
> Fecha: 2026-04-28
> Contexto: capa de acceso a memoria persistente para reducir uso de contexto, evitar compactaciones dañinas y permitir que muchos agentes trabajen con memoria sin tocar la base directamente.

---

## 1. Decisión

La memoria persistente del orchestrator se va a exponer mediante una capa intermedia, no por acceso directo de cada agente a la base de datos.

Arquitectura aprobada:

```text
Agentes especializados
  ↓ piden contexto puntual
MemoryContextAgent / MemoryRetriever liviano
  ↓ usa tools determinísticas
Memory MCP Server / Memory API interna
  ↓ consulta y escribe con reglas
MemoryStore SQLite + FTS5
```

Regla central:

> Los agentes no cargan toda la memoria ni consultan SQLite directamente. Reciben memory packs chicos, filtrados por proyecto, tarea, fase, rol y budget de contexto.

---

## 2. Por qué hace falta esta capa

El problema principal no es solo recordar cosas. El problema es recordar sin destruir el contexto de los agentes.

Si cada agente busca y carga memoria por su cuenta:

- consume muchos tokens;
- trae ruido;
- repite búsquedas;
- puede llenar la ventana de contexto;
- se compacta antes;
- al compactarse pierde detalles importantes;
- puede guardar basura o duplicados;
- puede confundir decisiones viejas con decisiones vigentes.

Por eso la memoria necesita una puerta oficial.

La solución:

- búsqueda determinística en una DB local;
- selección/síntesis liviana;
- memory packs por agente;
- límites estrictos de tokens;
- provenance/fuentes;
- redacción de secretos;
- consolidación centralizada.

---

## 3. Componentes

### 3.1 MemoryStore

La base de datos real.

MVP:

```text
workspace/.hermes-memory/memory.sqlite
workspace/.hermes-memory/audit.jsonl
```

Responsabilidades:

- guardar proyectos, features, topics y memory items;
- mantener índices FTS5 para búsqueda textual;
- guardar relaciones `memory_links`;
- guardar candidatos pendientes;
- soportar soft delete/tombstone;
- mantener timestamps, provenance, confidence e importance.

No usa LLM.

Es código normal, testeable y determinístico.

---

### 3.2 Memory MCP Server / Memory API interna

La puerta oficial entre agentes y base de datos.

Responsabilidades:

- exponer tools chicas y seguras;
- validar inputs;
- aplicar permisos/scopes;
- auditar lecturas/escrituras;
- evitar que un agente pida “toda la memoria”;
- devolver resultados estructurados y compactos.

Tools previstas:

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
memory.list_conflicts
memory.forget
memory.export_obsidian
```

Regla:

> Las queries crudas a SQLite viven adentro del servidor/tool layer, no en los prompts de los agentes.

---

### 3.3 MemoryContextAgent / MemoryRetriever

Agente liviano para traer contexto justo.

No es un “super agente”. Es más parecido a un bibliotecario rápido.

Responsabilidades:

- entender la tarea actual;
- detectar proyecto/feature/fase;
- pedir búsquedas al Memory MCP;
- rankear resultados;
- armar memory packs chicos por agente;
- explicar por qué incluyó cada memoria;
- respetar budget de contexto;
- escribir `memory_context` en SharedState.

No debería:

- tomar decisiones de producto;
- modificar código;
- guardar memoria canónica;
- hablar directamente con el usuario;
- cargar memoria completa;
- reemplazar al MemoryManager.

Modelo recomendado:

```text
economy o balanced chico
```

Motivo: su tarea es selección/síntesis, no arquitectura profunda.

---

### 3.4 MemoryManager

Agente/servicio de consolidación.

Responsabilidades:

- mirar eventos, artifacts y outputs al final de una fase/run;
- detectar candidatos de memoria;
- redactar secretos;
- deduplicar;
- detectar contradicciones;
- decidir commit/quarantine/reject;
- mantener memoria limpia;
- exportar a Obsidian.

Diferencia con MemoryContextAgent:

| Componente | Momento | Qué hace |
|---|---|---|
| MemoryContextAgent | Antes/durante el run | Busca y prepara contexto chico para cada agente |
| MemoryManager | Durante/después del run | Decide qué aprendizajes se guardan para el futuro |
| Memory MCP Server | Siempre | Ejecuta operaciones determinísticas contra MemoryStore |
| MemoryStore | Siempre | Guarda datos persistentes |

---

## 4. Flujo al iniciar una tarea

Ejemplo: “Agreguemos recordatorios por WhatsApp a turnos”.

```text
1. HermesOrchestrator recibe la intención.
2. Detecta proyecto probable: sistema odontológico.
3. Crea TaskContext inicial.
4. MemoryContextAgent pide búsquedas al Memory MCP.
5. Memory MCP consulta SQLite/FTS5.
6. MemoryContextAgent arma memory packs por rol.
7. SharedState recibe:
   - memory_context.global
   - memory_context.by_agent.BackendImplementer
   - memory_context.by_agent.FrontendImplementer
   - memory_context.by_agent.SecurityReviewer
   - memory_context.sources
8. Cada agente recibe solo su paquete.
```

Ejemplo de paquete para BackendImplementer:

```yaml
agent_id: BackendImplementer
project_id: sistema-odontologico
token_budget: 1800
items:
  - kind: architecture
    text: "El backend usa NestJS y DTOs por feature."
    source: "repo-scan:2026-04-20"
  - kind: decision
    text: "Los turnos no se borran físicamente; se cancelan para conservar historial."
    source: "memory:mem_0123"
  - kind: security
    text: "No persistir tokens ni credenciales en memoria; usar [REDACTED] en summaries."
    source: "PERSISTENT-MEMORY-SPEC.md"
```

---

## 5. Flujo al terminar una tarea

```text
1. Los agentes dejan outputs/artifacts/eventos en SharedState.
2. MemoryManager inspecciona lo producido.
3. Extrae candidatos de memoria.
4. Redacta secretos.
5. Deduplica contra memoria existente.
6. Clasifica por tipo y scope.
7. Decide:
   - commit automático;
   - quarantine;
   - rechazo;
   - requiere aprobación humana.
8. Memory MCP persiste cambios en MemoryStore.
9. Opcional: export a Obsidian.
```

Ejemplo de candidato útil:

```yaml
kind: problem_solution
project_id: sistema-odontologico
feature: pacientes
what: "El frontend esperaba dateOfBirth pero la API devuelve birthDate."
why: "Rompía la carga de pacientes."
solution: "Alinear contrato usando birthDate."
learned: "Antes de tocar pantallas de pacientes, revisar el contrato API real."
source: "contract-alignment-report:run_2026_04_28"
```

---

## 6. Estrategia anti-compactación

Objetivo: que los agentes no lleguen al límite de contexto por cargar historia innecesaria.

Reglas:

1. Ningún agente recibe la memoria completa.
2. Cada agente recibe un memory pack con budget explícito.
3. El pack debe priorizar decisiones vigentes sobre historia vieja.
4. Cada item debe tener fuente/provenance.
5. Los items largos se resumen antes de entrar al prompt.
6. Las búsquedas profundas quedan fuera del prompt, en tools.
7. Si un agente necesita más memoria, pide una búsqueda puntual.
8. Los outputs grandes se guardan como artifacts, no como texto infinito en conversación.
9. Los summaries post-run son memoria nueva, no reemplazo de artifacts canónicos.
10. La memoria puede traer links a artifacts, no copiar artifacts enteros.

Budgets iniciales sugeridos:

| Rol | Budget memoria |
|---|---:|
| HermesOrchestrator | 800-1500 tokens |
| CodeOrchestrator | 1500-2500 tokens |
| Planner / Architect | 1200-2200 tokens |
| BackendImplementer | 1000-1800 tokens |
| FrontendImplementer | 1000-1800 tokens |
| SystemDesigner | 800-1600 tokens |
| Tester / Reviewer | 800-1600 tokens |
| SecurityReviewer | 800-1600 tokens |
| MemoryContextAgent | puede leer más vía tools, pero entrega poco |
| MemoryManager | puede leer más para consolidar, pero no lo inyecta completo |

---

## 7. Permisos

Regla de seguridad:

> Leer contexto es barato; escribir memoria durable es delicado.

Permisos recomendados:

| Actor | Puede buscar | Puede armar pack | Puede proponer candidato | Puede commitear memoria |
|---|---:|---:|---:|---:|
| HermesOrchestrator | sí | no directo | sí | no |
| CodeOrchestrator | sí | no directo | sí | no |
| Specialist agents | limitado | no | sí | no |
| MemoryContextAgent | sí | sí | no | no |
| MemoryManager | sí | sí | sí | sí, con policy |
| Memory MCP Server | ejecuta tools | ejecuta tools | ejecuta tools | ejecuta tools validadas |

---

## 8. Modelo de datos mínimo

MVP de tablas:

```text
projects
features
topics
memory_items
memory_links
memory_candidates
sessions
memory_access_log
```

FTS5:

```text
memory_items_fts
```

Campos importantes de `memory_items`:

```text
id
project_id
feature_id
topic_id
kind
status
summary
content
source_type
source_ref
confidence
importance
tags
created_at
updated_at
deleted_at
```

Tipos iniciales:

```text
decision
problem_solution
architecture
convention
feature_state
api_contract
bug_fix
command
dependency
user_preference
domain_context
artifact_summary
technical_debt
open_question
```

---

## 9. Qué se implementa primero

Arrancar por memoria tiene sentido, pero no por “toda la memoria completa”.

Orden recomendado:

```text
0. Repo/test scaffold mínimo
1. MemoryStore SQLite + FTS5
2. Memory models + repository API
3. MemoryPackBuilder con budgets
4. Memory MCP/tool layer
5. MemoryContextAgent liviano
6. MemoryManager básico de candidatos
7. Integración con SharedState mock
8. Recién después: AgentRegistry, SkillRegistry, LangGraph runtime
```

Motivo:

- ataca primero el problema de contexto/compactación;
- se puede testear sin tener todos los agentes listos;
- deja una base reusable para todo el orchestrator;
- evita construir agentes “amnesicos” y después intentar parchearles memoria.

---

## 10. Fuera del MVP

No entra al primer MVP:

- vector DB compleja;
- GraphRAG completo;
- Neo4j;
- UI visual completa;
- multiusuario;
- sincronización bidireccional editable con Obsidian;
- auto-commit agresivo de memoria sin policy;
- agentes escribiendo directo a SQLite;
- memory packs gigantes.

---

## 11. Criterios de aceptación

La capa está lista cuando:

- se puede crear un proyecto en MemoryStore;
- se puede guardar una memoria con scope proyecto/feature/topic;
- se puede buscar por FTS5;
- se puede construir un memory pack para un agente con token budget;
- se puede registrar un candidato;
- MemoryManager puede aceptar/rechazar candidato;
- cada lectura/escritura queda auditada;
- los secretos se redactan antes de persistir;
- existe test automatizado para schema, search, pack building y redaction;
- existe un flujo mock end-to-end:
  - tarea entra;
  - se busca memoria;
  - se arma pack;
  - agente mock trabaja;
  - candidato se consolida.

---

## 12. Relación con documentos existentes

- `PERSISTENT-MEMORY-SPEC.md` define la memoria persistente general.
- `MEMORY-ARCHITECTURE-RESEARCH.md` justifica la decisión híbrida.
- Este documento define la capa concreta de acceso: Memory MCP + MemoryContextAgent.
- `IMPLEMENTATION-PLAN.md` define el orden para construirlo.
- `AGENT-REGISTRY.yaml` define permisos, roles y capacidades.
