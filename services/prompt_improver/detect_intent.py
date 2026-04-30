"""
Detección de intent del prompt
"""
import re
from typing import TypedDict
from .types import IntentType, IntentResult


INTENT_PATTERNS: dict[IntentType, tuple[list[str], float]] = {
    "code-generation": (
        [
            "crear", "implementar", "hacer", "construir", "generar", "agregar",
            "add", "create", "implement", "build", "generate", "make", "write",
            "nuevo", "new feature", "function", "endpoint", "componente", "component",
            "módulo", "module", "service", "api", "hook",
        ],
        1.0,
    ),
    "planning": (
        [
            "planificar", "diseñar", "arquitectura", "estructura", "cómo",
            "plan", "design", "architecture", "structure", "how to", "debería",
            "should", "approach", "estrategia", "estrategic",
        ],
        0.9,
    ),
    "refinement": (
        [
            "mejorar", "refactorizar", "optimizar", "limpiar", "reorganizar",
            "improve", "refactor", "optimize", "clean", "restructure", "rename",
            "extract", "simplify",
        ],
        0.9,
    ),
    "debugging": (
        [
            "bug", "error", "fallo", "problema", "no funciona", "no anda",
            "fix", "debug", "issue", "broken", "not working", "crash", "exception",
            "fallando", "stack trace", "traceback",
        ],
        1.0,
    ),
    "documentation": (
        [
            "documentar", "docs", "readme", "comentar", "explicar",
            "document", "comment", "explain", "readme", "wiki", "guía", "guide",
            "tutorial", "api docs",
        ],
        1.0,
    ),
    "prd-generation": (
        [
            "requisitos", "spec", "prd", "user story", "historia de usuario",
            "requirements", "specification", "product", "feature request",
        ],
        1.0,
    ),
    "testing": (
        [
            "test", "tests", "testing", "prueba", "pruebas", "unit test",
            "e2e", "integration", "coverage", "spec", "spy", "mock",
        ],
        1.0,
    ),
    "migration": (
        [
            "migrar", "actualizar", "upgrade", "portar", "convertir",
            "migrate", "update version", "port", "convert", "from",
        ],
        1.0,
    ),
    "security-review": (
        [
            "security", "seguridad", "vulnerability", "vulnerabilidad", "audit",
            "auth", "authentication", "authorization", "permission", "sanitize",
            "cors", "xss", "sql injection", "injection",
        ],
        1.0,
    ),
    "learning": (
        [
            "explicar", "entender", "cómo funciona", "qué es",
            "explain", "understand", "how does", "what is", "learn", "teach",
            "show me", "tell me", "tutorial", "concept",
        ],
        1.0,
    ),
    "summarization": (
        [
            "resumir", "summarize", "summary", "extract", "key points", "overview",
            "resumen", "extract requirements",
        ],
        1.0,
    ),
}


def _score_keyword_match(text: str, keywords: list[str]) -> float:
    """Cuenta cuántas keywords aparecen en el texto."""
    lower = text.lower()
    matches = 0

    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if re.search(pattern, lower):
            matches += 1

    return min(matches / len(keywords), 1.0) if keywords else 0.0


def detect_intent(prompt: str) -> IntentResult:
    """Detecta el tipo de intent del prompt."""
    scores: list[tuple[IntentType, float]] = []

    for intent_type, (keywords, weight) in INTENT_PATTERNS.items():
        score = _score_keyword_match(prompt, keywords) * weight
        scores.append((intent_type, score))

    # Ordenar por score descendente
    scores.sort(key=lambda x: x[1], reverse=True)

    top_type, top_score = scores[0]
    _, second_score = scores[1]

    # Confidence: alto si hay un claro ganador, bajo si es ambiguo
    if second_score > 0.3:
        confidence = min(top_score * 0.8, 0.9)
    else:
        confidence = min(top_score * 1.2, 1.0)

    detected_type = top_type if top_score > 0.05 else "code-generation"

    return IntentResult(
        type=detected_type,
        confidence=int(confidence * 100),
    )