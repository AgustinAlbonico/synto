"""Synto MCP Server — expone todas las herramientas como MCP tools.

Este server combina las herramientas de tool_layer con las de memoria
en un único servidor MCP que los agentes pueden usar.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from fastmcp import FastMCP

from synto.tools.tool_layer import (
    TOOL_REGISTRY,
    create_directory,
    delete_file,
    execute_tool,
    get_file_info,
    list_directory,
    move_file,
    patch,
    process_kill,
    process_list,
    process_poll,
    process_start,
    read_file,
    search_files,
    terminal,
    web_extract,
    web_search,
    write_file,
    git_status,
    git_diff,
    git_log,
    git_branch,
    git_checkout,
    git_commit,
    git_push,
    git_clone,
    github_search_code,
    github_search_issues,
    github_get_file_contents,
    github_create_issue,
    github_create_pull_request,
)

# ── MCP Server ─────────────────────────────────────────────────────────────

mcp = FastMCP("synto-tools", version="1.0.0")


# Filesystem tools

@mcp.tool()
def read_file_tool(path: str, offset: int = 1, limit: int = 500) -> dict[str, Any]:
    """Read a text file with line numbers. Use offset/limit for large files."""
    return read_file(path, offset=offset, limit=limit)


@mcp.tool()
def write_file_tool(path: str, content: str) -> dict[str, Any]:
    """Write content to a file. Creates parent directories if needed. Overwrites."""
    return write_file(path, content=content)


@mcp.tool()
def create_directory_tool(path: str) -> dict[str, Any]:
    """Create a directory, including parent directories."""
    return create_directory(path)


@mcp.tool()
def list_directory_tool(path: str) -> dict[str, Any]:
    """List files and directories in a path. Returns [FILE]/[DIR] prefixed names."""
    return list_directory(path)


@mcp.tool()
def search_files_tool(
    pattern: str,
    path: str = ".",
    target: str = "files",
    file_glob: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search for files by glob pattern or content regex. target='files' or 'content'."""
    return search_files(pattern, path=path, target=target, file_glob=file_glob, limit=limit)


@mcp.tool()
def move_file_tool(source: str, destination: str) -> dict[str, Any]:
    """Move or rename a file or directory."""
    return move_file(source, destination)


@mcp.tool()
def delete_file_tool(path: str) -> dict[str, Any]:
    """Delete a file or empty directory."""
    return delete_file(path)


@mcp.tool()
def get_file_info_tool(path: str) -> dict[str, Any]:
    """Get file metadata: size, permissions, modification time."""
    return get_file_info(path)


# Terminal tools

@mcp.tool()
def terminal_tool(command: str, workdir: str = "", timeout: int = 60) -> dict[str, Any]:
    """Execute a shell command. Returns output and exit code."""
    return terminal(command, workdir=workdir or None, timeout=timeout)


# Git tools

@mcp.tool()
def git_status_tool(path: str = ".") -> dict[str, Any]:
    """Get git status of a repository."""
    return git_status(path)


@mcp.tool()
def git_diff_tool(path: str = ".", args: str = "") -> dict[str, Any]:
    """Show git diff. Use '--cached' for staged changes."""
    return git_diff(path, args=args)


@mcp.tool()
def git_log_tool(path: str = ".", limit: int = 20, oneline: bool = True) -> dict[str, Any]:
    """Show git commit history."""
    return git_log(path, limit=limit, oneline=oneline)


@mcp.tool()
def git_branch_tool(path: str = ".", args: str = "") -> dict[str, Any]:
    """List git branches."""
    return git_branch(path, args=args)


@mcp.tool()
def git_checkout_tool(path: str, branch: str, create: bool = False) -> dict[str, Any]:
    """Switch to a branch or commit. create=True to make new branch."""
    return git_checkout(path, branch, create=create)


@mcp.tool()
def git_commit_tool(path: str, message: str, files: str = "-A") -> dict[str, Any]:
    """Stage and commit changes."""
    return git_commit(path, message, files=files)


@mcp.tool()
def git_push_tool(path: str, remote: str = "origin", branch: str = "") -> dict[str, Any]:
    """Push changes to remote."""
    return git_push(path, remote=remote, branch=branch)


@mcp.tool()
def git_clone_tool(url: str, path: str, depth: int = 0) -> dict[str, Any]:
    """Clone a git repository. depth>0 for shallow clone."""
    return git_clone(url, path, depth=depth)


# Web tools

@mcp.tool()
def web_search_tool(query: str, limit: int = 5) -> dict[str, Any]:
    """Search the web. Returns results with title, URL, description."""
    return web_search(query, limit=limit)


@mcp.tool()
def web_extract_tool(url: str) -> dict[str, Any]:
    """Extract text content from a web page URL."""
    return web_extract(url)


# GitHub tools

@mcp.tool()
def github_search_code_tool(query: str, limit: int = 30) -> dict[str, Any]:
    """Search code on GitHub. Requires GITHUB_TOKEN env var for best results."""
    return github_search_code(query, limit=limit)


@mcp.tool()
def github_search_issues_tool(query: str, limit: int = 30) -> dict[str, Any]:
    """Search issues/PRs on GitHub."""
    return github_search_issues(query, limit=limit)


@mcp.tool()
def github_get_file_contents_tool(
    owner: str, repo: str, path: str, branch: str = "",
) -> dict[str, Any]:
    """Get file contents from a GitHub repository."""
    return github_get_file_contents(owner, repo, path, branch=branch)


@mcp.tool()
def github_create_issue_tool(
    owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a GitHub issue."""
    return github_create_issue(owner, repo, title, body=body, labels=labels)


@mcp.tool()
def github_create_pull_request_tool(
    owner: str, repo: str, title: str, head: str, base: str,
    body: str = "", draft: bool = False,
) -> dict[str, Any]:
    """Create a GitHub pull request."""
    return github_create_pull_request(owner, repo, title, head, base, body=body, draft=draft)


# Code tools

@mcp.tool()
def patch_tool(path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
    """Targeted find-and-replace in a file. old_string must be unique unless replace_all=True."""
    return patch(path, old_string, new_string, replace_all=replace_all)


# Process tools

@mcp.tool()
def process_start_tool(command: str, workdir: str = "") -> dict[str, Any]:
    """Start a background process. Returns session_id for management."""
    return process_start(command, workdir=workdir)


@mcp.tool()
def process_poll_tool(session_id: str) -> dict[str, Any]:
    """Check status and get output from a background process."""
    return process_poll(session_id)


@mcp.tool()
def process_kill_tool(session_id: str) -> dict[str, Any]:
    """Kill a background process."""
    return process_kill(session_id)


@mcp.tool()
def process_list_tool() -> dict[str, Any]:
    """List all background processes."""
    return process_list()


# Memory tools (import from existing memory server)

try:
    from synto.mcp.memory_tools import MemoryToolLayer
    from synto.memory.store import MemoryStore

    _store = None

    def _get_store() -> MemoryStore:
        global _store
        db_path = os.environ.get("HERMES_MEMORY_DB", "memory_store.db")
        if _store is None or str(_store.db_path) != db_path:
            if _store is not None:
                try:
                    _store.close()
                except Exception:
                    pass
            _store = MemoryStore(db_path)
        return _store

    def _get_tools() -> MemoryToolLayer:
        return MemoryToolLayer(_get_store())

    @mcp.tool()
    def memory_search(query: str, project_id: str = "", limit: int = 20) -> list[dict]:
        """Full-text search across memory items."""
        return _get_tools().search(query=query, project_id=project_id, limit=limit)

    @mcp.tool()
    def memory_get_item(memory_id: str) -> dict | None:
        """Get a specific memory item by ID."""
        return _get_tools().get_item(memory_id)

    @mcp.tool()
    def memory_get_tree(project_id: str) -> dict:
        """Return the project -> feature -> topic tree."""
        return _get_tools().get_tree(project_id)

    @mcp.tool()
    def memory_build_pack(agent_id: str, task: str, project_id: str, token_budget: int = 4000) -> dict:
        """Build a bounded memory pack for an agent and task."""
        return _get_tools().build_pack(agent_id=agent_id, task=task, project_id=project_id, token_budget=token_budget)

    @mcp.tool()
    def memory_add_candidate(
        project_id: str, content: str, source_agent: str = "", kind: str = "note",
        title: str = "", reasoning: str = "", feature_id: str = "", topic_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Add a memory candidate for review."""
        return _get_tools().add_candidate(
            project_id=project_id, content=content, source_agent=source_agent,
            kind=kind, title=title, reasoning=reasoning, feature_id=feature_id,
            topic_id=topic_id, tags=tags,
        )

    @mcp.tool()
    def memory_list_candidates(project_id: str = "") -> list[dict]:
        """List pending memory candidates."""
        return _get_tools().list_candidates(project_id=project_id)

    @mcp.tool()
    def memory_commit_candidate(candidate_id: str) -> str:
        """Commit a memory candidate to permanent memory."""
        return _get_tools().commit_candidate(candidate_id)

    @mcp.tool()
    def memory_reject_candidate(candidate_id: str, reason: str = "") -> str:
        """Reject a memory candidate."""
        return _get_tools().reject_candidate(candidate_id, reason=reason)

except ImportError:
    pass  # Memory tools optional


def run_server(transport: str = "stdio", port: int = 8765):
    """Run the MCP server."""
    if transport == "stdio":
        mcp.run()
    elif transport == "sse":
        mcp.run(transport="sse", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synto MCP Tools Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(transport=args.transport, port=args.port)
