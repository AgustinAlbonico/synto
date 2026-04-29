"""MemoryContextAgent — builds context for agents at the start of a run."""

from typing import Optional

from synto.memory.models import (
    TaskContext, MemoryPack, MemorySearchResult,
)
from synto.memory.store import MemoryStore
from synto.memory.pack_builder import MemoryPackBuilder


class MemoryContextAgent:
    """Builds context for agents at the start of a run.
    
    Rules:
    - Does not talk to users
    - Does not save memory directly
    - Does not read SQLite directly — uses MemoryStore interface
    - Returns small, focused packs
    """

    def __init__(self, store: MemoryStore, pack_builder: Optional[MemoryPackBuilder] = None):
        self.store = store
        self.pack_builder = pack_builder or MemoryPackBuilder()

    def hydrate(
        self,
        task: TaskContext,
        agent_ids: list[str],
        token_budget: int = 4000,
    ) -> dict[str, MemoryPack]:
        """Build memory packs for each agent based on the task.
        
        Args:
            task: The task context
            agent_ids: List of agent IDs to build packs for
            token_budget: Max tokens per pack
            
        Returns:
            Dict mapping agent_id -> MemoryPack
        """
        # Search for memories relevant to the task
        keywords = " ".join(task.task.split()[:10])
        results: list[MemorySearchResult] = []
        
        try:
            results = self.store.search(
                keywords,
                project_id=task.project_id,
                limit=50,
            )
        except Exception:
            pass  # No results if search fails (e.g., empty DB)

        # Build one pack per agent
        packs: dict[str, MemoryPack] = {}
        for agent_id in agent_ids:
            pack = self.pack_builder.build_pack(
                task=task,
                agent_id=agent_id,
                results=results,
                token_budget=token_budget,
            )
            packs[agent_id] = pack

        return packs

    def get_global_context(self, project_id: str, limit: int = 10) -> list[dict]:
        """Get high-level project context (recent, important memories)."""
        items = self.store.list_by_project(project_id)
        return [
            {
                "id": i.id,
                "title": i.title or i.kind.value,
                "snippet": i.content[:200],
                "kind": i.kind.value,
                "importance": i.importance,
            }
            for i in items[:limit]
        ]
