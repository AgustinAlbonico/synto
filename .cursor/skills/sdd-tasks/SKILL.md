---
skill_name: sdd-tasks
description: Ejecuta la fase de Task Planning y Execution de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "tasks", "plan", "ejecutar"]
parameters:
  - name: design_path
    type: string
    required: true
    description: Ruta al directorio de design
---

# Skill: sdd-tasks

## Objetivo
Crear un plan de ejecución detallado con orden de implementación y asignaciones.

## Cuándo usar
Después de completar el diseño.

## Entradas
- `04-design/architecture.md`
- `03-spec/task-breakdown.md`

## Salidas
- `05-tasks/execution-plan.md`
- `05-tasks/task-assignments.md`

## Pasos

1. **Ordenar tasks por dependencias**
   - Topological sort del DAG

2. **Asignar prioridades**
   - Bloqueantes primero
   - Riesgosos después

3. **Crear milestones**
   - Puntos de revisión

4. **Definir Definition of Done por task**
   - ¿Qué significa que está listo?

## Reglas
- No empezar implementation sin execution plan.
- Todo task debe tener un único owner.
- Los milestones deben ser demostrables.

## Ejemplo de uso
```
@skill sdd-tasks design_path="04-design/"
```
