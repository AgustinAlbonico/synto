---
skill_name: sdd-design
description: Ejecuta la fase de Design de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "design", "diseno", "arquitectura"]
parameters:
  - name: spec_path
    type: string
    required: true
    description: Ruta al specification
---

# Skill: sdd-design

## Objetivo
Crear el diseño detallado: arquitectura, data model, APIs y decisiones arquitectónicas.

## Cuándo usar
Después de completar el spec.

## Entradas
- `03-spec/specification.md`
- `02-prd/prd.md`

## Salidas
- `04-design/architecture.md`
- `04-design/data-model.md`
- `04-design/api-spec.md` (si aplica)
- `04-design/adr/` (Architecture Decision Records)

## Pasos

1. **Diseñar componentes**
   - Diagrama de componentes
   - Responsabilidades claras

2. **Definir data model**
   - Schema detallado
   - Índices y constraints

3. **Especificar APIs**
   - Endpoints, request/response
   - Errores posibles

4. **Documentar decisiones (ADRs)**
   - Por qué se eligió X sobre Y

## Reglas
- Cada decisión arquitectónica debe tener un ADR.
- Los diagramas deben ser claros (ASCII o Mermaid).
- El diseño debe ser revisable por un arquitecto humano.

## Ejemplo de uso
```
@skill sdd-design spec_path="03-spec/specification.md"
```
