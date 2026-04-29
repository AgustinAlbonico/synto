# Synto

> Sistema de orquestación multi-agente para operar equipos de agentes especializados con SDD, PRD-first, TDD, LangGraph, MCP y Skill Registry dinámico.

Estado actual: **arquitectura documentada, implementación pendiente**.

---

## Decisión actual

La versión anterior apuntaba a Agency Swarm. Esa decisión quedó reemplazada.

La arquitectura vigente es:

- **LangGraph** como runtime de orquestación.
- **MCP** como protocolo agent-to-tool.
- **SharedState / Blackboard** para coordinación entre agentes propios dentro de un run.
- **PersistentMemory / MemoryStore** para memoria cross-session y rehidratación automática de contexto.
- **Skill Registry dinámico** para cargar skills por agente y permitir skills nuevas agregadas por el usuario.
- **A2A** queda como capa futura, no como dependencia del MVP.
- **Web Interface** queda prevista como fase posterior, una vez estable el motor.

---

## Documentos principales

| Documento | Para qué sirve |
|---|---|
| `LANGGRAPH-ARCHITECTURE.md` | Arquitectura principal, capas, workflow, decisiones y roadmap. |
| `AGENT-REGISTRY.yaml` | Contrato de agentes: roles, restricciones, skills, tools MCP, inputs/outputs. |
| `SKILL-LOADING-SYSTEM.md` | Diseño del sistema de carga dinámica de skills. |
| `SHARED-STATE-SPEC.md` | Especificación del blackboard, slots, gates, artifacts y concurrencia. |
| `PERSISTENT-MEMORY-SPEC.md` | Memoria cross-session, MemoryStore, rehidratación automática y MemoryManager. |
| `MEMORY-ARCHITECTURE-RESEARCH.md` | Investigación comparativa: Engram, Obsidian, vector DB, graph/tree memory y decisión recomendada. |
| `MEMORY-MCP-ARCHITECTURE.md` | Capa aprobada de acceso a memoria: Memory MCP Server + MemoryContextAgent + control anti-compactación. |
| `DOCUMENTATION-AUDIT.md` | Auditoría de documentación y huecos cerrados antes de implementar. |
| `IMPLEMENTATION-PLAN.md` | Plan de implementación memory-first con tareas, archivos y verificaciones. |
| `WEB-INTERFACE-VISION.md` | Visión inicial de la interfaz web futura. |
| `GUIA-MAESTRA.md` | Documento histórico/base del proyecto. Mantiene decisiones previas y referencia general. |
| `DEFINICION-AGENTES.md` | Definición original de agentes. Reemplazada parcialmente por `AGENT-REGISTRY.yaml`. |

---

## Equipo Code Domain actual

El MVP del dominio Code incluye:

- HermesOrchestrator
- CodeOrchestrator
- BusinessAnalyst
- ProductManager
- Planner
- CodebaseExplorer
- Architect
- SystemDesigner
- Tester
- BackendImplementer
- FrontendImplementer
- ContractAligner
- Reviewer
- SecurityReviewer
- QAGatekeeper
- DependencyChecker
- TechnicalWriter
- ReleaseManager
- Builder

Además del equipo Code Domain, se agrega un agente/servicio cross-cutting:

- MemoryContextAgent / MemoryRetriever
- MemoryManager

`MemoryContextAgent` es un agente liviano: busca contexto relevante vía Memory MCP y arma memory packs chicos por agente para evitar consumo excesivo de contexto.

`MemoryManager` no es un implementador ni un agente de producto: es la capa encargada de consolidar aprendizajes, deduplicar, redactar secretos y persistir memoria canónica entre sesiones.

Cada agente tiene:

- rol específico;
- responsabilidades;
- restricciones;
- inputs/outputs;
- slots de escritura;
- skills base;
- skills dinámicas permitidas;
- tools MCP permitidas.

El contrato vivo está en `AGENT-REGISTRY.yaml`.

---

## Workflow previsto

```text
Intake
  → Discovery
  → PRD approval
  → Technical Planning paralelo
  → Spec/Design consolidation
  → TDD/Test Plan
  → Backend + Frontend implementation paralelo
  → SystemDesigner review loop
  → Contract alignment
  → Review + Security + Tests
  → QA + Dependency + Docs
  → Release/PR
  → Deploy opcional
  → Delivery
```

---

## Skill Registry dinámico

Objetivo:

- No cargar todas las skills siempre.
- Cada agente carga solo su repertorio útil.
- El usuario puede agregar skills nuevas encontradas en internet.
- Las skills externas pasan por inbox/quarantine/validación antes de asignarse.
- Se soportan base skills, skills manuales, triggers y carga lazy.

Ver: `SKILL-LOADING-SYSTEM.md`.

---

## SharedState / Blackboard

Objetivo:

- permitir agentes paralelos sin pisarse;
- versionar artefactos;
- pausar y retomar workflows;
- registrar eventos;
- exponer estado a una futura UI web.

Regla central:

> Los workers escriben en su slot. Los orquestadores/consolidadores escriben artefactos canónicos.

Ver: `SHARED-STATE-SPEC.md`.

---

## PersistentMemory / MemoryStore

Objetivo:

- recordar contexto útil entre sesiones;
- rehidratar automáticamente cada run con memoria relevante;
- construir memory packs por agente sin cargar toda la historia;
- guardar decisiones, preferencias, resúmenes de artifacts y aprendizajes;
- mantener provenance, auditoría, redacción de secretos y derecho a olvidar.

Regla central:

> SharedState coordina el presente. PersistentMemory trae contexto del pasado y consolida aprendizajes para el futuro.

Ver: `PERSISTENT-MEMORY-SPEC.md`.

Investigación comparativa y decisión de diseño:

- `MEMORY-ARCHITECTURE-RESEARCH.md`

Decisión operativa actual:

> La memoria no será un árbol puro ni una DB plana. Será un híbrido: árbol primario `Project -> Feature -> Topic`, grafo liviano de relaciones, SQLite/FTS5 como fuente canónica, embeddings opcionales y export a Obsidian como espejo humano-readable.

Decisión de acceso:

> Los agentes no consultan SQLite ni cargan toda la memoria. La memoria se expone mediante `Memory MCP Server`/tool layer; `MemoryContextAgent` arma memory packs chicos por rol/fase/tarea; `MemoryManager` consolida y guarda aprendizajes.

---

## Interfaz web futura

Sí está contemplada.

La UI debería funcionar como un **Hermes Command Center** con:

- dashboard de runs;
- timeline de agentes;
- aprobación de gates;
- blackboard viewer;
- skill manager;
- artifacts center;
- design system studio;
- chat lateral con HermesOrchestrator.

Ver: `WEB-INTERFACE-VISION.md`.

---

## Próximo paso recomendado

Después de revisar la documentación:

1. tomar `DOCUMENTATION-AUDIT.md` como checklist de cierre documental;
2. seguir `IMPLEMENTATION-PLAN.md` como roadmap operativo;
3. arrancar por el MVP memory-first:
   - scaffolding + tests;
   - MemoryStore SQLite/FTS5;
   - Memory MCP/tool layer;
   - MemoryContextAgent;
   - MemoryManager básico;
   - integración con SharedState mock;
4. después implementar el motor mínimo:
   - AgentRegistry loader;
   - SkillRegistry scanner;
   - SharedState models completos;
   - LangGraph runtime;
   - primer workflow mock end-to-end.

---

## Nota importante

El código existente (`hermes_agency.py`) pertenece al prototipo anterior basado en Agency Swarm y no representa la arquitectura vigente. Debe considerarse legacy/prototipo hasta migrarlo o reemplazarlo.
