# apply_improvements.py
"""Orchestrates: intent detection → quality evaluation → improvement application"""
from .types import (
    ImprovedPrompt,
    WorkspaceContext,
    QualityScore,
    IntentResult,
    Depth,
    AppliedImprovement,
    IntentType,
)
from .detect_intent import detect_intent
from .evaluate_quality import evaluate_quality


def improve_primer(
    raw: str,
    context: WorkspaceContext | None = None,
) -> ImprovedPrompt:
    """
    Función principal para mejorar un prompt.
    
    Args:
        raw: Prompt original del usuario
        context: Contexto opcional del workspace (stack, nombre, etc.)
    
    Returns:
        ImprovedPrompt con intent, quality score, y prompt mejorado
    """
    if not raw.strip():
        return ImprovedPrompt(
            intent=IntentResult(type="code-generation", confidence=0),
            quality=QualityScore(
                clarity=0, efficiency=0, structure=0,
                completeness=0, actionability=0, specificity=0, overall=0,
            ),
            depth="standard",
            improved=raw,
            improvements=[],
        )

    # Paso 1: Detectar intent
    intent = detect_intent(raw)

    # Paso 2: Evaluar calidad
    quality = evaluate_quality(raw)

    # Paso 3: Determinar profundidad
    depth: Depth = (
        "comprehensive" if quality.overall >= 75
        else "standard"
    )

    # Paso 4: Aplicar mejoras
    improved, improvements = _apply_improvements(raw, intent.type, depth, context)

    return ImprovedPrompt(
        intent=intent,
        quality=quality,
        depth=depth,
        improved=improved,
        improvements=improvements,
    )


def _apply_improvements(
    original: str,
    intent: IntentType,
    depth: Depth,
    context: WorkspaceContext | None = None,
) -> tuple[str, list[AppliedImprovement]]:
    """Aplica mejoras al prompt."""
    import re
    improvements: list[AppliedImprovement] = []
    result = original.strip()

    # Verificar si tiene verbo de acción
    action_verbs = [
        "crear", "implementar", "agregar", "hacer", "diseñar",
        "fix", "build", "create", "add", "implement", "write",
    ]
    has_action = any(
        re.search(rf"^\b{verb}\b", result, re.IGNORECASE)
        for verb in action_verbs
    )

    if not has_action:
        preambles: dict[IntentType, str] = {
            "code-generation": "Implementar",
            "planning": "Diseñar y planificar",
            "refinement": "Refactorizar y mejorar",
            "debugging": "Diagnosticar y resolver el bug en",
            "documentation": "Documentar",
            "prd-generation": "Crear especificación de requisitos para",
            "testing": "Escribir tests para",
            "migration": "Migrar",
            "security-review": "Realizar revisión de seguridad de",
            "learning": "Explicar cómo funciona",
            "summarization": "Resumir y extraer puntos clave de",
        }
        preamble = preambles.get(intent, "Implementar")
        result = f"{preamble} {result}"
        improvements.append(AppliedImprovement(
            dimension="clarity",
            description="Verbo de acción explícito añadido",
        ))

    # Agregar contexto si está disponible
    if context:
        if context. name and context. name.lower() not in result.lower():
            result += f" en {context.name}"
            improvements.append(AppliedImprovement(
                dimension="completeness",
                description="Contexto de workspace añadido",
            ))
        if context.frameworks or context.languages:
            parts = []
            if context.frameworks:
                parts.extend(context.frameworks)
            if context.languages:
                parts.extend(context.languages)
            if parts:
                result += f" (Stack: {', '.join(parts)})"

    # Asegurar puntuación final
    if not re.search(r"[.!?]$", result):
        result += "."
        improvements.append(AppliedImprovement(
            dimension="clarity",
            description="Puntuación final añadida",
        ))

    return result, improvements


# Alias para compatibilidad
improve_prompt = improve_primer

__all__ = [
    "improve_prompt",
    "improve_primer",
    "ImprovedPrompt",
    "WorkspaceContext",
]