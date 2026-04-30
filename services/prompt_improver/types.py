"""
Prompt Improver - Tipos y modelos de datos
"""
from typing import Literal, NamedTuple
from dataclasses import dataclass


IntentType = Literal[
    "code-generation",
    "planning",
    "refinement",
    "debugging",
    "documentation",
    "prd-generation",
    "testing",
    "migration",
    "security-review",
    "learning",
    "summarization",
]

QualityDimension = Literal[
    "clarity",
    "efficiency",
    "structure",
    "completeness",
    "actionability",
    "specificity",
]

Depth = Literal["standard", "comprehensive"]


@dataclass
class QualityScore:
    clarity: int
    efficiency: int
    structure: int
    completeness: int
    actionability: int
    specificity: int
    overall: int


@dataclass
class AppliedImprovement:
    dimension: QualityDimension
    description: str


@dataclass
class IntentResult:
    type: IntentType
    confidence: int


@dataclass
class WorkspaceContext:
    name: str | None = None
    frameworks: list[str] | None = None
    languages: list[str] | None = None
    databases: list[str] | None = None
    package_manager: str | None = None


@dataclass
class ImprovedPrompt:
    intent: IntentResult
    quality: QualityScore
    depth: Depth
    improved: str
    improvements: list[AppliedImprovement]


DIMENSION_LABELS = {
    "clarity": "Claridad",
    "efficiency": "Eficiencia",
    "structure": "Estructura",
    "completeness": "Completitud",
    "actionability": "Acción",
    "specificity": "Especificidad",
}

DIMENSION_ICONS = {
    "clarity": "💡",
    "efficiency": "⚡",
    "structure": "📐",
    "completeness": "📋",
    "actionability": "🎯",
    "specificity": "🔍",
}