"""Deterministic memory tool layer used by the MCP server and workflows."""

from __future__ import annotations

from typing import Any

from synto.memory import (
    MemoryCandidate,
    MemoryContextAgent,
    MemoryKind,
    MemoryStore,
    TaskContext,
)


class MemoryToolLayer:
    """Thin deterministic wrapper around MemoryStore operations.

    This layer bounds outputs and returns plain dict/list structures so the same
    behavior can be exposed via MCP without duplicating business logic.
    """

    def __init__(self, store: MemoryStore):
        self.store = store
        self.context_agent = MemoryContextAgent(store)

    def create_project(self, slug: str, name: str) -> str:
        existing = self.store.get_project(slug)
        if existing:
            return existing["id"]
        return self.store.create_project(slug, name)

    def list_projects(self) -> list[dict[str, Any]]:
        return self.store.list_projects()

    def search(self, query: str, project_id: str = "", limit: int = 10) -> list[dict[str, Any]]:
        results = self.store.search(query, project_id=project_id, limit=limit)
        return [
            {
                "id": r.item.id,
                "project_id": r.item.project_id,
                "feature_id": r.item.feature_id,
                "topic_id": r.item.topic_id,
                "kind": r.item.kind.value,
                "title": r.item.title,
                "content": r.item.content[:300],
                "score": round(r.score, 3),
                "importance": r.item.importance,
                "confidence": r.item.confidence,
            }
            for r in results
        ]

    def get_item(self, memory_id: str) -> dict[str, Any] | None:
        item = self.store.get_memory_item(memory_id)
        if not item:
            return None
        return {
            "id": item.id,
            "project_id": item.project_id,
            "feature_id": item.feature_id,
            "topic_id": item.topic_id,
            "kind": item.kind.value,
            "status": item.status.value,
            "title": item.title,
            "content": item.content,
            "tags": item.tags,
            "importance": item.importance,
            "confidence": item.confidence,
            "metadata": item.metadata,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def get_tree(self, project_id: str) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        if not project:
            return {"project": None, "features": [], "root_memory_count": 0}

        resolved_project_id = project["id"]
        features = self.store.list_features(resolved_project_id)
        feature_nodes: list[dict[str, Any]] = []

        for feature in features:
            topics = self.store.list_topics(resolved_project_id, feature["id"])
            feature_items = self.store.list_by_hierarchy(resolved_project_id, feature_id=feature["id"])
            topic_nodes: list[dict[str, Any]] = []
            for topic in topics:
                topic_items = self.store.list_by_hierarchy(resolved_project_id, topic_id=topic["id"])
                topic_nodes.append(
                    {
                        "id": topic["id"],
                        "slug": topic["slug"],
                        "name": topic["name"],
                        "memory_count": len(topic_items),
                    }
                )

            feature_nodes.append(
                {
                    "id": feature["id"],
                    "slug": feature["slug"],
                    "name": feature["name"],
                    "memory_count": len(feature_items),
                    "topics": topic_nodes,
                }
            )

        root_items = [
            i for i in self.store.list_by_project(resolved_project_id)
            if not i.feature_id and not i.topic_id
        ]

        return {
            "project": project,
            "features": feature_nodes,
            "root_memory_count": len(root_items),
        }

    def build_pack(
        self,
        agent_id: str,
        task: str,
        project_id: str,
        token_budget: int = 4000,
    ) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        resolved_project_id = project["id"] if project else project_id
        packs = self.context_agent.hydrate(
            TaskContext(task=task, project_id=resolved_project_id, agent_ids=[agent_id]),
            [agent_id],
            token_budget=token_budget,
        )
        pack = packs.get(agent_id)
        if not pack:
            return {
                "agent_id": agent_id,
                "task_summary": task,
                "total_tokens_estimate": 0,
                "token_budget": token_budget,
                "items": [],
            }

        return {
            "agent_id": pack.agent_id,
            "task_summary": pack.task_summary,
            "total_tokens_estimate": pack.total_tokens_estimate,
            "token_budget": pack.token_budget,
            "items": [item.model_dump() for item in pack.items],
        }

    def add_candidate(
        self,
        project_id: str,
        content: str,
        source_agent: str = "",
        kind: str = "note",
        title: str = "",
        reasoning: str = "",
        feature_id: str = "",
        topic_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        candidate = MemoryCandidate(
            source_agent=source_agent,
            kind=MemoryKind(kind),
            title=title,
            content=content,
            project_id=project_id,
            feature_id=feature_id,
            topic_id=topic_id,
            tags=tags or [],
            reasoning=reasoning,
        )
        return self.store.add_candidate(candidate)

    def list_candidates(self, project_id: str = "") -> list[dict[str, Any]]:
        return self.store.list_candidates(project_id=project_id)

    def commit_candidate(self, candidate_id: str, actor: str = "tool") -> str:
        return self.store.commit_candidate(candidate_id, actor=actor)

    def reject_candidate(self, candidate_id: str, reason: str = "", actor: str = "tool") -> str:
        self.store.reject_candidate(candidate_id, reason=reason, actor=actor)
        return "rejected"

    def link_items(self, source_id: str, target_id: str, link_type: str = "related") -> str:
        return self.store.link_items(source_id, target_id, link_type)

    def forget(self, memory_id: str, actor: str = "tool") -> str:
        self.store.delete_memory_item(memory_id, actor=actor)
        return memory_id

    def stats(self) -> dict[str, Any]:
        return self.store.stats()

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.get_audit_log(limit=limit)
