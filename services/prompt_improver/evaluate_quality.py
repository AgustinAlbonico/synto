"""
Evaluación de calidad en 6 dimensiones
"""
import re
from typing import NamedTuple
from .types import QualityScore, QualityDimension


class IndicatorSet(NamedTuple):
    boost: list[str]
    reduce: list[str]


DIMENSION_WEIGHTS: dict[QualityDimension, float] = {
    "clarity": 0.20,
    "efficiency": 0.12,
    "structure": 0.13,
    "completeness": 0.20,
    "actionability": 0.20,
    "specificity": 0.15,
}


SCORE_INDICATORS: dict[QualityDimension, IndicatorSet] = {
    "clarity": IndicatorSet(
        boost=[
            r"\b(crear|implementar|agregar|build|create|implement|add)\b",
            r"\bpara\b",
            r"[?!.]$",
        ],
        reduce=[
            r"^(quiero|necesito|ayuda|hacer)",
            r"\balgo\b|\bcosas?\b",
            r"^.{0,20}$",
        ],
    ),
    "efficiency": IndicatorSet(
        boost=[
            r"\b(y|and|with|con)\b.{0,30}\b(y|and|with|con)\b",
            r"^\S.{0,100}$",
        ],
        reduce=[
            r"\b(por favor|gracias|disculpa)\b",
            r"\b(es que|esto es lo que|lo que necesito es)\b",
        ],
    ),
    "structure": IndicatorSet(
        boost=[
            r"^[\-\*•]\s",
            r"^\d+[.)]\s",
            r"\b(contexto:|request:|constraints:|criteria:)\b",
            r"\n\n",
        ],
        reduce=[
            r"^[A-Z][^.!?]*[.!?]([A-Z][^.!?]*[.!?])*$",
        ],
    ),
    "completeness": IndicatorSet(
        boost=[
            r"\b(v\d+\.\d+|version|versión)\b",
            r"\b(npm|pnpm|yarn|pip|poetry)\b",
            r"\b(eslint|prettier|jest|vitest|playwright)\b",
            r"\b(es|de|en|con|para)\b.{10,}",
        ],
        reduce=[
            r"^.{0,30}$",
        ],
    ),
    "actionability": IndicatorSet(
        boost=[
            r"\b(debería|should|must|has to|tiene que)\b",
            r"\b(resultado|output|result|expect|expected)\b",
            r"\b(que devuelva|que muestre|que guarde|return|show|save)\b",
        ],
        reduce=[
            r"\b(maybe|posibly|quizás)\b",
            r"\b(intentar|try to|tratar de)\b",
        ],
    ),
    "specificity": IndicatorSet(
        boost=[
            r"\b\d+\.\d+(\.\d+)?\b",
            r"\b(postgresql|mysql|mongodb|sqlite|redis)\b",
            r"\b(react|nestjs|fastapi|express|next\.?js)\b",
        ],
        reduce=[
            r"\b(framework|backend|frontend|base de datos)\b",
            r"\b(algún|alguno|some|any)\b",
            r"\b(normalmente|generalmente|usually)\b",
        ],
    ),
}


def _evaluate_dimension(prompt: str, dimension: QualityDimension) -> int:
    """Evalúa una dimensión específica."""
    indicators = SCORE_INDICATORS[dimension]
    base_score = 50

    # Aplicar boosts
    for pattern in indicators.boost:
        if re.search(pattern, prompt, re.IGNORECASE):
            base_score += 10

    # Aplicar reduces
    for pattern in indicators.reduce:
        if re.search(pattern, prompt, re.IGNORECASE):
            base_score -= 15

    # Clampear entre 0-100
    return max(0, min(100, base_score))


def evaluate_quality(prompt: str) -> QualityScore:
    """Evalúa la calidad del prompt en 6 dimensiones."""
    dimensions: list[QualityDimension] = [
        "clarity",
        "efficiency",
        "structure",
        "completeness",
        "actionability",
        "specificity",
    ]

    scores = {dim: _evaluate_dimension(prompt, dim) for dim in dimensions}

    # Calcular promedio ponderado
    overall = sum(scores[dim] * DIMENSION_WEIGHTS[dim] for dim in dimensions)

    return QualityScore(
        clarity=scores["clarity"],
        efficiency=scores["efficiency"],
        structure=scores["structure"],
        completeness=scores["completeness"],
        actionability=scores["actionability"],
        specificity=scores["specificity"],
        overall=int(overall),
    )