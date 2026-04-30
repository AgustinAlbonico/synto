# Prompt Improver - Main package
"""Client-side prompt quality analysis and improvement."""
from .improve import improve_primer, ImprovedPrompt, WorkspaceContext
from .types import QualityScore, IntentResult, Depth, AppliedImprovement, IntentType

# Alias for convenience
improve_primer = improve_primer
__all__ = [
    "improve_primer",
    "ImprovedPrompt",
    "WorkspaceContext",
    "QualityScore",
    "IntentResult",
    "Depth",
    "AppliedImprovement",
    "IntentType",
]
