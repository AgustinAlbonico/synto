# Definición de Agentes — Sistema Hermes Orquestado

> **Propuesta completa de agentes por dominio**
> Basado en: Agency Swarm + CCW workflow patterns + skills nativas de Hermes
> Idioma: Español rioplatense
> Orquestador principal: OpenCode

---

## 📋 Agentes propuestos

### CAPA 0: Orquestador Principal

| Agente | Rol | Responsabilidad | Qué NO hace |
|--------|-----|----------------|-------------|
| **HermesOrchestrator** | Tu punto de contacto único | Escucharte, hacer preguntas de clarificación, activar dominios, presentar resultados, pedir aprobaciones en gates | NUNCA toca código, NUNCA hace research directo, NUNCA deploya |

**Skills:** `plan`, `writing-plans`, `subagent-driven-development`, `obsidian`

---

### CAPA 1: Domain Orchestrators

| Agente | Rol | Responsabilidad | Qué NO hace |
|--------|-----|----------------|-------------|
| **CodeOrchestrator** | Jefe de ingeniería | Convertir PRD en spec técnica, gestionar task graph, asignar tareas a especialistas, coordinar testing y deploy técnico | NUNCA habla con el usuario, NUNCA modifica PRD sin aprobación |
| **ResearchOrchestrator** | Jefe de investigación | Investigar mercado, competencia, papers, tecnologías. Sintetizar en reportes | NUNCA implementa, NUNCA habla con el usuario |
| **ContentOrchestrator** | Jefe de contenido | Copy, landing pages, social media, diseño de interfaces | NUNCA codea, NUNCA habla con el usuario |
| **DevOpsOrchestrator** | Jefe de infra | CI/CD, deploys, monitoreo, infraestructura | NUNCA implementa features de negocio, NUNCA habla con el usuario |
| **DataOrchestrator** | Jefe de datos | Scraping, ETL, análisis, dashboards | NUNCA codea frontend, NUNCA habla con el usuario |

---

### CAPA 2: Code Specialists

| Agente | Rol | Responsabilidad | Tools/Skills |
|--------|-----|----------------|--------------|
| **Planner** | Planificador técnico | Descomponer specs en subtareas atómicas, definir dependencias, armar task graph | `writing-plans`, `codebase-inspection` |
| **CodebaseExplorer** | Explorador de código | Leer repo, entender estructura, encontrar dónde tocar, mapear dependencias | `codebase-inspection`, `github-repo-management` |
| **Architect** | Arquitecto | Diseñar componentes, definir APIs, modelar datos, decidir patrones | `architecture-diagram`, `excalidraw`, `design-md` |
| **Implementer** | Implementador | Escribir código siguiendo spec y estilo del repo. Usar OpenCode | `opencode`, `node-inspect-debugger`, `python-debugpy` |
| **Tester** | Tester TDD | Escribir tests ANTES del código. Test plan, unit, integration, E2E | `test-driven-development` |
| **Reviewer** | Revisor de código | Revisar código vs spec, calidad, bugs, estilo | `github-code-review`, `requesting-code-review` |
| **SecurityReviewer** | Revisor de seguridad | Scannear secrets, vulnerabilidades, OWASP antes de deploy | `requesting-code-review` (security scan) |

---

### CAPA 2: Research Specialists

| Agente | Rol | Responsabilidad | Tools/Skills |
|--------|-----|----------------|--------------|
| **Sourcer** | Buscador de fuentes | Buscar en web, papers, bases de datos, APIs. Encontrar fuentes confiables | `searxng-hermes-integration`, `arxiv`, `blogwatcher` |
| **Analyst** | Analista | Extraer insights de fuentes. Analizar competidores, nichos, tendencias | `jupyter-live-kernel`, `llm-wiki` |
| **Synthesizer** | Sintetizador | Juntar todo en reportes coherentes, ejecutivos, con recomendaciones | `obsidian`, `powerpoint` |

---

### CAPA 2: Content Specialists

| Agente | Rol | Responsabilidad | Tools/Skills |
|--------|-----|----------------|--------------|
| **Strategist** | Estratega de contenido | Definir ángulo, tono, keywords, estructura, buyer persona | `obsidian`, `writing-plans` |
| **Writer** | Redactor | Producir copy, landing pages, posts, emails | `claude-design`, `frontend-design` |
| **Editor** | Editor | Revisar claridad, gramática, coherencia, tono rioplatense | `clarify` (openclaw) |
| **SEO** | SEO specialist | Optimizar para búsqueda, meta tags, keywords, estructura | `obsidian` |
| **Designer** | Diseñador UI/UX | Diseñar interfaces, componentes, flujos de usuario | `frontend-design`, `excalidraw`, `popular-web-designs` |

---

### CAPA 2: DevOps Specialists

| Agente | Rol | Responsabilidad | Tools/Skills |
|--------|-----|----------------|--------------|
| **InfraArchitect** | Arquitecto de infra | Diseñar Docker, K8s, networking, escalabilidad | `architecture-diagram` |
| **Builder** | Builder de infra | Escribir Dockerfiles, GitHub Actions, scripts de deploy | `cloudflare-tunnel-local-dev`, `levantar-app` |
| **Validator** | Validador de infra | Testear infra en staging, verificar que todo funciona | `systematic-debugging` |

---

### CAPA 2: Data Specialists

| Agente | Rol | Responsabilidad | Tools/Skills |
|--------|-----|----------------|--------------|
| **Scraper** | Scraper | Extraer datos de webs, APIs, feeds respetando robots.txt | `searxng-hermes-integration` |
| **Cleaner** | Data cleaner | Limpiar, normalizar, validar datasets | `jupyter-live-kernel` |
| **Modeler** | Data modeler | Modelar datos, ML básico, análisis estadístico | `weights-and-biases`, `jupyter-live-kernel` |
| **Visualizer** | Visualizador | Dashboards, gráficos, reportes visuales | `jupyter-live-kernel` |

---

### Cross-Cutting Agents (aparecen cuando se necesitan)

| Agente | Cuándo se activa | Qué hace | Skills |
|--------|------------------|----------|--------|
| **QAGatekeeper** | Antes de entregar cualquier cosa al usuario | Verifica que el output cumpla el PRD original | `systematic-debugging` |
| **DependencyChecker** | Después de implementar | Verifica que no se rompan otras partes del sistema | `github-pr-workflow` |
| **DocumentationAgent** | Al finalizar cada fase | Genera docs: README, CHANGELOG, resumen ejecutivo | `obsidian` |
| **ContextManager** | Entre sesiones | Persiste estado, recupera contexto, resume sesiones | `obsidian` |

---

## 🎯 Priorización según tus proyectos actuales

### Fase 1: Code Domain (MVP — arrancar YA)
**Por qué:** Tenés el sistema odontológico y plasma-portfolio activos. Necesitás codear features, fixear bugs, refactorizar.

**Agentes mínimos necesarios:**
1. HermesOrchestrator (Capa 0)
2. CodeOrchestrator (Capa 1)
3. Planner, CodebaseExplorer, Implementer, Tester, Reviewer (Capa 2)

**Flujo de ejemplo:**
> "Agregame autenticación JWT al sistema odontológico"
> 
> HermesOrchestrator → CodeOrchestrator → 
> Planner (task graph) → CodebaseExplorer (entender repo) → 
> Implementer (codea con OpenCode) → Tester (tests TDD) → 
> Reviewer (revisa) → QAGatekeeper (verifica vs PRD) → 
> DevOpsOrchestrator (deploy si aplica)

---

### Fase 2: Research Domain (la que mencionaste)
**Por qué:** Querés emprender con IA aplicada a empresas. Necesitás investigar nichos, validar ideas, entender competencia.

**Agentes:**
1. ResearchOrchestrator
2. Sourcer, Analyst, Synthesizer

**Flujo de ejemplo:**
> "Investigame si hay mercado para un SaaS de gestión de turnos para odontólogos en Argentina"
>
> HermesOrchestrator → ResearchOrchestrator →
> Sourcer (busca competidores, tamaño de mercado, regulaciones) →
> Analyst (extrae insights: precios, features, gaps) →
> Synthesizer (arma reporte ejecutivo con recomendaciones)

---

### Fase 3: Content + DevOps
**Por qué:** Cuando tengás un producto, necesitás landing page, copy, deploy automático.

**Agentes:**
1. ContentOrchestrator + Strategist, Writer, Editor, SEO, Designer
2. DevOpsOrchestrator + InfraArchitect, Builder, Validator

---

### Fase 4: Data Domain
**Por qué:** Cuando el producto tenga usuarios, necesitás analytics, scraping, dashboards.

**Agentes:**
1. DataOrchestrator + Scraper, Cleaner, Modeler, Visualizer

---

## 🤔 Pregunta para vos

¿Esta lista te parece completa o querés agregar/eliminar agentes?

Algunas preguntas para ajustar:

1. **¿Solo OpenCode o también querés delegar a Claude Code/Codex en algunos casos?**
   - Por ejemplo: Implementer usa OpenCode, pero Architect podría usar Claude para diagramas complejos.

2. **¿Querés que el ResearchOrchestrator también investigue papers académicos (arxiv) o solo mercado/comercial?**

3. **¿Necesitás el ContentOrchestrator para crear landing pages de tus proyectos o eso lo hacés manual?**

4. **¿El DevOpsOrchestrator debería manejar deploy automático a producción o solo staging?**

5. **¿Falta algún rol?** Algunos que no incluí:
   - **Copywriter** (específico para ads, no solo landing)
   - **GrowthHacker** (estrategias de crecimiento, A/B testing)
   - **LegalReviewer** (revisar términos y condiciones, GDPR)
   - **UXResearcher** (entrevistas, user personas, journey maps)
   - **FinancialAnalyst** (proyecciones, unit economics, pricing)

---

## ✅ Mi recomendación de arranque

Empezar con estos **7 agentes** para la Fase 1 (Code Domain):

| # | Agente | Prioridad |
|---|--------|-----------|
| 1 | HermesOrchestrator | 🔴 Crítico |
| 2 | CodeOrchestrator | 🔴 Crítico |
| 3 | Planner | 🔴 Crítico |
| 4 | CodebaseExplorer | 🔴 Crítico |
| 5 | Implementer | 🔴 Crítico |
| 6 | Tester | 🔴 Crítico |
| 7 | Reviewer | 🟡 Importante |

Y después agregar:
- SecurityReviewer (cuando hagamos deploys)
- QAGatekeeper (cuando el flujo esté maduro)
- ResearchOrchestrator + equipo (cuando quieras investigar nichos)

¿Te parece bien? ¿Ajustamos algo?
