# Arquitectura del Sistema Hermes Orchestrator

## Visión general

El sistema se organiza en tres capas principales:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA 1: USUARIO                          │
│  (Vos, el humano que pide cosas)                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              CAPA 2: ORQUESTADORES (Orchestrators)          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   Main   │ │   Code   │ │ Research │ │ Content  │ ...   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  Objetivo: recibir la solicitud, entender el dominio,       │
│  decidir qué especialistas activar y consolidar resultados  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           CAPA 3: ESPECIALISTAS (Specialists)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Planner │ │ Explorer│ │Implement│ │ Reviewer│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  Tester │ │Architect│ │ Builder │ │Validator│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Sourcer │ │ Analyst │ │Synthe-  │ │Strategist│          │
│  └─────────┘ └─────────┘ │  sizer  │ └─────────┘           │
│                          └─────────┘                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  Writer │ │  Editor │ │   SEO   │ │   ...   │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                             │
│  CROSS-CUTTING:                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │Security │ │   Doc   │ │QA Gate  │ │Dependency│          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐                                                │
│  │ Context │                                                │
│  │ Manager │                                                │
│  └─────────┘                                                │
└─────────────────────────────────────────────────────────────┘
```

## Flujo de mensajes

```
Usuario → Orchestrator Main → Orchestrator Domain → Specialist → Resultado
                                    ↓                    ↓
                              Working Memory        Protocolo JSON
```

## Working Memory

La working memory vive en `workspace/.hermes-state/` y es el espacio compartido donde los agentes leen y escriben:

- Estado del proyecto
- Artefactos intermedios
- Logs de ejecución

## Protocolo de comunicación

Todos los agentes se comunican mediante mensajes JSON estandarizados definidos en `agents/protocols/message-protocol.md`.

## Fases SDD

```
Discovery ──→ Planning ──→ Implementation ──→ Testing ──→ Deploy
   │              │              │                │            │
   ▼              ▼              ▼                ▼            ▼
explore      propose         apply            verify       deploy
   │              │              │                │            │
   └──────────────┴──────────────┴────────────────┴────────────┘
                         PRD-first + TDD
```

## Extensibilidad

Para agregar un nuevo dominio:
1. Crear `orchestrator-<dominio>.md`
2. Definir qué specialists usa
3. Agregar su fase en `scripts/run-sdd.sh`
