---
skill_name: sdd-spec
description: Ejecuta la fase de Specification de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "spec", "specification", "especificacion"]
parameters:
  - name: prd_path
    type: string
    required: true
    description: Ruta al PRD
---

# Skill: sdd-spec

## Objetivo
Convertir el PRD en una especificación técnica detallada con tasks atómicas, dependencias y stack.

## Cuándo usar
Después de aprobar el PRD.

## Entradas
- `02-prd/prd.md`
- `01-discovery/tech-constraints.md`

## Salidas
- `03-spec/specification.md`
- `03-spec/task-breakdown.md`

## Pasos

1. **Elegir stack tecnológico**
   - Justificar cada elección

2. **Diseñar arquitectura de alto nivel**
   - Componentes e interfaces

3. **Definir modelo de datos**
   - Entidades, campos, relaciones

4. **Descomponer en tasks atómicas**
   - Cada task debe ser estimable (< 1 día idealmente)
   - Definir dependencias entre tasks

5. **Definir criterios de aceptación por task**
   - Vincular con criterios del PRD

## Reglas
- Las tasks deben ser atómicas y no solaparse.
- Las dependencias deben formar un DAG (sin ciclos).
- Todo task debe tener un criterio de aceptación claro.

## Ejemplo de uso
```
@skill sdd-spec prd_path="02-prd/prd.md"
```
