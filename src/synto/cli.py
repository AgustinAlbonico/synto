#!/usr/bin/env python3
"""CLI entry point for Synto."""

import argparse
import json
import sys

from synto.workflows import build_initial_state, get_compiled
from synto.memory import (
    MemoryStore,
    MemoryItem,
    MemoryKind,
)
from synto.memory.obsidian_export import export_to_obsidian
from synto.mcp.memory_tools import MemoryToolLayer
from synto.registry import AgentRegistry


def cmd_run(args):
    """Run a task through the orchestrator."""
    workflow = get_compiled()
    initial_state = build_initial_state(
        task=args.task,
        project_id=args.project or "default",
        memory_db_path=args.memory_db,
        config_dir=args.config_dir or "",
    )

    print(f"[orchestrator] Running: {args.task}")
    print(f"[orchestrator] Project: {args.project or 'default'}")
    print(f"[orchestrator] Memory DB: {args.memory_db}")

    result = workflow.invoke(initial_state)
    print("\n=== Run Complete ===")
    print(result.get("result", "no output"))
    print(f"\n[orchestrator] Events: {len(result.get('events', []))}")



def _resolve_project_id(store: MemoryStore, project: str) -> str:
    if not project:
        return ""
    proj = store.get_project(project)
    return proj["id"] if proj else project



def cmd_memory(args):
    """Memory operations CLI."""
    store = MemoryStore(args.db)
    tools = MemoryToolLayer(store)

    if args.memory_cmd == "init":
        pid = tools.create_project(args.project, args.project)
        print(f"  Project ready: {args.project} (id={pid})")

    elif args.memory_cmd == "add":
        if not args.project:
            print("ERROR: --project required", file=sys.stderr)
            sys.exit(1)
        text = args.text or args.query_or_text
        if not text:
            print("ERROR: --text or provide text as argument", file=sys.stderr)
            sys.exit(1)
        proj = store.get_project(args.project)
        if not proj:
            pid = store.create_project(args.project, args.project)
        else:
            pid = proj["id"]

        fid = ""
        if args.feature:
            features = store.list_features(pid)
            existing = [f for f in features if f["slug"] == args.feature]
            if existing:
                fid = existing[0]["id"]
            else:
                fid = store.create_feature(pid, args.feature, args.feature)

        tid = ""
        if args.topic:
            existing_topics = [t for t in store.list_topics(pid, fid) if t["slug"] == args.topic]
            if existing_topics:
                tid = existing_topics[0]["id"]
            else:
                tid = store.create_topic(pid, args.topic, args.topic, feature_id=fid)

        kind = MemoryKind(args.kind) if args.kind else MemoryKind.NOTE
        item = MemoryItem(
            project_id=pid,
            feature_id=fid,
            topic_id=tid,
            kind=kind,
            content=text,
            importance=float(args.importance) if args.importance else 0.5,
        )
        mid = store.add_memory_item(item)
        print(f"  Memory added: #{mid}")

    elif args.memory_cmd == "search":
        query = args.query or args.query_or_text or args.text
        pid = _resolve_project_id(store, args.project or "")
        results = store.search(query, project_id=pid, limit=args.limit)
        if not results:
            print("  No results.")
            return
        for r in results:
            print(f"  [{r.item.id}] {r.item.kind.value} (score={r.score:.2f}): {r.item.content[:100]}")

    elif args.memory_cmd == "stats":
        s = store.stats()
        print(json.dumps(s, indent=2))

    elif args.memory_cmd == "list":
        if not args.project:
            projects = store.list_projects()
            if not projects:
                print("  No projects.")
                return
            for p in projects:
                print(f"  [{p['id']}] {p['slug']} - {p['name']}")
        else:
            proj = store.get_project(args.project)
            if not proj:
                print(f"  Project '{args.project}' not found")
                return
            items = store.list_by_project(proj["id"])
            if not items:
                print("  No memories.")
                return
            for i in items:
                print(f"  [{i.id}] {i.kind.value}: {i.content[:80]}")

    elif args.memory_cmd == "tree":
        if not args.project:
            print("ERROR: --project required", file=sys.stderr)
            sys.exit(1)
        tree = tools.get_tree(args.project)
        print(json.dumps(tree, indent=2))

    elif args.memory_cmd == "export":
        if not args.project:
            print("ERROR: --project required", file=sys.stderr)
            sys.exit(1)
        proj = store.get_project(args.project)
        pid = proj["id"] if proj else args.project
        out = args.output or "./obsidian-export"
        files = export_to_obsidian(store, out, project_id=pid)
        print(f"  Exported {len(files)} files to {out}")
        for fp in files:
            print(f"    {fp}")

    elif args.memory_cmd == "build-pack":
        if not args.project or not args.agent:
            print("ERROR: --project and --agent required", file=sys.stderr)
            sys.exit(1)
        pack = tools.build_pack(
            agent_id=args.agent,
            task=args.task or "general",
            project_id=args.project,
            token_budget=args.limit * 200 if args.limit else 4000,
        )
        if pack["items"]:
            print(f"  Pack for {args.agent}: {len(pack['items'])} items, ~{pack['total_tokens_estimate']} tokens")
            for item in pack["items"]:
                print(f"    - {item['title']} ({item['source']})")
        else:
            print("  Empty pack")

    elif args.memory_cmd == "candidates":
        pid = _resolve_project_id(store, args.project or "")
        candidates = store.list_candidates(pid)
        if not candidates:
            print("  No candidates.")
            return
        for c in candidates:
            print(f"  [{c['id']}] {c['kind']}: {c['content'][:80]} (by {c['source_agent']})")

    elif args.memory_cmd == "commit-candidate":
        if not args.id:
            print("ERROR: --id required", file=sys.stderr)
            sys.exit(1)
        item_id = tools.commit_candidate(args.id, actor=args.actor)
        print(f"  Candidate committed: {item_id}")

    elif args.memory_cmd == "reject-candidate":
        if not args.id:
            print("ERROR: --id required", file=sys.stderr)
            sys.exit(1)
        tools.reject_candidate(args.id, reason=args.reason, actor=args.actor)
        print(f"  Candidate rejected: {args.id}")

    elif args.memory_cmd == "forget":
        if not args.id:
            print("ERROR: --id required", file=sys.stderr)
            sys.exit(1)
        tools.forget(args.id, actor=args.actor)
        print(f"  Memory archived: {args.id}")

    elif args.memory_cmd == "audit":
        log = store.get_audit_log(args.limit)
        for e in log:
            print(f"  [{e['action']}] by {e['actor']} -> {e['target_id']} | {e['details']}")

    store.close()



def cmd_registry(args):
    """Registry operations."""
    reg_path = args.registry or "AGENT-REGISTRY.yaml"
    reg = AgentRegistry(reg_path)
    try:
        reg.load()
        agents = reg.get_agents_by_phase(args.phase) if args.phase else [reg.get_agent(aid) for aid in reg.agent_ids]
        agents = [agent for agent in agents if agent]
        print(f"  Loaded {len(agents)} agents:")
        for agent in agents[:20]:
            print(f"    - {agent['id']}: {agent.get('role', 'no role')}")
        if len(agents) > 20:
            print(f"    ... and {len(agents) - 20} more")
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(1)



def main():
    parser = argparse.ArgumentParser("synto", description="Multi-agent AI orchestration system")
    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="Run a task through the orchestrator")
    p_run.add_argument("task", help="Task description")
    p_run.add_argument("--project", default="", help="Project name")
    p_run.add_argument("--config-dir", default="", help="Path to config directory")
    p_run.add_argument("--memory-db", default="memory_store.db", help="Path to memory database")
    p_run.set_defaults(func=cmd_run)

    # memory
    p_mem = sub.add_parser("memory", help="Memory operations")
    p_mem.add_argument("memory_cmd", choices=[
        "init", "add", "search", "stats", "list", "tree", "export",
        "build-pack", "candidates", "commit-candidate", "reject-candidate", "forget", "audit",
    ])
    p_mem.add_argument("query_or_text", nargs="?", default="", help="Text content or search query")
    p_mem.add_argument("--project", default="", help="Project name/slug")
    p_mem.add_argument("--feature", default="", help="Feature name/slug")
    p_mem.add_argument("--topic", default="", help="Topic name/slug")
    p_mem.add_argument("--text", default="", help="Memory content (for add)")
    p_mem.add_argument("--query", default="", help="Search query (for search)")
    p_mem.add_argument("--kind", default="", help="Memory kind (decision, fact, config, etc.)")
    p_mem.add_argument("--agent", default="", help="Agent ID (for build-pack)")
    p_mem.add_argument("--task", default="", help="Task context (for build-pack)")
    p_mem.add_argument("--importance", default="", help="Importance 0-1 (for add)")
    p_mem.add_argument("--output", default="", help="Output dir (for export)")
    p_mem.add_argument("--limit", type=int, default=20, help="Limit (for search/audit or pack budget multiplier)")
    p_mem.add_argument("--id", default="", help="Memory/candidate ID (for forget/commit/reject)")
    p_mem.add_argument("--reason", default="", help="Reason (for reject-candidate)")
    p_mem.add_argument("--actor", default="cli", help="Actor name for audit entries")
    p_mem.add_argument("--db", default="memory_store.db", help="Database path")
    p_mem.set_defaults(func=cmd_memory)

    # registry
    p_reg = sub.add_parser("registry", help="Agent registry operations")
    p_reg.add_argument("--registry", default="", help="Path to AGENT-REGISTRY.yaml")
    p_reg.add_argument("--phase", default="", help="Filter registry by phase")
    p_reg.set_defaults(func=cmd_registry)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
