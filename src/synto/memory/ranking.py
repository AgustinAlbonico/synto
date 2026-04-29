"""Memory ranking — heuristic scoring without embeddings."""

import time

from synto.memory.models import MemoryItem, MemorySearchResult


def rank_items(
    results: list[MemorySearchResult],
    project_id: str = "",
    agent_role: str = "",
    max_age_days: int = 0,
) -> list[MemorySearchResult]:
    """Re-rank search results with heuristics.
    
    score = fts_rank
          + project_scope_boost
          + agent_role_boost
          + importance * 0.3
          + confidence * 0.2
          - stale_penalty
    """
    now = time.time()
    day_seconds = 86400

    scored = []
    for r in results:
        score = r.score

        # Project scope boost
        if project_id and r.item.project_id == project_id:
            score += 0.3

        # Importance boost
        score += r.item.importance * 0.3

        # Confidence boost
        score += r.item.confidence * 0.2

        # Stale penalty: older items get penalized
        age_days = (now - r.item.updated_at) / day_seconds
        if max_age_days and age_days > max_age_days:
            score -= 0.5
        elif age_days > 90:
            score -= 0.1
        elif age_days > 30:
            score -= 0.05

        r.score = max(0.0, min(1.0, score))
        scored.append(r)

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored
