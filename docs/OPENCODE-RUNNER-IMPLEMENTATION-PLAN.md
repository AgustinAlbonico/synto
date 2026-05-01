# OpenCode Runner — implementation plan

Estado: plan técnico listo para implementar
Fecha: 2026-04-30

## Objetivo

Permitir que Synto ejecute cada agente ejecutor como una sesión OpenCode trazable, con contexto propio, logs persistidos, diff verificable y resultado estructurado.

## Decisión base

Usar `opencode run`, no TUI, para el MVP.

Comando verificado:

```bash
opencode run \
  --format json \
  --agent build \
  --title "synto:{run_id}:{agent_id}:{task_id}" \
  -f .synto/runs/{run_id}/context/{agent_id}.md \
  --dir "{workdir}" \
  "{task_prompt}"
```

Versión verificada localmente:

```txt
opencode 1.14.28
```

No usar `--dangerously-skip-permissions` por defecto.

## Archivos a crear

```txt
src/synto/runtime/__init__.py
src/synto/runtime/opencode_runner.py
tests/runtime/test_opencode_runner.py
```

## Tipos principales

```python
@dataclass(frozen=True)
class AgentExecutionSpec:
    run_id: str
    agent_id: str
    task_id: str
    task_prompt: str
    workdir: Path
    context_markdown: str
    opencode_agent: str = "build"
    model: str | None = None
    mode: Literal["read_only", "write", "test_only"] = "write"
    timeout_seconds: int = 900
    allowed_paths: tuple[str, ...] = ()

@dataclass(frozen=True)
class AgentRunResult:
    run_id: str
    agent_id: str
    task_id: str
    status: Literal["success", "failed", "timeout"]
    exit_code: int | None
    files_changed: tuple[str, ...]
    stdout_path: Path
    stderr_path: Path
    events_path: Path
    patch_path: Path | None
    summary: str
```

## OpenCodeSessionRunner responsibilities

1. Resolver binario:
   - primero `/home/agust/.opencode/bin/opencode` si existe;
   - fallback a `opencode` en PATH.
2. Crear directorios:
   - `.synto/runs/{run_id}/context/`
   - `.synto/runs/{run_id}/opencode/{agent_id}/`
   - `.synto/runs/{run_id}/patches/`
3. Escribir context markdown.
4. Ejecutar `opencode run --format json` vía `subprocess.run`.
5. Guardar stdout/stderr.
6. Guardar eventos JSONL crudos si stdout viene en formato JSON/events.
7. Medir `git status --short` antes y después.
8. Crear patch con `git diff --binary` si hubo cambios.
9. Retornar `AgentRunResult`.
10. Nunca confiar solamente en el resumen textual de OpenCode.

## Modos

### read_only

Prompt envelope agrega:

```txt
READ-ONLY MODE. Do not modify files. Do not run write/destructive commands.
```

Verificación posterior:
- si `git status` cambió, status = failed.

### test_only

Prompt envelope agrega:

```txt
TEST-ONLY MODE. You may create/modify tests and test config only. Do not modify production code.
```

Verificación posterior:
- comparar files_changed contra allowlist de tests;
- si toca producción, status = failed.

### write

Puede modificar archivos dentro del scope asignado por el agente.

Verificación posterior:
- comparar files_changed contra allowed_paths si se proveyeron.

## Integración con CodeOrchestrator

Nodo TDD:

```python
spec = AgentExecutionSpec(
    run_id=state.run_id,
    agent_id="TDDAgent",
    task_id="tdd-test-plan",
    workdir=state.workspace,
    mode="test_only",
    context_markdown=build_agent_context("TDDAgent", state),
    task_prompt=build_task_prompt(task),
)
result = opencode_runner.run(spec)
state.test_results = result
```

Nodo implementation:

MVP secuencial:

```txt
BackendImplementer -> FrontendImplementer
```

Luego paralelo seguro:

```txt
git worktree add .synto/worktrees/{run_id}/BackendImplementer HEAD
git worktree add .synto/worktrees/{run_id}/FrontendImplementer HEAD
run both sessions
export patches
apply patches to main workdir
run ContractAligner
```

## API para la app

```txt
POST /api/runs/{run_id}/agents/{agent_id}/execute
GET  /api/runs/{run_id}/agents/{agent_id}/sessions
GET  /api/runs/{run_id}/agents/{agent_id}/logs
GET  /api/runs/{run_id}/agents/{agent_id}/patch
POST /api/runs/{run_id}/agents/{agent_id}/cancel
```

## UI mínima

Card por agente:

```txt
Agent: TDDAgent
Phase: tdd
Status: running|success|failed|blocked
OpenCode session title: synto:{run}:{agent}:{task}
Files changed: N
Patch: path
Logs: stdout/stderr/events
```

## Tests a escribir primero

1. `test_builds_opencode_command_with_json_format_and_title`
2. `test_writes_context_file_under_synto_runs`
3. `test_read_only_mode_fails_if_git_status_changes`
4. `test_test_only_mode_rejects_production_file_changes`
5. `test_generates_patch_when_files_changed`
6. `test_timeout_returns_timeout_status`

## Riesgos

- OpenCode puede pedir permisos si el agente configurado no permite acciones necesarias.
- Sesiones paralelas sobre el mismo workdir pueden pisarse; usar worktrees antes de paralelizar escritura.
- `--format json` puede producir múltiples eventos; guardar crudo y parsear incrementalmente, no asumir una sola respuesta JSON.
- No ejecutar commit/push desde agentes implementadores.

## Siguiente paso recomendado

Implementar primero `OpenCodeSessionRunner` con tests unitarios mockeando `subprocess.run`, sin ejecutar OpenCode real en CI.
