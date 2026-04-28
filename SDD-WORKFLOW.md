# Flujo SDD con PRD + TDD

## Visión general

El flujo SDD (Structured Design & Development) garantiza que cada proyecto pase por 5 fases obligatorias, produciendo artefactos documentados en cada una.

## Fases

### 1. Discovery (Exploración)
**Skill**: `sdd-explore`

Objetivo: entender QUÉ se quiere construir y PARA QUIÉN.

Artefactos:
- `01-discovery/discovery-document.md`
- `01-discovery/user-personas.md`
- `01-discovery/tech-constraints.md`

Entradas: idea del usuario
Salidas: documento de discovery con bullets

### 2. Planning (Planificación)
**Skills**: `sdd-propose`, `sdd-spec`, `sdd-design`

Objetivo: definir CÓMO se va a construir.

Sub-fases:
- **Propose**: definir el PRD (Product Requirements Document)
- **Spec**: descomponer en tareas atómicas con dependencias
- **Design**: definir arquitectura y diseño técnico

Artefactos:
- `02-prd/prd.md`
- `03-spec/specification.md`
- `03-spec/task-breakdown.md`
- `04-design/architecture.md`
- `04-design/data-model.md`

Entradas: discovery document
Salidas: PRD + Spec + Design

**Regla PRD-first**: NINGÚN código se escribe antes de tener el PRD aprobado.

### 3. Implementation (Implementación)
**Skills**: `sdd-tasks`, `sdd-apply`

Objetivo: escribir el código según el spec y el diseño.

Sub-fases:
- **Tasks**: plan de tareas con orden de ejecución
- **Apply**: implementación de cada tarea

Artefactos:
- `05-tasks/execution-plan.md`
- `06-implementation/` (código fuente)

Entradas: spec + design
Salidas: código implementado

### 4. Testing (Pruebas)
**Skill**: `sdd-verify`

Objetivo: verificar que todo funciona según el PRD.

Artefactos:
- `07-tests/test-plan.md`
- `07-tests/unit-tests/` (tests unitarios)
- `07-tests/integration-tests/` (tests de integración)
- `07-tests/test-results.md`

Entradas: código + PRD
Salidas: tests pasando + reporte

**Regla TDD**: Los tests se escribieron ANTES o DURANTE la implementación, nunca después.

### 5. Deploy (Despliegue)
**Skill**: `sdd-deploy`

Objetivo: poner el producto en producción.

Artefactos:
- `08-deploy/deployment-guide.md`
- `08-deploy/release-notes.md`

## Flujo completo en un comando

```bash
./scripts/run-sdd.sh nombre-del-proyecto
```

Este script ejecuta todas las fases en orden, guardando artefactos en:
```
HERMES_PROJECTS_DIR/nombre-del-proyecto/
```

## Diagrama de flujo

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │ "Quiero una landing page"
       ▼
┌──────────────────┐
│    DISCOVERY     │ ← Skill: sdd-explore
│  ¿Qué? ¿Para quién? │
└────────┬─────────┘
         │ discovery-document.md
         ▼
┌──────────────────┐
│    PLANNING      │ ← Skills: sdd-propose, sdd-spec, sdd-design
│   PRD + Spec + Design  │
└────────┬─────────┘
         │ prd.md, spec.md, design.md
         ▼
┌──────────────────┐
│  IMPLEMENTATION  │ ← Skills: sdd-tasks, sdd-apply
│    Código        │
└────────┬─────────┘
         │ código fuente
         ▼
┌──────────────────┐
│    TESTING       │ ← Skill: sdd-verify
│   Tests TDD      │
└────────┬─────────┘
         │ tests pasando
         ▼
┌──────────────────┐
│     DEPLOY       │ ← Skill: sdd-deploy
│   Producción     │
└──────────────────┘
```

## Checklist por fase

### Discovery
- [ ] Identificamos el problema que resuelve
- [ ] Definimos usuario objetivo
- [ ] Listamos restricciones técnicas
- [ ] Confirmamos alcance

### Planning
- [ ] PRD tiene objetivo claro
- [ ] PRD tiene criterios de aceptación
- [ ] Spec tiene tareas atómicas
- [ ] Spec tiene dependencias definidas
- [ ] Design tiene arquitectura
- [ ] Design tiene modelo de datos

### Implementation
- [ ] Seguimos el orden de tareas del spec
- [ ] Cada tarea tiene su commit
- [ ] El código sigue el design

### Testing
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Todos los criterios de aceptación del PRD están cubiertos
- [ ] No hay regresiones

### Deploy
- [ ] Guía de deploy escrita
- [ ] Variables de entorno documentadas
- [ ] Release notes generadas
