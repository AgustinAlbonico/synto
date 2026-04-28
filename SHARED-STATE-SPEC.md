# SharedState / Blackboard Spec

> Estado: especificación para implementación
> Fecha: 2026-04-28
> Objetivo: definir cómo los agentes comparten información, trabajan en paralelo y evitan pisarse.

---

## 1. Concepto

El SharedState es el blackboard central de un run de LangGraph.

No es memoria libre. Es un contrato tipado donde cada agente:

- lee solo lo que necesita;
- escribe solo en su slot;
- no pisa artefactos canónicos;
- deja eventos auditables;
- permite checkpointing y recuperación.

Importante: SharedState no es memoria persistente global. Para recordar información entre sesiones se usa `PersistentMemory / MemoryStore`, definido en `PERSISTENT-MEMORY-SPEC.md`.

---

## 2. Principios

1. El estado debe ser serializable.
2. Cada agente escribe en un slot propio.
3. Los artefactos canónicos son inmutables por versión.
4. Solo nodos consolidadores escriben artefactos canónicos.
5. Los writes paralelos deben ser mergeables.
6. Todo cambio importante produce evento.
7. Todo gate deja estado explícito.
8. Los approvals humanos son artefactos de estado, no texto perdido en chat.
9. El estado debe poder mostrarse en una UI web.
10. El estado debe poder reconstruir qué pasó, quién decidió qué y cuándo.

---

## 3. Estructura general

```python
class SharedState(TypedDict):
    meta: RunMeta
    user: UserContext
    project: ProjectContext
    workflow: WorkflowState
    approvals: dict[str, Approval]
    gates: dict[str, GateStatus]
    artifacts: Artifacts
    slots: AgentSlots
    events: list[Event]
    errors: list[AgentError]
    metrics: Metrics
```

---

## 4. Meta

```python
class RunMeta(BaseModel):
    run_id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    architecture_version: str
    agent_registry_version: str
    skill_registry_fingerprint: str
    status: Literal[
        "created",
        "running",
        "waiting_for_user",
        "blocked",
        "completed",
        "failed",
        "cancelled"
    ]
```

---

## 5. ProjectContext

```python
class ProjectContext(BaseModel):
    name: str
    repo_path: str | None
    repo_url: str | None
    stack: list[str]
    package_manager: str | None
    test_commands: list[str]
    build_commands: list[str]
    deploy_target: str | None
    constraints: list[str]
```

---

## 6. WorkflowState

```python
class WorkflowState(BaseModel):
    current_phase: str
    completed_phases: list[str]
    pending_phases: list[str]
    retry_counts: dict[str, int]
    max_retries: int = 3
    execution_mode: Literal["interactive", "automatic"] = "interactive"
```

---

## 7. Approvals

Cada gate humano se guarda explícitamente.

```python
class Approval(BaseModel):
    approval_id: str
    gate: str
    status: Literal["pending", "approved", "rejected", "changes_requested"]
    requested_by: str
    requested_at: datetime
    answered_at: datetime | None
    user_response: str | None
    artifact_versions: dict[str, int]
```

Ejemplos:

```text
approval.prd
approval.spec
approval.design_system
approval.release
approval.deploy
```

---

## 8. Gates

```python
class GateStatus(BaseModel):
    gate_id: str
    status: Literal["not_started", "pending", "passed", "failed", "blocked"]
    checked_by: str
    checked_at: datetime | None
    required_artifacts: list[str]
    blocking_issues: list[str]
    warnings: list[str]
```

Gates iniciales:

```text
prd_gate
spec_gate
tdd_gate
contract_gate
review_gate
security_gate
qa_gate
release_gate
deploy_gate
```

---

## 9. Artifacts

Artefactos canónicos. Cada uno tiene versión.

```python
class Artifact(BaseModel):
    artifact_id: str
    kind: str
    path: str | None
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    status: Literal["draft", "approved", "superseded", "rejected"]
    summary: str
    content_hash: str
```

```python
class Artifacts(BaseModel):
    discovery: Artifact | None
    prd: Artifact | None
    spec: Artifact | None
    design: Artifact | None
    design_system: Artifact | None
    task_graph: Artifact | None
    test_plan: Artifact | None
    contract_report: Artifact | None
    code_review_report: Artifact | None
    security_report: Artifact | None
    qa_report: Artifact | None
    dependency_report: Artifact | None
    docs: list[Artifact]
    release_notes: Artifact | None
    deploy_report: Artifact | None
```

---

## 10. Agent Slots

Slots de escritura privada por agente.

```python
class AgentSlot(BaseModel):
    owner: str
    status: Literal["empty", "working", "done", "failed", "needs_input"]
    updated_at: datetime
    summary: str | None
    data: dict
    produced_artifacts: list[str]
    issues: list[str]
    next_actions: list[str]
```

```python
class AgentSlots(BaseModel):
    orchestrator_slot: AgentSlot
    code_orchestrator_slot: AgentSlot
    business_analyst_slot: AgentSlot
    product_manager_slot: AgentSlot
    planner_slot: AgentSlot
    codebase_explorer_slot: AgentSlot
    architect_slot: AgentSlot
    system_designer_slot: AgentSlot
    tester_slot: AgentSlot
    backend_implementer_slot: AgentSlot
    frontend_implementer_slot: AgentSlot
    contract_aligner_slot: AgentSlot
    reviewer_slot: AgentSlot
    security_reviewer_slot: AgentSlot
    qa_gatekeeper_slot: AgentSlot
    dependency_checker_slot: AgentSlot
    technical_writer_slot: AgentSlot
    release_manager_slot: AgentSlot
    builder_slot: AgentSlot
```

---

## 11. Regla de escritura

| Tipo | Quién puede escribir | Ejemplo |
|---|---|---|
| Slot propio | Agente dueño | FrontendImplementer → frontend_implementer_slot |
| Artefacto canónico | Orquestador/consolidador | CodeOrchestrator → spec.md |
| Gate | Orquestador/gatekeeper | QAGatekeeper → qa_gate |
| Approval | HermesOrchestrator | usuario aprueba PRD |
| Event | cualquier nodo | skill loaded, task completed |

Prohibido:

- BackendImplementer escribiendo frontend slot.
- FrontendImplementer editando `design_system` directamente.
- Workers paralelos editando `spec` final.
- Reviewer cambiando código durante review.

---

## 12. Reducers de LangGraph

Para evitar colisiones:

```python
class State(TypedDict):
    events: Annotated[list[Event], operator.add]
    errors: Annotated[list[AgentError], operator.add]
    design_reviews: Annotated[list[DesignReview], operator.add]
    loaded_skills: Annotated[list[SkillLoadEvent], operator.add]
```

Campos con ownership estricto no usan append reducer. Se actualizan por owner.

---

## 13. Paralelismo y merge

### Planning fan-out

```text
ProductManager/prd approved
  ├── Planner writes planner_slot
  ├── CodebaseExplorer writes codebase_explorer_slot
  ├── Architect writes architect_slot
  └── SystemDesigner writes system_designer_slot + design_system draft
        ▼
PlanningConsolidator writes spec/design/task_graph canonical
```

### Implementation fan-out

```text
Tester/test_plan passed
  ├── BackendImplementer writes backend_implementer_slot
  └── FrontendImplementer writes frontend_implementer_slot
        └── SystemDesigner review loop writes design_reviews
        ▼
ContractAligner reads backend + frontend slots
```

### Review fan-out

```text
Implementation done
  ├── Reviewer writes reviewer_slot
  ├── SecurityReviewer writes security_reviewer_slot
  └── Tester writes tester_slot/test_results
        ▼
ReviewConsolidator writes review summary
```

---

## 14. Design System state

`design-system.json` es artefacto canónico, versionado.

```python
class DesignSystem(BaseModel):
    version: int
    owner: Literal["SystemDesigner"]
    tokens: dict
    components: dict
    layouts: dict
    ux_patterns: dict
    accessibility: dict
    visual_api_contracts: dict
    change_log: list[DesignSystemChange]
```

Cambio permitido:

```python
class DesignSystemChange(BaseModel):
    change_id: str
    proposed_by: str
    approved_by: str
    reason: str
    diff_summary: str
    timestamp: datetime
```

Regla:

- FrontendImplementer puede proponer un nuevo componente.
- SystemDesigner decide si se agrega o se reutiliza uno existente.
- Si cambia design-system, se incrementa versión.

---

## 15. Design Review loop

```python
class DesignReview(BaseModel):
    review_id: str
    component_or_page: str
    submitted_by: Literal["FrontendImplementer"]
    reviewed_by: Literal["SystemDesigner"]
    status: Literal["approved", "needs_fix", "rejected"]
    feedback: list[str]
    design_system_version: int
    created_at: datetime
```

Condición:

- Si `needs_fix`, FrontendImplementer recibe feedback y reintenta.
- Máximo 3 reintentos antes de escalar al CodeOrchestrator.

---

## 16. Contract state

```python
class ApiContract(BaseModel):
    endpoints: list[EndpointContract]
    schemas: dict
    auth_requirements: dict
    error_shapes: dict
```

```python
class ContractReport(BaseModel):
    status: Literal["passed", "failed", "warnings"]
    backend_contract_version: str
    frontend_usage_version: str
    mismatches: list[ContractMismatch]
    required_fixes: list[str]
```

ContractAligner bloquea si:

- endpoint consumido por frontend no existe;
- shape de respuesta no coincide;
- auth requerida no contemplada;
- error shape no manejado;
- breaking change no documentado.

---

## 17. Eventos

```python
class Event(BaseModel):
    event_id: str
    timestamp: datetime
    run_id: str
    agent: str
    type: str
    summary: str
    data: dict
```

Tipos iniciales:

```text
run.created
agent.started
agent.completed
agent.failed
skill.loaded
skill.blocked
gate.requested
gate.passed
gate.failed
approval.requested
approval.received
artifact.created
artifact.updated
design.reviewed
contract.checked
release.created
deploy.completed
```

---

## 18. Errores y reintentos

```python
class AgentError(BaseModel):
    error_id: str
    agent: str
    phase: str
    severity: Literal["warning", "error", "critical"]
    message: str
    stack_or_trace: str | None
    retryable: bool
    retry_count: int
    suggested_action: str | None
```

Reglas:

- warning no bloquea salvo gate lo determine;
- error retryable puede reintentar hasta 3 veces;
- critical bloquea y escala;
- si el mismo agente falla 3 veces, CodeOrchestrator decide replanificar o pedir input.

---

## 19. Checkpointing

MVP:

```text
SQLite checkpointer local
workspace/.hermes-state/checkpoints/{project_id}.sqlite
```

Producción:

```text
Postgres checkpointer
```

Cada checkpoint debe incluir:

- SharedState completo serializable;
- nodo actual;
- próximas transiciones;
- eventos acumulados;
- artifact versions.

Permite:

- pausar en gate humano;
- retomar sesión;
- reintentar desde nodo fallido;
- auditar qué cambió.

---

## 20. Persistencia en disco

Estructura por proyecto:

```text
workspace/.hermes-state/projects/{project_id}/
  state/
    current-state.json
    checkpoints.sqlite
    events.jsonl
    skill-load-events.jsonl
  artifacts/
    01-discovery/discovery.md
    02-prd/prd.md
    03-spec/spec.md
    04-design/design.md
    04-design/design-system.json
    05-tests/test-plan.md
    06-implementation/backend-summary.md
    06-implementation/frontend-summary.md
    07-review/code-review-report.md
    07-review/security-report.md
    08-qa/qa-report.md
    09-release/release-notes.md
    10-deploy/deploy-report.md
  slots/
    planner_slot.json
    architect_slot.json
    frontend_implementer_slot.json
    ...
```

---

## 21. UI-readiness

El estado está diseñado para mostrarse en web:

- Timeline: `events`.
- Agent cards: `slots`.
- Gate approvals: `approvals` + `gates`.
- Artifacts panel: `artifacts`.
- Skills panel: `skill-load-events`.
- Design panel: `design_system` + `design_reviews`.
- Error panel: `errors`.

---

## 22. Seguridad de estado

No guardar:

- API keys en artifacts;
- tokens completos;
- secretos en logs;
- credenciales de deploy;
- datos sensibles no necesarios.

Redacción automática:

```text
sk-...
ghp_...
Bearer ...
password=...
secret=...
token=...
```

---

## 23. MVP de implementación

1. Definir modelos Pydantic de estado.
2. Crear StateStore local.
3. Crear helpers de lectura/escritura por slot.
4. Crear artifact writer versionado.
5. Crear event logger JSONL.
6. Integrar SQLite checkpointer de LangGraph.
7. Crear tests de:
   - escritura de slot propio;
   - bloqueo de escritura ajena;
   - merge de fan-out;
   - gate pending/resume;
   - artifact versioning.

---

## 24. Criterio de listo

El SharedState está listo cuando:

- un run puede pausarse y retomarse;
- dos agentes paralelos pueden escribir sin pisarse;
- un consolidador puede generar spec desde slots;
- un gate humano puede quedar pending y luego approved;
- todos los eventos quedan auditados;
- la UI puede leer current-state.json y mostrar estado básico.
