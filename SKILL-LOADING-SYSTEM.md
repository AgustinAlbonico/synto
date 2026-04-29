# Skill Loading System — Registro, carga dinámica y asignación por agente

> Estado: MVP implementado (`SkillRegistry` + `SkillLoader.resolve` + inyección lazy + auditoría JSONL)
> Fecha: 2026-04-29
> Objetivo: permitir que cada agente cargue solo las skills que necesita, y que el usuario pueda agregar nuevas skills encontradas en internet sin rehacer el sistema.

---

## 1. Problema que resuelve

Hermes tiene muchas skills. Si todos los agentes cargan todo:

- sube el costo de tokens;
- baja la precisión;
- aumentan conflictos de instrucciones;
- aparecen tools irrelevantes;
- se vuelve difícil auditar qué agente podía hacer qué.

La solución es un sistema de carga por capas:

```text
Skill discovery → metadata registry → agent allowlist → trigger matching → lazy full load
```

---

## 2. Principios

1. Ningún agente carga todas las skills.
2. Cada agente tiene base skills mínimas.
3. Skills nuevas pueden agregarse sin cambiar código.
4. Una skill externa no se activa hasta pasar validación.
5. El contenido completo de una skill se carga tarde/lazy.
6. La metadata puede estar disponible siempre.
7. El usuario puede asignar skills manualmente a agentes.
8. El sistema puede sugerir asignaciones por tags/triggers.
9. El agente no puede cargar una skill fuera de su allowlist salvo aprobación explícita.
10. Cada carga queda registrada para auditoría.

---

## 3. Directorios

```text
~/.hermes/skills/
  Skills instaladas y confiables de Hermes.

~/.hermes/custom-skills/
  Skills agregadas por el usuario.

~/.hermes/skills-inbox/
  Skills recién descargadas, todavía no confiables.

/home/agust/synto/config/
  agent-skill-map.yaml       # overrides/assignments del proyecto
  skill-registry-cache.json  # cache generado, no editar a mano

/home/agust/synto/workspace/.hermes-state/
  skill-load-events.jsonl    # auditoría de cargas
```

---

## 4. Estados de confianza de una skill

| Estado | Puede cargarse | Descripción |
|---|---:|---|
| `builtin` | Sí | Viene de `~/.hermes/skills`, ya conocida. |
| `local_trusted` | Sí | Skill custom aprobada por el usuario. |
| `community_reviewed` | Sí, con restricciones | Skill externa revisada y aprobada. |
| `quarantined` | No | Skill en inbox, sin validar. |
| `blocked` | No | Skill rechazada por riesgo o incompatibilidad. |

---

## 5. Formato extendido de SKILL.md

El formato base actual se mantiene. Se agregan campos opcionales.

```yaml
---
name: example-skill
description: "Qué hace la skill"
version: 1.0.0
author: "..."
license: MIT
metadata:
  hermes:
    tags: [frontend, react, ui]
    related_skills: [frontend-design]

# Extensiones para el swarm
default_agents:
  - FrontendImplementer
  - SystemDesigner

allowed_agents:
  - FrontendImplementer
  - SystemDesigner
  - Reviewer

denied_agents:
  - BackendImplementer
  - Builder

triggers:
  - type: prompt_regex
    pattern: "(?i)(react|component|ui|frontend)"
    confidence: 0.7
  - type: workflow_phase
    phase: implementation
    confidence: 0.5
  - type: file_glob
    pattern: "**/*.tsx"
    confidence: 0.6

capabilities:
  - frontend.component_design
  - frontend.accessibility_review

requires_tools:
  - filesystem_read
  - browser

loading:
  mode: lazy
  max_tokens: 6000
  priority: normal

security:
  trust: community_reviewed
  network_access: false
  shell_access: false
---

# Skill content...
```

Los campos nuevos no rompen compatibilidad: si no existen, el scanner infiere defaults.

---

## 6. Skill Scanner

Responsabilidad:

- recorrer directorios configurados;
- detectar `SKILL.md`;
- parsear frontmatter;
- extraer tags, descripción, triggers, restricciones;
- validar estructura;
- calcular fingerprint/hash;
- generar cache.

Pseudo-flujo:

```python
def scan_skills(paths):
    registry = {}
    for path in paths:
        for skill_md in find_skill_md(path):
            meta = parse_frontmatter(skill_md)
            body_summary = summarize_body_headings(skill_md)
            registry[meta.name] = SkillMetadata(
                name=meta.name,
                path=skill_md,
                tags=meta.tags,
                triggers=meta.triggers,
                allowed_agents=meta.allowed_agents,
                default_agents=meta.default_agents,
                trust=meta.security.trust,
                fingerprint=sha256(skill_md),
                body_summary=body_summary,
            )
    return registry
```

---

## 7. Skill Registry

El registry tiene dos capas:

### 7.1 Metadata Registry

Siempre liviano. Se puede cargar al boot.

```json
{
  "frontend-design": {
    "name": "frontend-design",
    "description": "Create distinctive frontend interfaces",
    "tags": ["frontend", "ui", "design"],
    "path": "/home/agust/.hermes/skills/openclaw-imports/frontend-design/SKILL.md",
    "trust": "builtin",
    "fingerprint": "...",
    "allowed_agents": ["SystemDesigner", "FrontendImplementer"],
    "triggers": []
  }
}
```

### 7.2 Full Skill Content

Se carga on-demand con `skill_view` o lector equivalente.

---

## 8. Agent Skill Map

Archivo de overrides del proyecto:

```yaml
assignments:
  FrontendImplementer:
    add:
      - skill: "new-react-patterns"
        priority: required
        reason: "Usar patrones modernos de React encontrados por el usuario"
    remove:
      - "claude-design"

  SystemDesigner:
    add:
      - skill: "brand-design-system"
        priority: required
        reason: "Design system específico del proyecto"

skill_overrides:
  new-react-patterns:
    trust: local_trusted
    allowed_agents:
      - FrontendImplementer
      - Reviewer
    triggers:
      - type: file_glob
        pattern: "**/*.tsx"
        confidence: 0.8
```

Este archivo permite que el usuario agregue skills nuevas sin tocar código.

---

## 9. Dynamic Loader

### 9.1 Inputs

```text
agent_id
workflow_phase
task_description
project_context
files_in_scope
manual_assignments
skill_registry
agent_policy
```

### 9.2 Cálculo de candidatas

```python
candidate_skills = []

candidate_skills += agent.base_skills.required
candidate_skills += manual_assignments.required_for(agent)
candidate_skills += phase_required_skills(phase)
candidate_skills += trigger_matches(task_description, files_in_scope, project_context)
candidate_skills += agent.base_skills.optional if budget_allows

candidate_skills = filter_by_agent_allowlist(candidate_skills, agent)
candidate_skills = remove_denied_skills(candidate_skills, agent)
candidate_skills = remove_untrusted(candidate_skills)
candidate_skills = rank(candidate_skills)
candidate_skills = apply_budget(candidate_skills)
```

### 9.3 Ranking

Prioridad:

1. base required del agente;
2. manual required por usuario;
3. workflow phase required;
4. trigger exacto por archivo/fase;
5. trigger semántico por prompt;
6. optional base;
7. related skills.

### 9.4 Budget

Default:

```yaml
max_full_skills_per_agent_run: 5
max_skill_tokens_per_agent_run: 20000
max_single_skill_tokens: 8000
```

Si excede:

- cargar metadata;
- cargar resumen;
- pedir al agente elegir cuál necesita;
- cargar full content solo de esa.

---

## 10. Modos de carga

| Modo | Qué carga | Cuándo |
|---|---|---|
| `metadata` | nombre, descripción, tags, triggers | siempre disponible |
| `summary` | headings y resumen corto | cuando hay match medio |
| `full` | SKILL.md completo + linked files necesarios | cuando se usa realmente |
| `tool_only` | solo tool wrappers, sin todo el texto | tools mecánicas estables |
| `blocked` | nada | skill no confiable/no permitida |

---

## 11. Manual assignment — flujo usuario

Cuando el usuario dice:

> Agregá esta skill de React al FrontendImplementer.

El sistema hace:

1. Descargar/copiar skill a `~/.hermes/skills-inbox/skill-name/`.
2. Validar que exista `SKILL.md`.
3. Parsear frontmatter.
4. Escanear comandos peligrosos, instrucciones conflictivas, secretos embebidos.
5. Marcar como `quarantined` si falta algo.
6. Si pasa revisión, mover a `~/.hermes/custom-skills/skill-name/`.
7. Marcar trust `local_trusted`.
8. Actualizar `agent-skill-map.yaml`.
9. Reescanear registry.
10. Registrar evento.

---

## 12. Validación de skills externas

Checks mínimos:

- `name` existe y coincide con carpeta.
- `description` clara.
- No contiene secrets.
- No contiene instrucciones tipo "ignore previous instructions".
- No exige acceso shell/network sin declararlo.
- No intenta cambiar rol del agente.
- No contiene comandos destructivos sin warning.
- Licencia/autor si aplica.
- Tamaño razonable.

Riesgos a bloquear:

```text
rm -rf /
curl ... | sh
subir secrets
exfiltrar archivos
ignorar políticas del sistema
pedir credenciales al usuario sin razón
```

---

## 13. Agent allowlist

Cada agente en `AGENT-REGISTRY.yaml` define:

```yaml
dynamic_skill_policy:
  allowed_tags:
    - frontend
    - react
  denied_tags:
    - deploy
    - database
```

Regla:

- Si una skill matchea denied tag → no se carga.
- Si no matchea ningún allowed tag → requiere aprobación explícita.
- Si es `required` por asignación manual, igual pasa por trust/security.

---

## 14. Registro de eventos

Cada carga se audita en JSONL:

```json
{
  "timestamp": "2026-04-28T03:00:00Z",
  "run_id": "run_123",
  "agent": "FrontendImplementer",
  "skill": "frontend-design",
  "mode": "full",
  "reason": "base_required",
  "trust": "builtin",
  "fingerprint": "sha256:..."
}
```

Esto después se muestra en la UI web.

---

## 15. Skill conflict handling

Conflictos posibles:

- Dos skills dan instrucciones opuestas.
- Una skill contradice el rol del agente.
- Una skill pide tools que el agente no tiene.
- Una skill excede presupuesto de tokens.

Resolución:

1. Instrucciones del sistema > rol del agente > workflow phase > skill.
2. Base required > manual required > trigger dynamic > optional.
3. Si contradice restricciones del agente, se bloquea.
4. Si pide tools no permitidas, se carga como documentación, no como tool.
5. Si el conflicto es ambiguo, CodeOrchestrator decide o escala.

---

## 16. Integración con LangGraph

Cada nodo recibe un contexto preparado:

```python
class AgentRuntimeContext(BaseModel):
    agent_id: str
    role_prompt: str
    loaded_skill_metadata: list[SkillMetadata]
    loaded_skill_docs: list[SkillDoc]
    mcp_tools: list[Tool]
    state_slice: dict
    write_slot: str
```

Antes de ejecutar nodo:

```python
def prepare_agent_context(agent_id, state):
    agent = agent_registry.get(agent_id)
    skills = skill_loader.resolve(agent, state)
    tools = mcp_resolver.resolve(agent.mcp_capabilities)
    state_slice = state_reader.slice_for(agent)
    return AgentRuntimeContext(...)
```

---

## 17. Integración futura con UI web

La UI web tendrá una pantalla de Skills:

- listar skills disponibles;
- importar skill desde carpeta/URL;
- ver trust status;
- asignar a agentes;
- editar triggers;
- ver historial de cargas;
- simular qué skills se cargarían para una tarea;
- bloquear/desbloquear skills.

---

## 18. MVP técnico

Implementado:

1. `SkillRegistry` como scanner/registry de metadata.
2. `AgentRegistry` leyendo `AGENT-REGISTRY.yaml`.
3. `SkillLoader.resolve(agent, state)` para resolver base skills, overrides, triggers y políticas por agente.
4. `state/skill-load-events.jsonl` mediante `StateStore.append_skill_events()`.
5. `config/agent-skill-map.yaml` como archivo de overrides/manual assignments.
6. Inyección lazy en runtime: cada `_invoke_agent()` agrega `--- Loaded Skills ---` al system prompt del agente.
7. API web: `GET /api/runs/{run_id}/skill-events`.

Pendiente para fases posteriores:

8. importación de skills externas desde URL/carpeta;
9. validación avanzada y revisión asistida de skills en inbox;
10. UI completa para asignar/bloquear/desbloquear skills;
11. auto-sugerencias por embedding/semantic search.
