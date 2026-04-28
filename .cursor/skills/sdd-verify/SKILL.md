---
skill_name: sdd-verify
description: Ejecuta la fase de Verification/Testing de un proyecto SDD
version: 1.0.0
triggers: ["sdd", "verify", "test", "testing", "probar"]
parameters:
  - name: implementation_path
    type: string
    required: true
    description: Ruta al código implementado
  - name: prd_path
    type: string
    required: true
    description: Ruta al PRD
---

# Skill: sdd-verify

## Objetivo
Verificar que el producto implementado cumple con el PRD mediante tests automatizados y validación manual.

## Cuándo usar
Después de la implementación.

## Entradas
- `06-implementation/` (código)
- `02-prd/prd.md`
- `03-spec/specification.md`

## Salidas
- `07-tests/test-plan.md`
- `07-tests/unit-tests/`
- `07-tests/integration-tests/`
- `07-tests/test-results.md`
- `07-tests/validation-report.md`

## Pasos

1. **Escribir tests (TDD)**
   - Unit tests para cada criterio de aceptación
   - Integration tests para flujos end-to-end

2. **Ejecutar tests**
   - Registrar resultados
   - Medir cobertura

3. **Validar contra PRD**
   - Verificar cada criterio de aceptación
   - Documentar gaps

4. **Reportar**
   - ¿Pasa o no pasa?
   - ¿Qué falta?

## Reglas
- Tests escritos ANTES o DURANTE implementation.
- Cobertura ≥ 80% en lógica de negocio.
- Ningún criterio de aceptación sin test asociado.
- Si falla, se bloquea el deploy.

## Ejemplo de uso
```
@skill sdd-verify implementation_path="06-implementation/" prd_path="02-prd/prd.md"
```
