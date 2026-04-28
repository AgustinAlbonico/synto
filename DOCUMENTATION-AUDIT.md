# Documentation Audit

> Fecha: 2026-04-28
> Estado: revisión previa a implementación
> Objetivo: verificar si la documentación está suficientemente cerrada para empezar a implementar sin improvisar.

---

## Resultado ejecutivo

La documentación base está bien encaminada y cubre las decisiones principales.

Faltaba documentar explícitamente una pieza importante:

```text
Memory MCP Server + MemoryContextAgent
```

Ese hueco ya queda cubierto por:

```text
MEMORY-MCP-ARCHITECTURE.md
```

La recomendación después de esta auditoría es:

```text
Arrancar implementación por un MVP memory-first:
1. scaffolding + tests;
2. MemoryStore SQLite/FTS5;
3. Memory MCP/tool layer;
4. MemoryContextAgent;
5. MemoryManager básico;
6. integración con SharedState mock;
7. recién después AgentRegistry/SkillRegistry/LangGraph runtime.
```

---

## Estado por documento

| Documento | Estado | Observación |
|---|---|---|
| `README.md` | OK con actualización pendiente aplicada | Índice principal y estado del proyecto. Debe referenciar Memory MCP, audit y plan. |
| `LANGGRAPH-ARCHITECTURE.md` | OK con actualización pendiente aplicada | Arquitectura principal. Debe explicitar que memoria se accede vía Memory MCP/MemoryContextAgent. |
| `AGENT-REGISTRY.yaml` | OK con actualización pendiente aplicada | Contrato vivo de agentes. Debe incluir MemoryContextAgent y separar rehidratación de consolidación. |
| `SKILL-LOADING-SYSTEM.md` | OK | Cubre Skill Registry dinámico, lazy loading, quarantine y validación. No bloquea implementación. |
| `SHARED-STATE-SPEC.md` | OK | Cubre blackboard intra-run y aclara que no es memoria persistente. |
| `PERSISTENT-MEMORY-SPEC.md` | OK con actualización pendiente aplicada | Cubre MemoryStore/MemoryManager/memory packs. Debe sumar Memory MCP como capa de acceso aprobada. |
| `MEMORY-ARCHITECTURE-RESEARCH.md` | OK | Investigación comparativa Engram/Obsidian/vector/graph. Justifica diseño híbrido. |
| `MEMORY-MCP-ARCHITECTURE.md` | NUEVO / OK | Documenta metodología aprobada: Memory MCP + MemoryContextAgent + MemoryManager + anti-compactación. |
| `WEB-INTERFACE-VISION.md` | OK | Cubre Memory Center y endpoints futuros. No bloquea MVP. |
| `GUIA-MAESTRA.md` | OK histórico | Mantiene decisiones y roadmap general. Debe referenciar nuevos docs. |
| `IMPLEMENTATION-PLAN.md` | NUEVO / OK | Plan de implementación recomendado. |
| `DEFINICION-AGENTES.md` | Legacy/parcial | Documento original. La fuente actual de verdad es `AGENT-REGISTRY.yaml`. |
| `ARCHITECTURE.md` | Legacy/parcial | Documento previo. La fuente actual de verdad es `LANGGRAPH-ARCHITECTURE.md`. |
| `hermes_agency.py` | Legacy/prototipo | Basado en Agency Swarm. No representa la arquitectura vigente. |

---

## Huecos detectados y resolución

### 1. Acceso a memoria persistente

Antes estaba claro que existiría `PersistentMemory`, pero no estaba suficientemente explícito cómo accederían los agentes a esa memoria sin consumir contexto de más.

Resolución:

- agregar `Memory MCP Server / Memory API interna` como puerta oficial;
- agregar `MemoryContextAgent` como agente liviano de recuperación/síntesis;
- prohibir acceso directo de agentes a SQLite;
- entregar memory packs por rol/fase/tarea.

Documentado en:

```text
MEMORY-MCP-ARCHITECTURE.md
PERSISTENT-MEMORY-SPEC.md
AGENT-REGISTRY.yaml
README.md
LANGGRAPH-ARCHITECTURE.md
```

---

### 2. Problema de compactación/context window

El riesgo del sistema es que los agentes llenen la ventana de contexto y, al compactarse, pierdan detalles críticos.

Resolución:

- budget de memoria por agente;
- memory packs chicos;
- tools determinísticas para buscar fuera del prompt;
- links a artifacts en vez de copiar artifacts enteros;
- MemoryContextAgent puede leer más, pero entrega poco;
- MemoryManager consolida después, no durante el razonamiento principal de cada agente.

Documentado en:

```text
MEMORY-MCP-ARCHITECTURE.md
PERSISTENT-MEMORY-SPEC.md
```

---

### 3. Orden de implementación

La documentación anterior decía “cerrar memoria” pero no fijaba claramente con qué arrancar.

Resolución:

Recomendación aprobada:

```text
Memory-first MVP, pero con scaffolding/test base antes.
```

Esto significa:

1. crear estructura Python moderna;
2. crear tests;
3. implementar MemoryStore;
4. implementar Memory MCP/tools;
5. implementar MemoryContextAgent;
6. integrar con SharedState mock;
7. recién después runtime LangGraph.

Documentado en:

```text
IMPLEMENTATION-PLAN.md
README.md
GUIA-MAESTRA.md
```

---

## Checklist antes de codear

| Ítem | Estado |
|---|---|
| Decisión de framework principal | OK: LangGraph |
| Decisión de tools | OK: MCP |
| Decisión de coordinación intra-run | OK: SharedState / Blackboard |
| Decisión de memoria persistente | OK: Hybrid Hermes Project Memory |
| Decisión de capa de acceso a memoria | OK: Memory MCP Server |
| Decisión de agente de recuperación liviano | OK: MemoryContextAgent |
| Decisión de consolidación | OK: MemoryManager |
| Agentes principales definidos | OK: `AGENT-REGISTRY.yaml` |
| Skills por agente definidas | OK inicial |
| Plan de implementación | OK: `IMPLEMENTATION-PLAN.md` |
| Tests existentes | PENDIENTE: no hay suite real todavía |
| Git inicializado | PENDIENTE: el directorio no es repo Git |
| Package layout moderno | PENDIENTE |
| Dependency manifest | PENDIENTE |
| Runtime funcional | PENDIENTE |

---

## Riesgos si se empieza a implementar sin esto

- construir agentes que carguen demasiado contexto;
- duplicar lógica de búsqueda en cada agente;
- mezclar SharedState con memoria histórica;
- dejar que cualquier agente escriba memoria durable;
- generar una DB llena de basura;
- compactaciones prematuras;
- pérdida de decisiones importantes;
- dificultad para agregar UI después.

---

## Decisión final de auditoría

La documentación ya está suficientemente completa para empezar implementación **después** de aplicar las actualizaciones de Memory MCP/MemoryContextAgent y guardar el plan.

No conviene arrancar por el swarm completo.

Conviene arrancar por:

```text
Scaffold + tests → MemoryStore → Memory MCP → MemoryContextAgent → MemoryManager básico → SharedState mock → LangGraph MVP
```

Motivo:

La memoria y el control de contexto son infraestructura transversal. Si se dejan para el final, después hay que rehacer prompts, agentes y flujos.
