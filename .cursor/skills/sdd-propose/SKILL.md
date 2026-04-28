---
skill_name: sdd-propose
description: Ejecuta la fase de Proposal/PRD de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "propose", "prd", "requerimientos"]
parameters:
  - name: discovery_path
    type: string
    required: true
    description: Ruta al discovery document
---

# Skill: sdd-propose

## Objetivo
Crear el Product Requirements Document (PRD) basado en el Discovery Document.

## Cuándo usar
Después de completar la fase de Discovery.

## Entradas
- `01-discovery/discovery-document.md`
- Input del usuario sobre prioridades

## Salidas
- `02-prd/prd.md`

## Pasos

1. **Definir objetivo claro**
   - Una oración que describa el producto

2. **Listar funcionalidades**
   - Must-have (MVP)
   - Nice-to-have (v2)
   - Out-of-scope explícito

3. **Definir criterios de aceptación**
   - Formato Gherkin: Dado/Cuando/Entonces
   - Un criterio por funcionalidad must-have

4. **Definir restricciones**
   - Técnicas, de negocio, legales

5. **Definir métricas de éxito**
   - ¿Cómo sabemos si funciona?

## Reglas
- NINGÚN código se escribe antes de tener PRD aprobado.
- Todo criterio de aceptación debe ser testeable.
- El PRD debe ser revisado por QA Gatekeeper.

## Ejemplo de uso
```
@skill sdd-propose discovery_path="01-discovery/discovery-document.md"
```
