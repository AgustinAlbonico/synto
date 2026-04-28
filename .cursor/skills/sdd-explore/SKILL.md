---
skill_name: sdd-explore
description: Ejecuta la fase de Discovery/Exploration de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "explore", "discovery", "investigar"]
parameters:
  - name: topic
    type: string
    required: true
    description: Tema o proyecto a explorar
---

# Skill: sdd-explore

## Objetivo
Realizar la fase de Discovery de un proyecto SDD, entendiendo el problema, la audiencia, las restricciones y las alternativas.

## Cuándo usar
Al inicio de cualquier proyecto, antes de escribir un PRD.

## Entradas
- Idea o solicitud del usuario
- Contexto de negocio (si existe)

## Salidas
- `01-discovery/discovery-document.md`
- `01-discovery/user-personas.md`
- `01-discovery/tech-constraints.md`

## Pasos

1. **Identificar el problema**
   - ¿Qué dolor está resolviendo?
   - ¿Por qué importa?
   - ¿Quién lo sufre?

2. **Definir audiencia**
   - Crear 1-2 user personas
   - Identificar goals y frustrations

3. **Investigar alternativas**
   - Listar 3 alternativas existentes
   - Pros y cons de cada una

4. **Documentar restricciones**
   - Técnicas, de negocio, legales

5. **Definir alcance tentativo**
   - In-scope vs out-of-scope

## Reglas
- No asumir nada que el usuario no confirmó.
- Si falta información, hacer preguntas antes de continuar.
- Documentar supuestos claramente.

## Ejemplo de uso
```
@skill sdd-explore topic="Quiero una landing page para mi servicio de consultoría"
```
