# Prompt Improver — Planificación

## Resumen

El **Prompt Improver** es una herramienta integrada en el Orchestrator de AgentDock que mejora prompts antes de ejecutarlos. A diferencia de Clavix (que guarda a archivo), esta herramienta muestra el resultado editable y lo usa directamente como input del Supervisor.

**Estado:** Planificación — no implementado  
**位置:** Tool del Orchestrator  
**trigger:** Toggle en UI (on/off) o comando específico

---

## 1. Concepto

### Diferencia con Clavix

| Aspecto | Clavix Improve | Prompt Improver (aquí) |
|--------|----------------|------------------------|
| Output | Guarda a `.clavix/outputs/prompts/` | Muestra editable en UI |
| Flow | Improve → Save → Implement (manual) | Input → Improve → Edit → Execute (auto) |
| Persistencia | Sí (markdown) | No (en memoria solo) |
| Integración | Slash command externa | Dentro del Orchestrator |

### Flujo Propuesto

```
Usuario dicta prompt raw
        ↓
[Prompt Improver OFF] → → → Ejecutar directamente en Supervisor
        ↓ ON
Mostrar prompt raw + evaluación de calidad (6 dimensiones)
        ↓
Generar prompt mejorado (editable)
        ↓
Usuario aprueba (o_edita)
        ↓
Usar prompt mejorado como input del Supervisor
```

---

## 2. Inspiración: Clavix Improve

El skill `clavix-improve` de Clavix usa un sistema de 6 dimensiones para evaluar y mejorar prompts:

### 6 Dimensiones de Calidad

| Dimensión | Qué Mide | Ejemplo |
|----------|----------|---------|
| **Clarity** | ¿El objetivo es claro y unambiguous? | "Crear login" → "Crear endpoint POST /auth/login con JWT" |
| **Efficiency** | ¿Es conciso sin perder info crítica? | Eliminar redundancias, mergedirecciones |
| **Structure** | ¿Está organizado lógicamente? | Separar contexto, requerimients, constraints |
| **Completeness** | ¿Están todos los detalles necesarios? | Versiones, paths, DB, auth, etc. |
| **Actionability** | ¿Puede la IA actuar inmediatamente? | Criterios de éxito claros |
| **Specificity** | ¿Qué tan concreto y preciso? | Números de versión, identificadores |

### Puntuación y Profundidad

| Quality Score | Profundidad | Descripción |
|---------------|-------------|-------------|
| ≥ 75% | **Comprehensive** | Prompt ya bueno → añadir polish, alternativas, edge cases |
| 60-74% | **User choice** | Borderline → preguntar qué quiere el usuario |
| < 60% | **Standard** | Necesita fixes básicos |

### Output por Profundidad

**Standard:**
- Intent Analysis
- Quality Assessment (6 dimensiones)
- Optimized Prompt
- Improvements Applied (etiquetados por dimensión)

**Comprehensive (includes standard +):**
- Alternative Approaches (2-3 formas diferentes)
- Validation Checklist
- Edge Cases to Consider
- Risk Assessment

---

## 3. UI / UX

### Toggle en InputBar

```
┌──────────────────────────────────────────────────────────────┐
│  💡 [Improver ON]  │  [ Input prompt aquí...               ]  │
└──────────────────────────────────────────────────────────────┘
```

### Modal de Mejora (cuando está activo y usuario envía)

```
┌─────────────────────────────────────────────────────────────┐
│  Prompt Improver                                     [ ✕ ]   │
├─────────────────────────────��───────────────────────────────┤
│                                                              │
│  📝 Prompt Original:                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ agregarle auth con JWT al sistema                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  📊 Calidad:                                               │
│  │ Dimension    │ Score │                                │
│  │ Clarity     │ 40%   │ ████░░░░░░░░░░░░               │
│  │ Efficiency  │ 70%   │ ████████░░░░░░░░░               │
│  │ Structure   │ 30%   │ ██░░░░░░░░░░░░░░░               │
│  │ Completeness│ 35%   │ ███░░░░░░░░░░░░░░               │
│  │ Actionabil. │ 50%   │ █████░░░░░░░░░░░░░               │
│  │ Specificity │ 25%   │ ██░░░░░░░░░░░░░░               │
│  │ ──────────────────                                 │
│  │ Overall      │ 42%   │ Score < 60% → Modo Standard     │
│                                                              │
│  ✨ Prompt Mejorado:                         [Refresh ♻️]    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Implementar sistema de autenticación JWT para       │    │
│  │ elSistemaOdontologico:                              │    │
│  │                                                  │    │
│  │ Stack detectado: NestJS + Prisma + PostgreSQL      │    │
│  │ - Endpoint: POST /auth/login                     │    │
│  │ - Endpoint: POST /auth/register                  │    │
│  │ - JWT con refresh tokens                          │    │
│  │ - Hash: bcrypt con salt 12                       │    │
│  │ - Validez: 15min access, 7 días refresh        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [Cancelar]              [ Usar Original ]  [ Confirmar ✓ ]   │
└─────────────────────────────────────────────────────────────┘
```

### Mejoras Etiquetadas

Debajo del prompt mejorado, mostrar las mejoras aplicadas con tags:

```
Aplicadas:
  [Clarity] ✓ Objetivo específico: sistema auth JWT
  [Completeness] ✓ Añadido: endpoints, hash, validez tokens
  [Specificity] ✓ Versiones: bcrypt salt 12, JWT 15min/7días
  [Structure] ✓ Organizado en lista de features
```

---

## 4. Modelo de Datos

```typescript
interface PromptImproverState {
  isEnabled: boolean;              // Toggle global
  originalPrompt: string;
  improvedPrompt: string;
  qualityScore: QualityScore;
  depth: 'standard' | 'comprehensive';
  intentType: IntentType;
  improvements: AppliedImprovement[];
}

interface QualityScore {
  clarity: number;        // 0-100
  efficiency: number;
  structure: number;
  completeness: number;
  actionability: number;
  specificity: number;
  overall: number;      // weighted average
}

type IntentType = 
  | 'code-generation'
  | 'planning'
  | 'refinement'
  | 'debugging'
  | 'documentation'
  | 'prd-generation'
  | 'testing'
  | 'migration'
  | 'security-review'
  | 'learning'
  | 'summarization';

interface AppliedImprovement {
  dimension: keyof QualityScore;
  description: string;
}
```

---

## 5. Lógica de Mejoramiento

### Paso a Paso

```typescript
function improvePrompt(raw: string, context?: WorkspaceContext): ImprovedPrompt {
  // 1. Detectar intent
  const intent = detectIntent(raw);
  
  // 2. Evaluar 6 dimensiones
  const quality = evaluateQuality(raw, context);
  
  // 3. Seleccionar profundidad
  const depth = quality.overall >= 75 ? 'comprehensive' 
               : quality.overall >= 60 ? 'user-choice'
               : 'standard';
  
  // 4. Aplicar patrones de mejora
  const improved = applyImprovements(raw, context, depth);
  
  // 5. Etiquetar cambios
  const improvements = tagChanges(original, improved);
  
  return { intent, quality, depth, improved, improvements };
}
```

### Patrones de Mejora por Dimensión

| Dimensión | Patrón |
|----------|--------|
| Clarity | Explicitificar objetivo vago → específico |
| Efficiency | Eliminar redundancias, usar estructura colapsable |
| Structure | Separar: Contexto → Request → Constraints → Criterios |
| Completeness | Añadir: stack, versiones, paths, DB, auth, edge cases |
| Actionability | Añadir criterios de éxito medibles |
| Specificity | concretear: "X" → "v2.0", "/ruta", "PostgreSQL 15" |

---

## 6. Integración con el Orchestrator

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ InputBar + Toggle [Improver ON/OFF]         │   │
│  └──────────────────┬────────────────────────┘   │
│                     │                             │
│         ¿Improver ON?                            │
│         ╱              ╲                         │
│       NO              YES                         │
│       ↓              ↓                          │
│  Supervisor    ┌──────────────────┐             │
│           ←──→ │ Prompt Improver │             │
│           │    └────────┬─────────┘             │
│           │             │                        │
│  ┌────────┴────────┐  │                        │
│  │ 1. Raw → Quality │  │                        │
│  │ 2. Show Modal    │  │                        │
│  │ 3. User Edit   │  │                        │
│  │ 4. Approve    │  │                        │
│  │ 5. Return    │  │                        │
│  └────────┬────────┘  │                        │
│           └───────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### Inyección de Contexto

El Prompt Improver tiene acceso al **Workspace activo** para incluir info del stack:

```
Input: "agregarle auth"
Improver detecta workspace activo: "Sistema Odontológico"
Stack: NestJS + Prisma + PostgreSQL + pnpm + Turborepo

Output mejorado incluye:
  "Implementar sistema de autenticación JWT para el Sistema Odontologico"
  "(Stack: NestJS + Prisma + PostgreSQL)"
```

---

## 7. Atajos de Teclado

| Atajo | Acción |
|-------|-------|
| `Ctrl+Shift+I` | Toggle Improver on/off |
| `Ctrl+Enter` | Enviar y mejorar (si improver ON) |
| `Esc` | Cerrar modal y usar original |
| `Tab` | Moverse entre original e mejorado |

---

## 8. Persistencia

El prompt mejorado **NO se guarda a disco** — vive solo en memoria durante la sesión.

```typescript
// Solo en Zustand store ( RAM )
interface ImproverStore {
  isEnabled: boolean;
  currentEdit: {
    original: string;
    improved: string;
    quality: QualityScore;
  } | null;
}
```

**Rationale:** El usuario quiere usarlo "al vuelo" — no necesita guardar para luego. El output mejorado se pasa directamente al Supervisor.

---

## 9. Roadmap de Implementación

### Fase 1: Lógica Core
- [ ] Función `evaluateQuality(prompt)` → 6 dimensiones
- [ ] Función `detectIntent(prompt)` → intent type
- [ ] Función `applyImprovements(prompt, depth)` → prompt mejorado
- [ ] Función `tagChanges(original, improved)` → labels

### Fase 2: UI del Improver
- [ ] Toggle en InputBar
- [ ] Modal con split view (original | mejorado)
- [ ] Editor de texto para mejorado
- [ ] Calidad visual (barras, scores)
- [ ] Tags de mejoras aplicadas

### Fase 3: Integración Orchestrator
- [ ] Hook del input →interceptar si improver ON
- [ ] Mostrar modal → esperar approve
- [ ] Pasar mejorado al Supervisor
- [ ] Integrar con Workspace activo (detectar stack)

### Fase 4: Config y UX
- [ ] Persistir preference (on/off) en localStorage
- [ ] Keyboard shortcuts
- [ ] Animaciones de transición
- [ ] Historial en memoria (último mejorado, por si necesitás comparar)

---

## 10. Decisiones de Diseño

| Decisión | Justificación |
|----------|---------------|
| No guardar a disco | Usuario quiere usarlo "al vuelo", no revisar después |
| Modal obligatorio | No debe ejecutarse sin que usuario vea qué mejoró |
| Editor editable | Permite corregir si la IA se equivocó |
| Contexto del workspace | Añade valor — stack específico no genérico |
| Tags por dimensión | Sirve para que usuario entienda qué mejoró |
| Toggle default OFF | El usuario elige cuándo usar, no siempre |

---

## 11. Archivos a Crear

```
src/
  services/
    promptImprover/
      evaluateQuality.ts     # Scoring 6 dimensiones
      detectIntent.ts       # Clasificar intent
      applyImprovements.ts  # Mejorar prompt
      tagChanges.ts        # Etiquetar cambios
  components/
    InputBar/
      ImproverToggle.tsx   # Toggle button
    PromptImprover/
      PromptImproverModal.tsx  # Modal principal
      QualityScoreCard.tsx    # Barras de score
      ImprovedPromptEditor.tsx # Textarea editable
      ImprovementTags.tsx     # Tags visuales
  stores/
    improverStore.ts      # Zustand store
  hooks/
    usePromptImprover.ts # Hook para usar en components
```

---

## 12. Notas

- El modelo de mejora puede usar el mismo modelo configurado en AgentDock (Gemini, Anthropic, etc.) — solo hace falta el prompt del skill.
- **Futuro:** opcionalmente guardar "templates" de prompts improvedos favoritos como snippets.
- **Futuro:** "improve mode" configurable (solo estándar vs ask depth).

---

## Referencia: Clavix Improve Skill

Skills relacionados consultadas:
- `clavix-improve` (loppety/Clavix)
- `clavix-improve` (majiayu000/clavix-improve @ agentskill.sh)

Diferencia clave implementada aquí:
- Clavix: Save to file → Execute separately
- Aquí: Edit in modal → Execute immediately