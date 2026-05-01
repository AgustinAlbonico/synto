# Synto — Flujo Nuevo Proyecto + Flujo Proyecto Existente

## Estado: diseño aprobado

---

## Flujo A — Proyecto NUEVO (sin inicializar)

```
╔══════════════════════════════════════════════════════════════════╗
║             FASE 1: CONFIGURACIÓN INICIAL                     ║
║             (Solo se ejecuta una vez por proyecto)            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────┐                                           ║
║  │ ProjectInitAgent│ ← Detecta que no existe workspace        ║
║  │ (entrevista     │   y activa este flujo automáticamente     ║
║  │  general)       │                                           ║
║  └────────┬────────┘                                           ║
║           │                                                     ║
║           ▼                                                     ║
║  ┌─────────────────┐    ┌─────────────────┐                   ║
║  │ InterviewAgent   │───→│ RequirementsAgent│                  ║
║  │ (preguntas      │    │ (no funcionales  │                  ║
║  │  generales sobre │    │  de alto nivel)  │                  ║
║  │  el proyecto)   │    │                  │                  ║
║  └────────┬────────┘    └────────┬────────┘                  ║
║           │                         │                           ║
║           │                         ▼                           ║
║  ┌─────────────────────────────────────────────┐               ║
║  │ TechAgent                                  │               ║
║  │ (asesor de stack tecnológico)              │               ║
║  │                                             │               ║
║  │ Recibe: contexto del proyecto               │               ║
║  │ Hace preguntas hasta definir:              │               ║
║  │   • backend: NestJS / Go / FastAPI / ...  │               ║
║  │   • frontend: React / Vue / Next / ...    │               ║
║  │   • database: PostgreSQL / Mongo / ...    │               ║
║  │   • auth: JWT / OAuth / Session / ...     │               ║
║  │   • deploy: Docker / Vercel / Railway / .│               ║
║  │   • extras: Redis, S3, etc.              │               ║
║  │                                             │               ║
║  │ Usuario confirma stack                       │               ║
║  └────────┬────────────────────────────────────┘               ║
║           │                                                     ║
║           ▼                                                     ║
║  ┌─────────────────────────────────────────────┐               ║
║  │ ProjectInitializerAgent                      │               ║
║  │ (inicializa el proyecto)                    │               ║
║  │                                             │               ║
║  │ Ejecuta según stack definido:               │               ║
║  │   • Crea estructura de carpetas             │               ║
║  │   • Git init + gitignore                    │               ║
║  │   • Instala dependencias                     │               ║
║  │   • Crea archivos base del stack            │               ║
║  │   • Crea workspace/.synto/config.yaml      │               ║
║  │   • Guarda stack en SharedState              │               ║
║  │                                             │               ║
║  │ Artefactos:                                 │               ║
║  │   workspace/.synto/config.yaml ← stack     │               ║
║  │   Proyecto inicializado                     │               ║
║  └────────┬────────────────────────────────────┘               ║
║           │                                                     ║
║           ▼                                                     ║
║  ══► ENTRA AL FLUJO B (proyecto existente) ══                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Agentes de Fase 1

| Agente | Rol | Input | Output |
|--------|-----|-------|--------|
| `ProjectInitAgent` | Detecta contexto nuevo y activa flujo | Idea crude del usuario | Flag `new_project=true` |
| `InterviewAgent` | Entrevista general | Idea del usuario | `01-discovery/context.md` |
| `RequirementsAgent` | Requisitos no funcionales altos | Contexto del proyecto | `01-discovery/non-functional.md` |
| `TechAgent` | Asesor de stack | Contexto + requisitos no func. | `01-discovery/stack.md` |
| `ProjectInitializerAgent` | Ejecuta inicialización | Stack confirmado | Proyecto creado + `.synto/config.yaml` |

### Preguntas del TechAgent

```
1. Backend o solo API?
   → API REST → FastAPI/NestJS
   → API + lógica compleja → NestJS
   → Microservicios → Go

2. Frontend o solo panel admin?
   → SPA → React/Vue
   → SSR → Next.js
   → Solo admin → React + Tailwind
   → Sin frontend (mobile-first) → Solo API

3. Base de datos?
   → Relacional → PostgreSQL
   → Documentos → MongoDB
   → Llave-valor → Redis
   → Mixtos → PostgreSQL + Redis

4. Autenticación?
   → JWT simple → sin OAuth
   → OAuth (Google, GitHub) → Auth0/Supabase
   → SSO corporativo → LDAP

5. Tiempo real?
   → WebSockets → Socket.io / Pusher
   → No → skip

6. Deploy target?
   → Contenedores → Docker + Railway/ECS
   → Serverless → Vercel / Render
   → VPS → Docker Compose + Nginx
```

---

## Flujo B — Proyecto EXISTENTE (ya inicializado)

```
╔══════════════════════════════════════════════════════════════════╗
║             FASE 2: DESARROLLO NORMAL                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────┐    ┌─────────────────┐                    ║
║  │ InterviewAgent   │──→│ RequirementsAgent│                    ║
║  │ (entrevista     │    │ (genera reqs.md) │                    ║
║  │  específica)    │    │ funcs + no funcs │                    ║
║  └────────┬────────┘    └────────┬────────┘                    ║
║           │                         │                             ║
║           ▼                         ▼                             ║
║  ┌─────────────────────────────────────────┐                   ║
║  │ PlannerAgent                            │                   ║
║  │ (genera tareas mínimas, testeables)     │                   ║
║  └────────┬────────────────────────────────┘                   ║
║           │                                                       ║
║           ▼                                                       ║
║  ┌─────────────────┐                                             ║
║  │ TDDAgent        │  ← CORRECTO: TDD PRIMERO                    ║
║  │ (escribe tests  │      Escribe los tests que                  ║
║  │  ANTES de       │      backend y frontend                     ║
║  │  implementar)   │      van a implementar                     ║
║  └────────┬────────┘                                             ║
║           │                                                       ║
║           │ Los tests ya existen.                                ║
║           │ Backend y Frontend van a implementar                  ║
║           │ para que estos tests pasen.                           ║
║           │                                                       ║
║           ▼                                                       ║
║  ┌─────────────────┐         ┌─────────────────┐                ║
║  │ BackendAgent    │◄────────│    Frontend     │                ║
║  │                 │  iteran  │    Agent        │                ║
║  │ Ejecuta tests   │  si      │                 │                ║
║  │ Si fallan →     │  fallan  │ Ejecuta tests  │                ║
║  │ reintenta       │          │ Si fallan →     │                ║
║  │ (max 3 veces)   │          │ reintenta       │                ║
║  └────────┬────────┘          └────────┬────────┘                ║
║           │                             │                         ║
║           │         ┌───────────────────┘                        ║
║           │         │                                             ║
║           ▼         ▼                                             ║
║  ┌─────────────────────────────────────────┐                   ║
║  │ ReviewAgent                             │                   ║
║  │ (revisa código vs spec, seguridad,      │                   ║
║  │  estilo)                                │                   ║
║  └────────┬────────────────────────────────┘                   ║
║           │                                                       ║
║           ▼                                                       ║
║  ┌─────────────────────────────────────────┐                   ║
║  │ QAAgent                                │                   ║
║  │ (valida coverage, criteria, deploy)    │                   ║
║  └─────────────────────────────────────────┘                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Loop TDD

```
TDDAgent escribe tests (backend + frontend)
         │
         ├─→ BackendAgent implementa
         │        │
         │        ├─→ corre tests backend
         │        │        │
         │        │        ├─→ PASAN ──→ siguiente
         │        │        └─→ FALLAN ──→ reintenta (max 3)
         │        │                      │
         │        │                      └─→ revise + reimplement
         │        │
         │        └─→ mismo para frontend
         │
         └─→ ReviewAgent
                  │
                  └─→ QAAgent
```

---

## Detección automática de flujo

```
Usuario dice "quiero hacer..."
     │
     ├─→ ¿Existe workspace/.synto/config.yaml?
     │       │
     │       ├─→ SÍ  → Flujo B (desarrollo normal)
     │       │
     │       └─→ NO  → Flujo A (configuración inicial)
     │                   → luego pasa a Flujo B
```

---

## Archivos a crear/modificar

### Nuevos prompts (agents/prompts/)

| Archivo | Agente | Descripción |
|---------|--------|-------------|
| `specialist-project-init.md` | ProjectInitAgent | Detecta contexto nuevo |
| `specialist-interview.md` | InterviewAgent | Entrevista preguntas |
| `specialist-tech-advisor.md` | TechAgent | Asesor de stack |
| `specialist-project-initializer.md` | ProjectInitializerAgent | Inicializa proyecto |
| `specialist-requirements.md` | RequirementsAgent | Requistos funcionales |
| `specialist-tdd.md` | TDDAgent | TDD-first (existente como specialist-tester.md) |

### Agentes Python (src/synto/agents/)

| Archivo | Cambio |
|---------|--------|
| `workflow_agents.py` | Agregar: `ProjectInitAgent`, `TechAgent`, `ProjectInitializerAgent`, `TDDAgent` con prompts de TDD-first |

### Orchestrator LangGraph (src/synto/workflows/)

| Archivo | Cambio |
|---------|--------|
| `orchestrator.py` | Agregar rama `new_project_flow` con los 5 nodos de Fase 1. Modificar flujo existente para TDD-first. |

### Config (workspace/.synto/config.yaml)

```yaml
# Generado por ProjectInitializerAgent
project:
  name: "nombre-del-proyecto"
  slug: "nombre-del-proyecto"
  initialized_at: "2026-04-30T..."

stack:
  backend: "NestJS"
  frontend: "React"
  database: "PostgreSQL"
  auth: "JWT"
  deploy: "Docker"
  extras: ["Redis"]

features: []
```

---

## Artefactos por fase

### Fase 1 (Nuevo proyecto)

```
workspace/.synto/
├── config.yaml          ← stack tecnológico confirmado
├── state.json            ← estado del proyecto
proyecto/
├── src/                  ← según stack
├── tests/
├── package.json / pyproject.toml / go.mod
└── README.md
01-discovery/
├── context.md            ← entrevista general
├── non-functional.md     ← requisitos no funcionales altos
└── stack.md              ← stack elegido + justificación
```

### Fase 2 (Desarrollo)

```
01-discovery/
├── feature-xyz.md        ← contexto de la feature
02-requirements/
├── requirements.md        ← funcionales + no func
03-spec/
├── spec.md                ← comportamiento exacto
04-design/
├── architecture.md
└── data-model.md
05-tasks/
├── tasks.md               ← tareas atómicas
06-implementation/
├── backend/
└── frontend/
07-tests/
├── test-results.md
08-review/
├── code-review.md
└── security-review.md
09-qa/
└── qa-report.md
```

---

## Orden de implementación recomendado

```
Paso 1: Modificar workflow_agents.py
        → TDDAgent con TDD-first (escribe tests, no los ejecuta)
        → BackendAgent/FrontendAgent con retry loop

Paso 2: Crear prompts de Fase 1
        → specialist-project-init.md
        → specialist-interview.md  
        → specialist-tech-advisor.md
        → specialist-project-initializer.md

Paso 3: Modificar orchestrator.py (LangGraph)
        → Agregar rama new_project_flow
        → Modificar flujo existente para TDD-first

Paso 4: ProjectInitializerAgent
        → Ejecutor que lee config.yaml y crea proyecto

Paso 5: Detección automática
        → Leer workspace/.synto/config.yaml al inicio
        → Decidir Flujo A o Flujo B
```

---

## Skills que necesitan actualizarse

| Skill | Cambio |
|-------|--------|
| `sdd-apply` | TDD-first: TDDAgent corre antes que implementer |
| `sdd-tasks` | Generar tareas que alimenten TDDAgent |
| Skill de stack (NestJS, React, etc.) | Agregar templates de inicialización |

---

## Notas

- El flujo TDD-correcto ya está implícito en `orchestrator-code.md` (step 5: specialist-tester antes de builder). Lo que falta es el **retry loop** y la **separación clara** de que TDDAgent escribe los tests que luego son usados como criterio.
- El flujo de proyecto nuevo es绿色的 territory — no existe aún y es lo que más valor agrega porque evita el "blank page problem".
