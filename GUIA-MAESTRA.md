# Guía Maestra — Sistema de Orquestación Multi-Capa para Hermes

> **Versión:** 1.0.0  
> **Autor:** Agustín Albonico + Synto  
> **Propósito:** Documento único de referencia para reconstruir el sistema si se pierde contexto. Cada fase, cada agente, cada skill, cada decisión de diseño está acá.  
> **Regla de oro:** Si no está en esta guía, no existe todavía.

---

## 📋 Índice

1. [Filosofía de trabajo](#1-filosofía-de-trabajo)
2. [Arquitectura de capas](#2-arquitectura-de-capas)
3. [Mapeo de skills de Hermes por agente](#3-mapeo-de-skills-de-hermes-por-agente)
4. [Flujo SDD + PRD-first + TDD](#4-flujo-sdd--prd-first--tdd)
5. [Protocolo de mensajes entre agentes](#5-protocolo-de-mensajes-entre-agentes)
6. [Working Memory (estado compartido)](#6-working-memory-estado-compartido)
7. [Dashboards existentes (NO reinventar)](#7-dashboards-existentes-no-reinventar)
8. [Configuración de cada orquestador](#8-configuración-de-cada-orquestador)
9. [Roadmap de implementación](#9-roadmap-de-implementación)
10. [Decisiones de diseño ya tomadas](#10-decisiones-de-diseño-ya-tomadas)

---

## 1. Filosofía de trabajo

### 1.1 PRD-first (Product Requirements Document)
Antes de tocar UNA línea de código, se escribe un PRD completo que define:
- Qué problema resuelve
- Quién lo usa (personas)
- Qué funcionalidades incluye (y qué NO incluye — out of scope)
- Criterios de aceptación medibles
- Restricciones técnicas y de negocio

**Regla:** Sin PRD aprobado por el usuario, no se pasa a la siguiente fase.

### 1.2 TDD (Test Driven Development)
Antes de escribir código de producción, se escriben los tests que ese código debe pasar.

**Ciclo RED-GREEN-REFACTOR:**
1. **RED:** Escribir un test que falla (porque la funcionalidad no existe todavía)
2. **GREEN:** Escribir el código mínimo necesario para que pase
3. **REFACTOR:** Mejorar el código sin romper los tests

**Regla:** Si no hay test plan, no hay implementación.

### 1.3 Orquestación jerárquica
- El usuario habla SIEMPRE con un solo punto de contacto (Capa 0)
- Los orquestadores de dominio (Capa 1) nunca hablan directamente con el usuario
- Los specialists (Capa 2) nunca hablan entre sí, solo con su orquestador
- Las tools (Capa 3) no razonan, ejecutan

### 1.4 Skills nativas de Hermes
NO creamos nada desde cero si Hermes ya tiene una skill para eso. Cada agente debe cargar las skills relevantes antes de arrancar.

---

## 2. Arquitectura de capas

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA 0: HERMES ORCHESTRATOR (Tu punto de contacto único)  │
│  - Te escucha, hace preguntas de clarificación              │
│  - Activa el flujo SDD completo                             │
│  - NUNCA toca código, NUNCA hace research directo           │
│  - Skills: plan, writing-plans, subagent-driven-development │
└──────────────────────┬──────────────────────────────────────┘
                       │ delega a
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 1: DOMAIN ORCHESTRATORS                               │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ CodeOrche   │ │ ResearchOrc │ │ ContentOrc  │           │
│  │ - planner   │ │ - sourcer   │ │ - strategist│           │
│  │ - explorer  │ │ - analyst   │ │ - writer    │           │
│  │ - implement │ │ - synthe    │ │ - editor    │           │
│  │ - reviewer  │ │             │ │ - seo       │           │
│  │ - tester    │ │             │ │             │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐                           │
│  │ DevOpsOrc   │ │ DataOrc     │                           │
│  │ - architect │ │ - scraper   │                           │
│  │ - builder   │ │ - cleaner   │                           │
│  │ - validator │ │ - modeler   │                           │
│  │             │ │ - visualizer│                           │
│  └─────────────┘ └─────────────┘                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ delega a
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 2: SPECIALIST AGENTS                                  │
│  Cada specialist es un subagente con prompt + skills propias│
│  NO se comunican entre sí, solo con su orchestrator         │
└──────────────────────┬──────────────────────────────────────┘
                       │ invoca
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA 3: TOOL / UTILITY AGENTS                              │
│  FileReader, FileWriter, CodeExecutor, WebSearch,           │
│  GitOperator, TestRunner, Linter, SecurityScanner           │
│  Estos NO razonan. Ejecutan y devuelven resultados.         │
└─────────────────────────────────────────────────────────────┘
```

### Cross-cutting agents (aparecen cuando se necesitan)
- **SecurityReviewer** → antes de deploy
- **QAGatekeeper** → verifica que el output cumpla el PRD original
- **DependencyChecker** → verifica que no se rompa otra parte del sistema
- **DocumentationAgent** → genera docs al finalizar cada fase
- **ContextManager** → persiste estado entre sesiones

---

## 3. Mapeo de skills de Hermes por agente

Esta tabla es CRÍTICA. Cada agente, antes de arrancar, debe cargar sus skills asignadas.

### Capa 0: HermesOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `plan` | Escribir planes a .hermes/plans/ antes de ejecutar |
| `writing-plans` | Descomponer tareas en pasos ejecutables |
| `subagent-driven-development` | Delegar todo el trabajo real a subagentes |
| `obsidian` | Guardar descubrimientos en el vault de segundo cerebro |

### Capa 1: CodeOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `test-driven-development` | FORZAR tests antes de código en todo el dominio Code |
| `writing-plans` | Descomponer specs en subtareas atómicas |
| `codebase-inspection` | Entender el repo antes de tocar nada |
| `github-pr-workflow` | Gestionar branches, commits, PRs |
| `github-code-review` | Revisar PRs con inline comments |
| `github-issues` | Crear issues cuando se encuentran bugs |
| `requesting-code-review` | Pre-commit security scan + quality gates |
| `systematic-debugging` | Debuggear errores en 4 fases |
| `node-inspect-debugger` | Debug Node.js |
| `python-debugpy` | Debug Python |
| `architecture-diagram` | Generar diagramas de arquitectura del sistema |
| `claude-code` / `codex` / `opencode` | Delegar implementación a agentes de coding |

### Capa 1: ResearchOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `searxng-hermes-integration` | Búsqueda web propia (sin pagar APIs) |
| `arxiv` | Papers académicos |
| `blogwatcher` | Monitorear blogs y RSS |
| `polymarket` | Datos de mercado/predicciones |
| `llm-wiki` | Construir bases de conocimiento markdown |
| `obsidian` | Guardar investigación en el vault |

### Capa 1: ContentOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `frontend-design` | Diseñar interfaces web |
| `excalidraw` | Diagramas hand-drawn style |
| `architecture-diagram` | Diagramas técnicos |
| `claude-design` | Landing pages, decks, prototipos |
| `popular-web-designs` | 54 design systems reales como referencia |
| `youtube-content` | Transcripts de YouTube a resúmenes |
| `xurl` | Postear en X/Twitter |
| `obsidian` | Guardar contenido en el vault |

### Capa 1: DevOpsOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `cloudflare-tunnel-local-dev` | Exponer servicios locales a internet |
| `levantar-app` | Levantar proyectos locales + notificar Telegram |
| `hermes-gateway-background-wsl` | Levantar Hermes gateway como servicio |
| `webhook-subscriptions` | Webhooks para event-driven deploys |
| `searxng-setup` | Setup de SearXNG si se necesita |
| `openviking-setup` | Setup de OpenViking RAG si aplica |

### Capa 1: DataOrchestrator
| Skill | Para qué se usa |
|-------|----------------|
| `jupyter-live-kernel` | Análisis exploratorio con Python |
| `weights-and-biases` | Logging de experimentos de ML |
| `searxng-hermes-integration` | Scraping/web search |
| `huggingface-hub` | Descargar datasets y modelos |

### Cross-cutting agents
| Agente | Skills |
|--------|--------|
| SecurityReviewer | `requesting-code-review` (security scan) |
| QAGatekeeper | `systematic-debugging`, `codebase-inspection` |
| DocumentationAgent | `obsidian` |
| ContextManager | `obsidian` (persistencia en vault) |

---

## 4. Flujo SDD + PRD-first + TDD

### Diagrama del flujo completo

```
Usuario dice: "Quiero X"
    │
    ▼
┌─────────────────────────────────────┐
│ FASE 1: DISCOVERY                   │
│ Output: discovery.md                │
│ ¿Aprobado? ──NO──► itera           │
│     │ SÍ                            │
│     ▼                               │
│ FASE 2: PRD (Product Requirements)  │
│ Output: prd.md                      │
│ ¿Aprobado? ──NO──► itera           │
│     │ SÍ                            │
│     ▼                               │
│ FASE 3: SPEC (Technical Spec)       │
│ Output: spec.md + task-graph.json   │
│ ¿Aprobado? ──NO──► itera           │
│     │ SÍ                            │
│     ▼                               │
│ FASE 4: DESIGN                      │
│ Output: design.md (arquitectura)    │
│     │                               │
│     ▼                               │
│ FASE 5: TEST PLAN (TDD)             │
│ Output: test-plan.md                │
│     │                               │
│     ▼                               │
│ FASE 6: IMPLEMENTATION              │
│ Output: código + tasks/result.md    │
│     │                               │
│     ▼                               │
│ FASE 7: TESTING                     │
│ Output: test-results.md             │
│ ¿Pasa? ──NO──► vuelve a Fase 6     │
│     │ SÍ (máx 3 reintentos)         │
│     ▼                               │
│ FASE 8: DEPLOY                      │
│ Output: deploy.md + artefacto final │
│     │                               │
│     ▼                               │
│ Entrega al usuario                  │
└─────────────────────────────────────┘
```

### Detalle de cada fase

#### FASE 1: Discovery (Descubrimiento)
**Quién:** HermesOrchestrator  
**Skills:** `plan`, `writing-plans`, `obsidian`  
**Input:** Petición del usuario (vaga o específica)  
**Output:** `discovery.md`

**Contenido de `discovery.md`:**
```markdown
# Discovery: [Nombre del proyecto]

## Objetivo
[En una oración, qué quiere el usuario]

## Audiencia
[Quién va a usar esto]

## Contexto actual
[Qué tiene hoy, qué falta]

## Preguntas de clarificación
- [Pregunta 1]: [Respuesta del usuario]
- [Pregunta 2]: [Respuesta del usuario]

## Restricciones identificadas
- [Restricción 1]

## Out of scope (qué NO incluye)
- [Lo que quedó fuera]

## Formato de entrega esperado
[Repo, landing, PDF, API, etc.]
```

#### FASE 2: PRD (Product Requirements Document)
**Quién:** DomainOrchestrator correspondiente  
**Skills:** `writing-plans`, `obsidian`  
**Input:** `discovery.md`  
**Output:** `prd.md`  
**Gate:** Aprobación del usuario obligatoria

**Contenido de `prd.md`:**
```markdown
# PRD: [Nombre del proyecto]

## 1. Resumen ejecutivo
[Qué es, para quién, por qué]

## 2. Objetivos
[Goals medibles]

## 3. Usuarios / Personas
[Perfiles de usuario con necesidades específicas]

## 4. Funcionalidades (Features)
### 4.1 Must Have
- [F1] [Descripción] → Criterio de aceptación: [X]
- [F2] [Descripción] → Criterio de aceptación: [Y]

### 4.2 Should Have
- [F3] ...

### 4.3 Nice to Have
- [F4] ...

## 5. Restricciones
- Técnicas: [stack, compatibilidad]
- Negocio: [presupuesto, tiempo]
- Legales: [compliance, GDPR, etc.]

## 6. Criterios de aceptación generales
[Qué significa "listo" para este proyecto]

## 7. Out of Scope
[Lo que NO vamos a hacer]

## 8. Métricas de éxito
[Cómo medimos si funcionó]
```

#### FASE 3: SPEC (Especificación técnica)
**Quién:** CodeOrchestrator → Specialist Planner  
**Skills:** `writing-plans`, `codebase-inspection`, `architecture-diagram`  
**Input:** `prd.md`  
**Output:** `spec.md` + `task-graph.json`  
**Gate:** Aprobación del usuario

**Contenido de `spec.md`:**
```markdown
# Spec Técnica: [Nombre del proyecto]

## 1. Arquitectura propuesta
[Diagrama + explicación]

## 2. Stack tecnológico
[Frameworks, librerías, versiones]

## 3. Componentes / Módulos
### 3.1 [Módulo A]
- Responsabilidad: [qué hace]
- Inputs: [qué recibe]
- Outputs: [qué devuelve]
- Dependencias: [de qué depende]

## 4. Task Graph
[Descripción textual del grafo de tareas]

## 5. API / Interfaces
[Endpoints, contratos de datos]

## 6. Modelo de datos
[Entidades, relaciones]

## 7. Decisiones técnicas
[Por qué elegimos X sobre Y]
```

**Contenido de `task-graph.json`:**
```json
{
  "project": "nombre-proyecto",
  "tasks": [
    {
      "id": "T001",
      "name": "Explorar codebase",
      "description": "Entender estructura actual del repo",
      "specialist": "explorer",
      "depends_on": [],
      "outputs": ["codebase-report.md"],
      "estimated_effort": "30min"
    },
    {
      "id": "T002",
      "name": "Implementar auth",
      "description": "JWT login/signup",
      "specialist": "implementer",
      "depends_on": ["T001"],
      "outputs": ["auth.module.ts", "auth.test.ts"],
      "estimated_effort": "2h"
    }
  ]
}
```

#### FASE 4: DESIGN (Diseño de arquitectura)
**Quién:** CodeOrchestrator → Specialist Architect (si aplica) o el mismo Planner  
**Skills:** `architecture-diagram`, `excalidraw`  
**Input:** `spec.md`  
**Output:** `design.md` + diagramas

**Contenido de `design.md`:**
```markdown
# Design: [Nombre del proyecto]

## 1. Diagrama de arquitectura
[Imagen o ASCII art]

## 2. Diagrama de flujo de datos
[Cómo viaja la información]

## 3. Decisiones de diseño
[ADR - Architecture Decision Records]

## 4. Patrones aplicados
[MVC, Repository, CQRS, etc.]
```

#### FASE 5: TEST PLAN (Plan de tests — TDD)
**Quién:** CodeOrchestrator → Specialist Tester  
**Skills:** `test-driven-development`  
**Input:** `spec.md` + `design.md`  
**Output:** `test-plan.md`  
**Regla:** Estos tests se escriben ANTES del código de producción.

**Contenido de `test-plan.md`:**
```markdown
# Test Plan: [Nombre del proyecto]

## 1. Tests unitarios
### [Módulo A]
- `test_should_login_with_valid_credentials()`
  - Setup: [mock de DB, credenciales válidas]
  - Execute: [llamar a login()]
  - Assert: [token JWT retornado, status 200]
  
- `test_should_reject_invalid_password()`
  - Setup: [usuario existente, password incorrecto]
  - Execute: [llamar a login()]
  - Assert: [status 401, mensaje "Invalid credentials"]

## 2. Tests de integración
[Flujos end-to-end]

## 3. Tests de seguridad
[OWASP top 10 relevantes]

## 4. Tests de performance
[Cargas esperadas, tiempos de respuesta]

## 5. Mocks / Stubs necesarios
[Qué vamos a mockear]
```

#### FASE 6: IMPLEMENTATION
**Quién:** CodeOrchestrator → Specialist Implementer  
**Skills:** `claude-code` / `codex` / `opencode`, `node-inspect-debugger`, `python-debugpy`  
**Input:** `spec.md` + `test-plan.md` + contexto de tareas previas  
**Output:** Código + `tasks/Txxx/result.md`

**Reglas:**
- Implementer NUNCA modifica el PRD ni la Spec
- Si encuentra que algo no se puede hacer, levanta un `error` al orchestrator
- El orchestrator decide si replanifica la spec o levanta el issue al usuario
- Cada tarea tiene máximo 3 reintentos antes de escalar

**Formato de `tasks/Txxx/result.md`:**
```markdown
# Resultado: [Nombre de tarea]

## Estado: [completed / failed / needs-review]

## Archivos modificados
- `ruta/al/archivo.ts`

## Decisiones tomadas
[Por qué hice X en vez de Y]

## Bloqueos encontrados
[Si aplica, con contexto]

## Próximos pasos sugeridos
```

#### FASE 7: TESTING (Validación)
**Quién:**
1. Self-test: Implementer corre tests antes de entregar
2. Specialist Reviewer: Revisa código vs spec
3. QAGatekeeper: Revisa conjunto completo vs PRD original

**Skills:** `test-driven-development`, `requesting-code-review`, `systematic-debugging`  
**Input:** Código + `test-plan.md` + `prd.md`  
**Output:** `test-results.md` + `reviews/final-review.md`

**Gate:** Si falla → vuelve a Fase 6 (máximo 3 veces)  
**Gate:** Si pasa 3 veces → escala al usuario con el problema

#### FASE 8: DEPLOY
**Quién:** DevOpsOrchestrator  
**Skills:** `cloudflare-tunnel-local-dev`, `levantar-app`, `hermes-gateway-background-wsl`  
**Input:** Código aprobado  
**Output:** Deploy + `deploy.md`

**Flujo:**
1. SecurityReviewer escanea secrets/vulnerabilidades
2. DependencyChecker verifica que no se rompa nada
3. DevOpsOrchestrator ejecuta deploy
4. DocumentationAgent genera README/CHANGELOG
5. HermesOrchestrator presenta resultado al usuario

---

## 5. Protocolo de mensajes entre agentes

### Formato de mensaje (JSON)
```json
{
  "message_id": "uuid-v4",
  "context_id": "nombre-proyecto",
  "timestamp": "ISO-8601",
  "from": "agente-emisor",
  "to": "agente-receptor",
  "type": "task | review | question | result | error | approval-request",
  "payload": {
    "... contenido específico ..."
  },
  "references": ["task-001", "spec.md"],
  "priority": "low | normal | high | critical",
  "requires_response": true | false
}
```

### Tipos de mensaje
| Tipo | Cuándo se usa | Quién lo envía |
|------|--------------|----------------|
| `task` | Delegar una subtarea | Orchestrator → Specialist |
| `review` | Pedir revisión de output | Implementer → Reviewer |
| `question` | Duda que bloquea el avance | Specialist → Orchestrator |
| `result` | Entrega de tarea completada | Specialist → Orchestrator |
| `error` | Fallo que requiere decisión | Cualquiera → Orchestrator |
| `approval-request` | Pedir OK del usuario | Orchestrator → Usuario |

### Reglas de routing
1. **Capa 0 solo habla con Capa 1** (y el usuario)
2. **Capa 1 delega en Capa 2** y consolida antes de volver a Capa 0
3. **Capa 2 invoca Capa 3** libremente
4. **Capa 3 NO habla entre sí** (salvo chaining técnico)
5. **Cross-cutting agents** son invocados por Capa 1 o 2, reportan a quien los invocó

---

## 6. Working Memory (estado compartido)

### Ubicación
```
/home/agust/synto/workspace/.hermes-state/
├── README.md
└── {context_id}/
    ├── discovery.md
    ├── prd.md
    ├── spec.md
    ├── task-graph.json
    ├── design.md
    ├── test-plan.md
    ├── tasks/
    │   ├── T001-explorar/
    │   │   ├── result.md
    │   │   └── files/
    │   └── T002-implementar/
    │       ├── result.md
    │       └── files/
    ├── reviews/
    │   └── final-review.md
    ├── test-results.md
    ├── deploy.md
    └── final-deliverable/
```

### Contrato de persistencia
- Cada fase produce **exactamente un artefacto principal**
- El artefacto de la fase N es input de la fase N+1
- Los agentes NO se "cuentan" lo que hicieron: leen los archivos del working memory
- Todo se guarda en markdown (human-readable) + JSON (machine-readable donde aplica)

---

## 7. Dashboards existentes (NO reinventar)

### Opciones investigadas

| Proyecto | Qué hace | URL / Repo | Estado |
|----------|---------|------------|--------|
| **LangSmith** (LangChain) | Tracing, evaluación, monitoreo de agentes | langchain.com/langsmith | Pago (tiene free tier) |
| **Langfuse** | Open source, self-hosted, tracing de LLMs | langfuse.com | Open source ✅ |
| **AgentOps** | Monitoreo de agentes, costos, tracing | agentops.ai | Freemium |
| **Phoenix** (Arize AI) | Observabilidad de LLMs, evaluación | arize.com/phoenix | Open source ✅ |
| **Helicone** | Logging, caching, rate limiting de LLMs | helicone.ai | Open source ✅ |
| **CrewAI Studio** | Dashboard visual para Crews | crewai.com | Pago |

### Recomendación para este proyecto
Usar **Langfuse** (open source, self-hosted, se puede correr local con Docker):
- Tracea cada llamada a LLM (costos, latencia, tokens)
- Muestra el grafo de ejecución de agentes
- Soporta evaluaciones automáticas
- Tiene API REST para integrar con nuestros scripts

Alternativa si no queremos self-host: **Phoenix** (más simple, también open source).

**NO vamos a construir un dashboard desde cero.**

---

## 8. Configuración de cada orquestador

### 8.1 HermesOrchestrator (Capa 0)

```yaml
nombre: HermesOrchestrator
rol: Punto de contacto único del usuario
scope:
  - Escuchar peticiones del usuario
  - Hacer preguntas de clarificación (máx 3-4 intercambios)
  - Activar DomainOrchestrators
  - Presentar resultados finales
  - Pedir aprobaciones en gates
prohibido:
  - Escribir código
  - Hacer research directo
  - Ejecutar tests
  - Deployar
delega_a:
  - CodeOrchestrator: peticiones de software
  - ResearchOrchestrator: investigación
  - ContentOrchestrator: contenido/multimedia
  - DevOpsOrchestrator: infra/deploy
  - DataOrchestrator: datos/scraping
skills_requeridas:
  - plan
  - writing-plans
  - subagent-driven-development
  - obsidian
formato_salida: |
  Siempre responde al usuario en español rioplatense.
  Usá "vos" en vez de "tú".
  Resumí el estado en bullets.
  Cuando delegues, decí: "Lo delego al equipo de [dominio]..."
```

### 8.2 CodeOrchestrator (Capa 1)

```yaml
nombre: CodeOrchestrator
rol: Jefe de ingeniería de software
scope:
  - Convertir PRD en Spec técnica
  - Gestionar el Task Graph
  - Asignar tareas a specialists
  - Consolidar resultados de implementación
  - Coordinar Testing y Deploy técnico
specialists:
  - Planner: descompone specs en subtareas
  - Explorer: lee y entiende codebases
  - Implementer: escribe código
  - Reviewer: revisa código vs spec
  - Tester: escribe y corre tests
prohibido:
  - Hablar directamente con el usuario
  - Modificar el PRD sin aprobación
  - Saltear la fase de tests
skills_requeridas:
  - test-driven-development
  - writing-plans
  - codebase-inspection
  - github-pr-workflow
  - github-code-review
  - github-issues
  - requesting-code-review
  - systematic-debugging
  - architecture-diagram
  - claude-code / codex / opencode
formato_salida: |
  Los artefactos técnicos se escriben en Markdown en el working memory.
  Los task graphs se escriben en JSON.
  Los diagramas se generan con architecture-diagram o excalidraw.
reglas:
  - Siempre correr codebase-inspection antes de tocar un repo nuevo
  - Nunca mergear sin code review
  - Nunca deployar sin security review
  - Si un specialist falla 3 veces, escalar al orchestrator principal
```

### 8.3 ResearchOrchestrator (Capa 1)

```yaml
nombre: ResearchOrchestrator
rol: Jefe de investigación
scope:
  - Investigación de mercado, competencia, papers
  - Síntesis de información en reportes
  - Validación de fuentes
specialists:
  - Sourcer: busca fuentes (web, papers, APIs)
  - Analyst: extrae insights
  - Synthesizer: junta todo en reportes coherentes
skills_requeridas:
  - searxng-hermes-integration
  - arxiv
  - blogwatcher
  - polymarket
  - llm-wiki
  - obsidian
reglas:
  - Siempre citar fuentes
  - Distinguir entre hecho verificado y opinión/hipótesis
  - Priorizar fuentes primarias sobre secundarias
```

### 8.4 ContentOrchestrator (Capa 1)

```yaml
nombre: ContentOrchestrator
rol: Jefe de contenido y diseño
scope:
  - Copy, landing pages, social media
  - Diseño de interfaces
  - Multimedia
specialists:
  - Strategist: define ángulo, tono, keywords
  - Writer: produce borradores
  - Editor: revisa claridad y coherencia
  - SEO: optimiza para búsqueda
skills_requeridas:
  - frontend-design
  - claude-design
  - excalidraw
  - popular-web-designs
  - xurl
  - obsidian
reglas:
  - Todo contenido debe pasar por Editor antes de entregar
  - El Strategist define el tono (rioplatense profesional)
  - El SEO revisa después del Editor, no antes
```

### 8.5 DevOpsOrchestrator (Capa 1)

```yaml
nombre: DevOpsOrchestrator
rol: Jefe de infraestructura y deploy
scope:
  - Diseño de infraestructura
  - CI/CD
  - Deploys
  - Monitoreo
specialists:
  - Architect: diseña infra/config
  - Builder: escribe Dockerfiles, workflows, scripts
  - Validator: testea en entorno aislado
skills_requeridas:
  - cloudflare-tunnel-local-dev
  - levantar-app
  - hermes-gateway-background-wsl
  - webhook-subscriptions
reglas:
  - Nunca deployar a producción sin staging
  - Siempre tener rollback plan
  - Documentar cada deploy
```

### 8.6 DataOrchestrator (Capa 1)

```yaml
nombre: DataOrchestrator
rol: Jefe de datos
scope:
  - Scraping
  - ETL
  - Análisis
  - Dashboards
specialists:
  - Scraper: extrae datos de fuentes
  - Cleaner: limpia y normaliza
  - Modeler: modela datos/ML
  - Visualizer: genera dashboards
skills_requeridas:
  - jupyter-live-kernel
  - weights-and-biases
  - searxng-hermes-integration
  - huggingface-hub
reglas:
  - Nunca scrapear sin respetar robots.txt
  - Documentar fuentes y métodos
  - Versionar datasets como código
```

---

## 8.1 Sistema de Modelos Configurables por Agente

Cada agente tiene su propio modelo asignado según la complejidad de su tarea.

### Archivo de configuración
```config/models.yaml``` — acá definís qué modelo usa cada agente.

### Profiles de modelos

| Profile | Para qué sirve | Modelos OpenRouter | Modelos OpenAI |
|---------|---------------|-------------------|----------------|
| **premium** | Razonamiento complejo, conversación natural, decisiones importantes | Claude Sonnet 4 | GPT-4o |
| **balanced** | Tareas técnicas, implementación, análisis | Gemini Flash Thinking (free) | GPT-4o-mini |
| **economy** | Tool agents, tareas repetitivas, búsquedas | Llama 3.2 3B (free) | GPT-3.5-turbo |

### Asignación por agente (ejemplo)

```yaml
# Capa 0: Orquestador principal → necesita el mejor modelo
HermesOrchestrator: premium

# Capa 1: Domain Orchestrators → razonamiento + coordinación
CodeOrchestrator: premium
BusinessOrchestrator: premium
ResearchOrchestrator: balanced

# Capa 2: Specialists → según complejidad
Planner: premium          # Descomponer specs = complejo
Implementer: balanced     # Codear = tarea técnica
Sourcer: economy          # Buscar fuentes = repetitivo
SEO: economy             # Keywords = repetitivo
```

### Cómo cambiar un modelo

1. Editá `config/models.yaml`
2. Cambiá el profile del agente (premium/balanced/economy)
3. O definí un modelo específico:
   ```yaml
   Implementer: "openrouter/anthropic/claude-sonnet-4"
   ```
4. Recargá la agencia — no hace falta reiniciar

### Cómo cambiar de proveedor

```bash
# En .env:
MODEL_PROVIDER=openrouter   # o openai, anthropic
```

Cambia el proveedor y todos los agentes usan automáticamente el modelo correspondiente de ese proveedor.

### Costo estimado por ejecución

| Dominio | Agentes involucrados | Costo aproximado (con free models) |
|---------|---------------------|-----------------------------------|
| Code (feature chica) | 5-7 | $0 (con OpenRouter free) |
| Research (reporte) | 3-4 | $0 (con OpenRouter free) |
| Business (validación) | 3 | $0 (con OpenRouter free) |

Con modelos de pago: ~$0.10-$0.50 por ejecución de feature chica.

---

## 9. Roadmap de implementación

### Fase 0: Fundamentos (esta sesión)
- [x] Armar la Guía Maestra (este documento)
- [ ] Crear prompts de sistema para cada orquestador
- [ ] Crear templates (PRD, Discovery, Spec, Test Plan)
- [ ] Crear protocolo de mensajes
- [ ] Crear scripts de orquestación
- [ ] Crear skills de SDD para Hermes

### Fase 1: MVP Code Domain
- [ ] Implementar HermesOrchestrator con prompts reales
- [ ] Implementar CodeOrchestrator con todos sus specialists
- [ ] Crear un proyecto de ejemplo completo (landing Python)
- [ ] Integrar TDD (test-driven-development skill)
- [ ] Integrar Langfuse para tracing

### Fase 2: Testing + DevOps
- [ ] Activar SecurityReviewer, QAGatekeeper
- [ ] Activar DevOpsOrchestrator
- [ ] Pipeline de CI/CD con GitHub Actions
- [ ] Deploy automatizado

### Fase 3: Otros dominios
- [ ] ResearchOrchestrator
- [ ] ContentOrchestrator
- [ ] DataOrchestrator

### Fase 4: Optimización
- [ ] Paralelismo de tareas independientes
- [ ] Cache de resultados de Tool Agents
- [ ] Evaluación automática con Langfuse

---

## 10. Decisiones de diseño ya tomadas

| Decisión | Qué elegimos | Por qué |
|----------|-------------|---------|
| PRD-first | Sí, obligatorio | Evita "y si agregamos esto también" a mitad de camino |
| TDD | Sí, obligatorio | Tests antes de código = menos bugs, mejor diseño |
| Dashboard | Langfuse (open source) | No reinventamos la rueda, tracing nativo de LLMs |
| Working Memory | Archivos en disco (Markdown + JSON) | Human-readable, debuggeable, persistente entre sesiones |
| Lenguaje de comunicación | Español rioplatense | Preferencia del usuario |
| Skills de Hermes | Usar nativas siempre que existan | No duplicar funcionalidad |
| Aprobaciones del usuario | Gates en PRD, Spec, y Deploy | El usuario tiene veto en momentos clave |
| Máximo reintentos | 3 por tarea | Evita loops infinitos |
| Modelo para Capa 0/1 | Grande (Claude/GPT-4) | Necesitan razonamiento complejo |
| Modelo para Capa 3 | Chico (GPT-4o-mini/Haiku) | Solo ejecutan, no razonan |
| Framework vigente | LangGraph | Agency Swarm queda legacy; LangGraph da state, checkpointing, sub-grafos y human-in-the-loop |
| Tools externas | MCP | Estándar agent-to-tool, evita integraciones custom por agente |
| Coordinación interna | SharedState / Blackboard | Permite paralelismo seguro sin que los agentes se pisen |
| Memoria persistente | PersistentMemory / MemoryStore | Rehidrata contexto entre sesiones sin cargar toda la historia en el prompt |
| Skills | Skill Registry dinámico | Cada agente carga su repertorio útil; se pueden agregar skills externas después |
| A2A | Futuro/opcional | Útil para agentes externos; no es dependencia del MVP |
| UI Web | Fase posterior documentada | El motor nace UI-ready, pero se implementa después de tener runtime estable |

---

## 11. Actualización 2026-04-28 — Contrato vigente

La documentación nueva reemplaza el enfoque de prototipo Agency Swarm como dirección principal.

Documentos vigentes:

- `LANGGRAPH-ARCHITECTURE.md` — arquitectura principal LangGraph + MCP.
- `AGENT-REGISTRY.yaml` — contrato vivo de agentes, skills, permisos y restricciones.
- `SKILL-LOADING-SYSTEM.md` — sistema de carga dinámica de skills.
- `SHARED-STATE-SPEC.md` — blackboard, slots, gates, artifacts y concurrencia.
- `PERSISTENT-MEMORY-SPEC.md` — memoria cross-session, MemoryStore, rehidratación automática y MemoryManager.
- `MEMORY-ARCHITECTURE-RESEARCH.md` — investigación Engram/Obsidian/vector/graph y decisión Hybrid Hermes Project Memory.
- `MEMORY-MCP-ARCHITECTURE.md` — capa aprobada de acceso a memoria: Memory MCP Server + MemoryContextAgent + control anti-compactación.
- `DOCUMENTATION-AUDIT.md` — auditoría de documentación antes de implementar.
- `IMPLEMENTATION-PLAN.md` — roadmap operativo memory-first para empezar implementación.
- `WEB-INTERFACE-VISION.md` — visión de interfaz web futura.

Decisión importante:

> El código actual `hermes_agency.py` debe considerarse legacy/prototipo hasta migrarlo o reemplazarlo por el runtime LangGraph.

Próximo paso recomendado:

1. Tomar `DOCUMENTATION-AUDIT.md` como checklist documental.
2. Seguir `IMPLEMENTATION-PLAN.md` como roadmap operativo.
3. Implementar MVP memory-first:
   - scaffolding + tests;
   - MemoryStore SQLite/FTS5;
   - Memory MCP/tool layer;
   - MemoryContextAgent;
   - MemoryManager básico;
   - integración con SharedState mock.
4. Después implementar AgentRegistry + SkillRegistry + SharedState completo.
5. Implementar primer workflow LangGraph mock end-to-end.

---

*Última actualización: 2026-04-28*  
*Próximo paso: implementar MVP memory-first y luego motor mínimo LangGraph*
