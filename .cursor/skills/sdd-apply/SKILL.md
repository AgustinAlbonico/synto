---
skill_name: sdd-apply
description: Ejecuta la fase de Implementation/Apply de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "apply", "implementar", "codear"]
parameters:
  - name: execution_plan_path
    type: string
    required: true
    description: Ruta al execution plan
---

# Skill: sdd-apply

## Objetivo
Implementar el código siguiendo el execution plan, el design y el spec.

## Cuándo usar
Después de completar el plan de tareas.

## Entradas
- `05-tasks/execution-plan.md`
- `04-design/architecture.md`
- `03-spec/specification.md`

## Salidas
- `06-implementation/` (código fuente)

## Pasos

1. **Setup del proyecto**
   - Scaffolding, dependencias, configuración

2. **Implementar tasks en orden**
   - Seguir el execution plan
   - Commits atómicos

3. **Aplicar TDD**
   - Tests antes o durante, nunca después

4. **Code review entre tasks**
   - Revisar calidad antes de seguir

## Reglas
- SIEMPRE seguir el diseño aprobado.
- SIEMPRE escribir tests para lógica de negocio.
- NUNCA hardcodear secrets.
- NUNCA dejar código comentado o debug.

## Ejemplo de uso
```
@skill sdd-apply execution_plan_path="05-tasks/execution-plan.md"
```
