# Technical Specification

## Información general

- **Proyecto**: {{PROJECT_NAME}}
- **Fecha**: {{DATE}}
- **Versión**: 1.0.0
- **Basado en PRD**: [link al PRD]

---

## 1. Resumen ejecutivo

Breve descripción de qué vamos a construir y cómo.

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión | Justificación |
|------|-----------|---------|---------------|
| Frontend | ... | ... | ... |
| Backend | ... | ... | ... |
| Base de datos | ... | ... | ... |
| Hosting | ... | ... | ... |

---

## 3. Arquitectura de alto nivel

```
[Diagrama ASCII de componentes]
```

### Componentes

- **Componente A**: responsabilidad
- **Componente B**: responsabilidad

### Interfaces

- API entre A y B: formato, protocolo

---

## 4. Modelo de datos

### Entidades

- **Entidad 1**
  - campo: tipo (constraints)
  - campo: tipo (constraints)

- **Entidad 2**
  - campo: tipo (constraints)

### Relaciones

- Entidad 1 --1:N--> Entidad 2

---

## 5. API Specification (si aplica)

### Endpoint: `GET /api/resource`

- **Descripción**: ...
- **Request**: query params, headers
- **Response 200**: schema JSON
- **Response 4xx**: errores posibles

---

## 6. Task Breakdown

### Task T001: [Nombre]
- **Descripción**: ...
- **Dependencias**: ninguna / T00X
- **Criterio de aceptación**: ...
- **Estimación**: XS / S / M / L / XL

### Task T002: [Nombre]
- **Descripción**: ...
- **Dependencias**: T001
- **Criterio de aceptación**: ...
- **Estimación**: XS / S / M / L / XL

---

## 7. Consideraciones de seguridad

- Autenticación:
- Autorización:
- Validación de inputs:
- Manejo de secrets:

---

## 8. Consideraciones de performance

- Targets:
- Estrategias de caching:
- Optimizaciones planificadas:

---

## 9. Plan de testing

- Tests unitarios: framework, cobertura objetivo
- Tests de integración: alcance
- Tests e2e: si aplica

---

## 10. Plan de deploy

- Ambientes: dev, staging, prod
- Estrategia: blue-green, rolling, canary
- Rollback plan:
