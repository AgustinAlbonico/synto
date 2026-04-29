"""MemoryPackBuilder — transforms search results into bounded context packages."""

from synto.memory.models import (
    TaskContext, MemoryPack, MemoryPackItem, MemorySearchResult,
)
from synto.memory.ranking import rank_items


SNIPPET_MAX_CHARS = 300


def _make_pack_item(result: MemorySearchResult) -> MemoryPackItem:
    content = result.item.content
    snippet = content[:SNIPPET_MAX_CHARS]
    if len(content) > SNIPPET_MAX_CHARS:
        snippet += "..."
    
    source_parts = [result.item.project_id]
    if result.item.feature_id:
        source_parts.append(result.item.feature_id)
    if result.item.topic_id:
        source_parts.append(result.item.topic_id)

    return MemoryPackItem(
        id=result.item.id,
        title=result.item.title or result.item.kind.value,
        snippet=snippet,
        source="/".join(source_parts),
        importance=result.item.importance,
        link_back=f"score={result.score:.2f}",
    )


class MemoryPackBuilder:
    """Builds bounded memory packs for agents."""

    def __init__(self, default_token_budget: int = 4000):
        self.default_token_budget = default_token_budget

    def build_pack(
        self,
        task: TaskContext,
        agent_id: str,
        results: list[MemorySearchResult],
        token_budget: int = 0,
    ) -> MemoryPack:
        """Build a memory pack from search results.
        
        Args:
            task: The task context
            agent_id: Target agent
            results: Ranked search results
            token_budget: Max tokens (defaults to class default)
        """
        budget = token_budget or self.default_token_budget
        pack = MemoryPack(
            agent_id=agent_id,
            task_summary=task.task,
            token_budget=budget,
        )

        # Re-rank with project context
        ranked = rank_items(results, project_id=task.project_id)

        for result in ranked:
            item = _make_pack_item(result)
            if not pack.add_item(item):
                break  # budget exceeded

        return pack
