"""Obsidian export — generate human-readable Markdown from memory."""

from pathlib import Path
import json

from synto.memory import MemoryStore, MemoryItem


def _memory_to_markdown(item: MemoryItem) -> str:
    """Convert a MemoryItem to Obsidian-flavored Markdown."""
    lines = [
        f"# {item.title or item.kind.value}",
        "",
        f"**Kind:** {item.kind.value}",
        f"**Status:** {item.status.value}",
        f"**Importance:** {item.importance:.1%}",
        f"**Confidence:** {item.confidence:.1%}",
        f"**Created:** {item.created_iso}",
        f"**Updated:** {item.updated_iso}",
        "",
        "---",
        "",
        item.content,
    ]

    if item.tags:
        tag_line = " ".join(f"#{t}" for t in item.tags)
        lines.extend(["", tag_line])

    lines.extend(["", "---", ""])

    # Links
    if item.metadata:
        lines.append("## Metadata")
        lines.append("```json")
        lines.append(json.dumps(item.metadata, indent=2))
        lines.append("```")

    return "\n".join(lines)


def export_to_obsidian(
    store: MemoryStore,
    output_dir: str,
    project_id: str = "",
) -> dict[str, str]:
    """Export memory items to Obsidian vault structure.
    
    Output: {output_dir}/{project}/{feature}/{topic}.md
    
    Returns dict mapping file_path -> memory_id.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    files = {}

    if project_id:
        projects = [store.get_project_by_id(project_id)] if hasattr(store, 'get_project_by_id') else []
        items = store.list_by_project(project_id)
    else:
        items = []
        for proj in store.list_projects():
            items.extend(store.list_by_project(proj["id"]))

    for item in items:
        # Build path: project/feature/topic.md
        proj_slug = item.project_id
        feat_slug = item.feature_id or "_root"
        topic_slug = item.topic_id or "_general"

        item_dir = output / proj_slug / feat_slug
        item_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        title = (item.title or item.id).replace("/", "-").replace("\\", "-")[:100]
        filename = f"{title}.md"
        filepath = item_dir / filename

        filepath.write_text(_memory_to_markdown(item))
        files[str(filepath)] = item.id

    return files
