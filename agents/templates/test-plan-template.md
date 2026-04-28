# Test Plan (TDD)

## Información general

- **Proyecto**: {{PROJECT_NAME}}
- **Fecha**: {{DATE}}
- **Basado en PRD**: [link al PRD]
- **Basado en Spec**: [link al Spec]

---

## 1. Estrategia de testing

- **Enfoque**: TDD (Test Driven Development)
- **Framework**: pytest / jest / unittest / vitest
- **Cobertura objetivo**: ≥ 80% lógica de negocio

### Pirámide de testing

```
       /\
      /  \   E2E (pocos)
     /____\
    /      \  Integration (algunos)
   /________\
  /          \ Unit (muchos)
 /____________\
```

---

## 2. Casos de prueba por criterio de aceptación

### CA-001: [Nombre del criterio]

#### Test: UT-001 — [Nombre del test unitario]
- **Módulo**: ...
- **Función**: ...
- **Setup (mocks)**:
  - mock X → valor Y
- **Input**: ...
- **Assertion esperado**:
  - assert result == expected
- **Estado**: ⬜ Por escribir / ✅ Escrito / ⚠️ Fallando / ✅ Pasando

#### Test: IT-001 — [Nombre del test de integración]
- **Descripción**: ...
- **Setup**: ...
- **Input**: ...
- **Assertion esperado**: ...
- **Estado**: ⬜ / ✅ / ⚠️ / ✅

---

## 3. Tests unitarios

| ID | Módulo | Función | Input | Expected | Estado |
|----|--------|---------|-------|----------|--------|
| UT-001 | ... | ... | ... | ... | ⬜ |
| UT-002 | ... | ... | ... | ... | ⬜ |

---

## 4. Tests de integración

| ID | Componentes | Escenario | Estado |
|----|-------------|-----------|--------|
| IT-001 | A + B | Flujo feliz | ⬜ |
| IT-002 | A + B | Error de red | ⬜ |

---

## 5. Mocks y fixtures

### Fixtures
- `fixture_name`: descripción y datos

### Mocks
- `mock_name`: qué simula y por qué

---

## 6. Edge cases identificados

- [ ] Input vacío / null
- [ ] Input muy grande
- [ ] Caracteres especiales
- [ ] Race conditions
- [ ] Timeout

---

## 7. Resultados de ejecución

### Última ejecución: [fecha]

| Tipo | Total | Pasados | Fallidos | Skipped |
|------|-------|---------|----------|---------|
| Unit | 0 | 0 | 0 | 0 |
| Integration | 0 | 0 | 0 | 0 |

### Cobertura

| Módulo | Cobertura % |
|--------|-------------|
| ... | 0% |

---

## 8. Regresiones

- [ ] No hay regresiones conocidas

---

## 9. Checklist TDD

- [ ] Tests escritos ANTES o DURANTE la implementación
- [ ] Todos los criterios de aceptación tienen al menos un test
- [ ] Todos los tests pasan
- [ ] Cobertura ≥ 80%
- [ ] No hay tests skippeados sin justificación
