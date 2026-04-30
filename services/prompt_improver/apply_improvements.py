# Prompt Improver - Punto de entrada
"""
Orchestrates: intent detection → quality evaluation → improvement application
"""
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
from .apply_improvements import apply_improvements


def improve_prompt(
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
    improved, improvements = apply_improvements(raw, intent.type, depth, context)

    return ImprovedPrompt(
        intent=intent,
        quality=quality,
        depth=depth,
        improved=improved,
        improvements=improvements,
    )


# Exports方便
__all__ = [
    "improve_prompt",
    "ImprovedPrompt",
    "WorkspaceContext",
    "QualityScore",
    "IntentResult",
    "Depth",
    "AppliedImprovement",
    "IntentType",
]