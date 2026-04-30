"""Rule-based prompt improver for the Synto web UI.

This module intentionally does not require an LLM. The UI can expose the flow now,
and a future implementation can swap this with an LLM-backed service while keeping
the same response shape.
"""

from __future__ import annotations

from typing import Any


def _stack_names(stack: dict[str, Any] | None) -> list[str]:
    items = (stack or {}).get("items", [])
    return [str(item.get("name")) for item in items if isinstance(item, dict) and item.get("name")]


def improve_prompt(prompt: str, *, workspace: dict[str, Any] | None = None, stack: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an editable improved prompt plus explanations of the changes."""
    original = str(prompt or "").strip()
    workspace_name = str((workspace or {}).get("name") or (workspace or {}).get("id") or "workspace seleccionado")
    paths = (workspace or {}).get("paths") or (stack or {}).get("paths") or []
    stack_list = _stack_names(stack)

    context_lines = [f"Workspace: {workspace_name}."]
    if paths:
        context_lines.append("Rutas relevantes: " + ", ".join(str(path) for path in paths[:4]) + ("…" if len(paths) > 4 else ""))
    if stack_list:
        context_lines.append("Stack detectado: " + ", ".join(stack_list[:10]) + ("…" if len(stack_list) > 10 else ""))

    improved = f"""Objetivo
{original}

Contexto del workspace
{' '.join(context_lines)}

Forma de trabajo esperada
1. Analizá primero la estructura del workspace y reutilizá las convenciones existentes.
2. Proponé un plan corto antes de modificar archivos si la tarea es grande o riesgosa.
3. Implementá cambios mínimos, coherentes con el stack detectado y sin introducir dependencias innecesarias.
4. Delegá a subagentes especializados cuando corresponda: frontend, backend, testing, seguridad, documentación o devops.
5. Verificá el resultado con tests, lint o checks disponibles en el proyecto.

Criterios de aceptación
- La solución cumple el pedido original sin romper flujos existentes.
- Los archivos modificados son los estrictamente necesarios.
- La respuesta final resume qué se cambió, cómo se verificó y qué queda pendiente si aplica.
""".strip()

    improvements = [
        "Separé objetivo, contexto, forma de trabajo y criterios de aceptación.",
        "Agregué el stack y rutas detectadas para que el orquestador tenga contexto desde el arranque.",
        "Incluí reglas de delegación para que Synto decida mejor qué subagentes activar.",
        "Sumé criterios verificables para reducir ambigüedad y evitar cambios de más.",
    ]
    return {
        "original_prompt": original,
        "improved_prompt": improved,
        "improvements": improvements,
        "why": "El prompt mejorado baja ambigüedad, explicita contexto técnico y le da al orquestador una definición clara de éxito.",
    }
