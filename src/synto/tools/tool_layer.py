"""Synto Tools — capa de herramientas para agentes autónomos.

Cada herramienta es una función con type hints y docstring que describe
su propósito, parámetros y retorno. Los agentes pueden usarlas via
tool calling con el LLM.

Categorías:
- filesystem: leer, escribir, buscar, listar, mover, borrar
- terminal: ejecutar comandos, procesos background
- git: status, diff, commit, push, branch, log
- web: buscar, extraer contenido
- browser: navegar, hacer click, tipear, screenshots
- github: issues, PRs, code search
- code: buscar código, aplicar patches
- process: gestionar procesos background
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# ── Types ───────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(name: str, category: str, description: str, parameters: dict):
    """Decorator para registrar una herramienta en el registry."""
    def decorator(fn):
        fn._tool_meta = {
            "name": name,
            "category": category,
            "description": description,
            "parameters": parameters,
        }
        TOOL_REGISTRY[name] = fn._tool_meta
        return fn
    return decorator


def list_tools(categories: list[str] | None = None) -> list[dict[str, Any]]:
    """Listar todas las herramientas disponibles, opcionalmente filtradas por categoría."""
    tools = []
    for name, meta in TOOL_REGISTRY.items():
        if categories is None or meta["category"] in categories:
            tools.append({
                "name": name,
                "category": meta["category"],
                "description": meta["description"],
                "parameters": meta["parameters"],
            })
    return tools


def get_tool(name: str) -> dict[str, Any] | None:
    """Obtener metadata de una herramienta por nombre."""
    return TOOL_REGISTRY.get(name)


def execute_tool(name: str, **kwargs) -> Any:
    """Ejecutar una herramienta por nombre con los argumentos dados."""
    # Import dynamically to avoid circular imports
    import synto.tools.tool_layer as tl
    fn = getattr(tl, name, None)
    if fn is None:
        raise ValueError(f"Tool '{name}' not found")
    return fn(**kwargs)


# ── Filesystem Tools ────────────────────────────────────────────────────────

@register_tool(
    "read_file", "filesystem",
    "Read a text file with line numbers and pagination. Use offset and limit for large files.",
    {
        "path": {"type": "string", "description": "Absolute path to the file"},
        "offset": {"type": "integer", "description": "Starting line number (1-indexed)", "default": 1},
        "limit": {"type": "integer", "description": "Maximum lines to read", "default": 500},
    }
)
def read_file(path: str, offset: int = 1, limit: int = 500) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}", "content": ""}
    if not p.is_file():
        return {"error": f"Not a file: {path}", "content": ""}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        start = max(0, offset - 1)
        end = min(start + limit, total)
        chunk = lines[start:end]
        numbered = [f"{i+1}|{line}" for i, line in enumerate(chunk, start=start)]
        return {
            "content": "\n".join(numbered),
            "total_lines": total,
            "offset": offset,
            "limit": limit,
            "showing": f"lines {start+1}-{end} of {total}",
        }
    except Exception as e:
        return {"error": str(e), "content": ""}


@register_tool(
    "write_file", "filesystem",
    "Write content to a file, creating parent directories if needed. Overwrites existing files.",
    {
        "path": {"type": "string", "description": "Absolute path to the file"},
        "content": {"type": "string", "description": "Content to write"},
    }
)
def write_file(path: str, content: str) -> dict[str, Any]:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": str(p), "bytes": len(content)}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@register_tool(
    "create_directory", "filesystem",
    "Create a directory, including parent directories if needed.",
    {
        "path": {"type": "string", "description": "Absolute path to the directory"},
    }
)
def create_directory(path: str) -> dict[str, Any]:
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "path": str(p)}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@register_tool(
    "list_directory", "filesystem",
    "List files and directories in a path. Returns names with [FILE] or [DIR] prefix.",
    {
        "path": {"type": "string", "description": "Directory path to list"},
    }
)
def list_directory(path: str) -> dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        if not p.is_dir():
            return {"error": f"Not a directory: {path}"}
        items = []
        for entry in sorted(p.iterdir()):
            prefix = "[DIR]" if entry.is_dir() else "[FILE]"
            size = _human_size(entry.stat().st_size) if entry.is_file() else ""
            items.append(f"{prefix} {entry.name} {size}".strip())
        return {"path": str(p), "items": items, "count": len(items)}
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "search_files", "filesystem",
    "Search for files by glob pattern (e.g., '*.py') or search content inside files with regex.",
    {
        "pattern": {"type": "string", "description": "Glob pattern for file search or regex for content search"},
        "path": {"type": "string", "description": "Directory to search in (default: current directory)"},
        "target": {"type": "string", "enum": ["files", "content"], "description": "Search for files by name or content", "default": "files"},
        "file_glob": {"type": "string", "description": "Filter by file extension (e.g., '*.py') when searching content"},
        "limit": {"type": "integer", "description": "Maximum results", "default": 50},
    }
)
def search_files(
    pattern: str,
    path: str = ".",
    target: str = "files",
    file_glob: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    try:
        root = Path(path)
        if target == "files":
            matches = list(root.rglob(pattern))[:limit]
            return {
                "matches": [str(m) for m in matches],
                "count": len(matches),
                "total_found": len(list(root.rglob(pattern))) if len(matches) < limit else f">{limit}",
            }
        else:
            import re
            results = []
            regex = re.compile(pattern)
            for f in root.rglob(file_glob or "*"):
                if not f.is_file():
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            results.append({"file": str(f), "line": i, "content": line.strip()})
                            if len(results) >= limit:
                                break
                except Exception:
                    pass
                if len(results) >= limit:
                    break
            return {"matches": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "move_file", "filesystem",
    "Move or rename a file or directory.",
    {
        "source": {"type": "string", "description": "Source path"},
        "destination": {"type": "string", "description": "Destination path"},
    }
)
def move_file(source: str, destination: str) -> dict[str, Any]:
    try:
        s = Path(source)
        d = Path(destination)
        if not s.exists():
            return {"error": f"Source not found: {source}"}
        d.parent.mkdir(parents=True, exist_ok=True)
        s.rename(d)
        return {"status": "ok", "source": str(s), "destination": str(d)}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@register_tool(
    "delete_file", "filesystem",
    "Delete a file or empty directory.",
    {
        "path": {"type": "string", "description": "Path to delete"},
    }
)
def delete_file(path: str) -> dict[str, Any]:
    try:
        p = Path(path)
        if p.is_dir():
            p.rmdir()
        else:
            p.unlink()
        return {"status": "ok", "path": path}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@register_tool(
    "get_file_info", "filesystem",
    "Get metadata about a file or directory: size, permissions, modification time.",
    {
        "path": {"type": "string", "description": "Path to inspect"},
    }
)
def get_file_info(path: str) -> dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        stat = p.stat()
        return {
            "path": str(p),
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
            "size": stat.st_size,
            "size_human": _human_size(stat.st_size),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Terminal Tools ──────────────────────────────────────────────────────────

@register_tool(
    "terminal", "terminal",
    "Execute a shell command. Returns output and exit code. Use background=True for long-running processes.",
    {
        "command": {"type": "string", "description": "Shell command to execute"},
        "workdir": {"type": "string", "description": "Working directory (default: current)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)", "default": 60},
    }
)
def terminal(command: str, workdir: str | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        return {
            "output": output[:50000],  # Cap output
            "exit_code": result.returncode,
            "truncated": len(output) > 50000,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "exit_code": -1}


# ── Git Tools ───────────────────────────────────────────────────────────────

@register_tool(
    "git_status", "git",
    "Get the current git status of a repository.",
    {
        "path": {"type": "string", "description": "Repository path (default: current directory)"},
    }
)
def git_status(path: str = ".") -> dict[str, Any]:
    return terminal(f"git -C {shlex.quote(path)} status --short --branch")


@register_tool(
    "git_diff", "git",
    "Show git diff. Use --cached for staged changes, or specify files.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "args": {"type": "string", "description": "Additional git diff arguments (e.g., '--cached', 'file.py')", "default": ""},
    }
)
def git_diff(path: str = ".", args: str = "") -> dict[str, Any]:
    return terminal(f"git -C {shlex.quote(path)} diff {args}")


@register_tool(
    "git_log", "git",
    "Show git commit history.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "limit": {"type": "integer", "description": "Number of commits to show", "default": 20},
        "oneline": {"type": "boolean", "description": "Show one-line format", "default": True},
    }
)
def git_log(path: str = ".", limit: int = 20, oneline: bool = True) -> dict[str, Any]:
    fmt = "--oneline" if oneline else "--format='%H %s (%ar)'"
    return terminal(f"git -C {shlex.quote(path)} log -{limit} {fmt}")


@register_tool(
    "git_branch", "git",
    "List git branches. Use '-a' for all branches.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "args": {"type": "string", "description": "Additional arguments", "default": ""},
    }
)
def git_branch(path: str = ".", args: str = "") -> dict[str, Any]:
    return terminal(f"git -C {shlex.quote(path)} branch {args}")


@register_tool(
    "git_checkout", "git",
    "Switch to a branch or commit.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "branch": {"type": "string", "description": "Branch name or commit hash"},
        "create": {"type": "boolean", "description": "Create branch if it doesn't exist (-b flag)", "default": False},
    }
)
def git_checkout(path: str, branch: str, create: bool = False) -> dict[str, Any]:
    flag = "-b" if create else ""
    return terminal(f"git -C {shlex.quote(path)} checkout {flag} {shlex.quote(branch)}")


@register_tool(
    "git_commit", "git",
    "Stage and commit changes.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "message": {"type": "string", "description": "Commit message"},
        "files": {"type": "string", "description": "Files to stage (default: all with git add -A)", "default": "-A"},
    }
)
def git_commit(path: str, message: str, files: str = "-A") -> dict[str, Any]:
    result = terminal(f"git -C {shlex.quote(path)} add {files}")
    if result.get("exit_code", 0) != 0:
        return result
    return terminal(f"git -C {shlex.quote(path)} commit -m {shlex.quote(message)}")


@register_tool(
    "git_push", "git",
    "Push changes to remote.",
    {
        "path": {"type": "string", "description": "Repository path"},
        "remote": {"type": "string", "description": "Remote name", "default": "origin"},
        "branch": {"type": "string", "description": "Branch name (default: current)", "default": ""},
    }
)
def git_push(path: str, remote: str = "origin", branch: str = "") -> dict[str, Any]:
    cmd = f"git -C {shlex.quote(path)} push {shlex.quote(remote)}"
    if branch:
        cmd += f" {shlex.quote(branch)}"
    return terminal(cmd)


@register_tool(
    "git_clone", "git",
    "Clone a git repository.",
    {
        "url": {"type": "string", "description": "Repository URL"},
        "path": {"type": "string", "description": "Destination directory"},
        "depth": {"type": "integer", "description": "Clone depth (for shallow clone)", "default": 0},
    }
)
def git_clone(url: str, path: str, depth: int = 0) -> dict[str, Any]:
    cmd = f"git clone {shlex.quote(url)} {shlex.quote(path)}"
    if depth > 0:
        cmd += f" --depth {depth}"
    return terminal(cmd)


# ── Web Tools ───────────────────────────────────────────────────────────────

@register_tool(
    "web_search", "web",
    "Search the web for information. Returns results with titles, URLs, and descriptions.",
    {
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "description": "Number of results", "default": 5},
    }
)
def web_search(query: str, limit: int = 5) -> dict[str, Any]:
    # Use a simple web search via DuckDuckGo or similar
    try:
        # Try SearXNG first if available
        try:
            resp = httpx.get(
                "http://localhost:8080/search",
                params={"q": query, "format": "json", "results": limit},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for r in data.get("results", [])[:limit]:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("content", "")[:200],
                    })
                return {"results": results, "count": len(results)}
        except Exception:
            pass
        # Fallback: DuckDuckGo HTML scrape
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if resp.status_code == 200:
            # Simple HTML parsing
            import re
            html = resp.text
            results = []
            for match in re.finditer(
                r'class="result__title">.*?<a[^>]+href="([^"]+)".*?>(.*?)</a>.*?class="result__snippet">(.*?)</span>',
                html, re.DOTALL
            ):
                url = match.group(1)
                title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()[:200]
                results.append({"title": title, "url": url, "description": snippet})
                if len(results) >= limit:
                    break
            return {"results": results, "count": len(results)}
        return {"error": f"Search failed with status {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "web_extract", "web",
    "Extract content from a web page URL. Returns page content as text.",
    {
        "url": {"type": "string", "description": "URL to extract content from"},
    }
)
def web_extract(url: str) -> dict[str, Any]:
    try:
        resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            return {"error": f"Failed to fetch: {resp.status_code}"}
        # Simple HTML to text
        import re
        html = resp.text
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return {
            "url": url,
            "title": _extract_title(html),
            "content": text[:10000],
            "truncated": len(text) > 10000,
        }
    except Exception as e:
        return {"error": str(e)}


def _extract_title(html: str) -> str:
    import re
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return ""


# ── GitHub Tools ────────────────────────────────────────────────────────────

@register_tool(
    "github_search_code", "github",
    "Search for code across GitHub repositories.",
    {
        "query": {"type": "string", "description": "GitHub code search query (e.g., 'express language:javascript')"},
        "limit": {"type": "integer", "description": "Results per page (max 100)", "default": 30},
    }
)
def github_search_code(query: str, limit: int = 30) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = httpx.get(
            "https://api.github.com/search/code",
            params={"q": query, "per_page": limit},
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            return {"error": f"GitHub API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        items = []
        for item in data.get("items", [])[:limit]:
            items.append({
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "repository": item.get("repository", {}).get("full_name", ""),
                "url": item.get("html_url", ""),
            })
        return {"results": items, "total_count": data.get("total_count", 0), "count": len(items)}
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "github_search_issues", "github",
    "Search for issues and pull requests across GitHub repositories.",
    {
        "query": {"type": "string", "description": "GitHub issue search query"},
        "limit": {"type": "integer", "description": "Results per page", "default": 30},
    }
)
def github_search_issues(query: str, limit: int = 30) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = httpx.get(
            "https://api.github.com/search/issues",
            params={"q": query, "per_page": limit},
            headers=headers,
            timeout=30,
        )
        if resp.status_code != 200:
            return {"error": f"GitHub API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        items = []
        for item in data.get("items", [])[:limit]:
            items.append({
                "title": item.get("title", ""),
                "url": item.get("html_url", ""),
                "state": item.get("state", ""),
                "created_at": item.get("created_at", ""),
                "repository": item.get("repository_url", "").split("/repos/")[-1] if "/repos/" in item.get("repository_url", "") else "",
            })
        return {"results": items, "total_count": data.get("total_count", 0), "count": len(items)}
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "github_get_file_contents", "github",
    "Get the contents of a file from a GitHub repository.",
    {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "path": {"type": "string", "description": "File path in repository"},
        "branch": {"type": "string", "description": "Branch name (default: main)", "default": ""},
    }
)
def github_get_file_contents(owner: str, repo: str, path: str, branch: str = "") -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        if branch:
            url += f"?ref={branch}"
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {"error": f"GitHub API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        import base64
        content = base64.b64decode(data.get("content", "")).decode("utf-8") if data.get("content") else ""
        return {
            "path": path,
            "content": content,
            "sha": data.get("sha", ""),
            "size": data.get("size", 0),
        }
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "github_create_issue", "github",
    "Create a new issue in a GitHub repository.",
    {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "title": {"type": "string", "description": "Issue title"},
        "body": {"type": "string", "description": "Issue body/description"},
        "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to add"},
    }
)
def github_create_issue(owner: str, repo: str, title: str, body: str = "", labels: list[str] | None = None) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = httpx.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            return {"error": f"GitHub API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        return {
            "status": "ok",
            "issue_number": data.get("number"),
            "url": data.get("html_url"),
            "title": data.get("title"),
        }
    except Exception as e:
        return {"error": str(e)}


@register_tool(
    "github_create_pull_request", "github",
    "Create a new pull request in a GitHub repository.",
    {
        "owner": {"type": "string", "description": "Repository owner"},
        "repo": {"type": "string", "description": "Repository name"},
        "title": {"type": "string", "description": "PR title"},
        "body": {"type": "string", "description": "PR body/description"},
        "head": {"type": "string", "description": "Source branch name"},
        "base": {"type": "string", "description": "Target branch name"},
        "draft": {"type": "boolean", "description": "Create as draft PR", "default": False},
    }
)
def github_create_pull_request(
    owner: str, repo: str, title: str, head: str, base: str,
    body: str = "", draft: bool = False,
) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        payload = {"title": title, "head": head, "base": base, "body": body, "draft": draft}
        resp = httpx.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            return {"error": f"GitHub API error: {resp.status_code}", "detail": resp.text[:500]}
        data = resp.json()
        return {
            "status": "ok",
            "pr_number": data.get("number"),
            "url": data.get("html_url"),
            "title": data.get("title"),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Code Tools ──────────────────────────────────────────────────────────────

@register_tool(
    "patch", "code",
    "Targeted find-and-replace edit in a file. Replaces old_string with new_string.",
    {
        "path": {"type": "string", "description": "File path to edit"},
        "old_string": {"type": "string", "description": "Text to find (must be unique in file)"},
        "new_string": {"type": "string", "description": "Replacement text"},
        "replace_all": {"type": "boolean", "description": "Replace all occurrences", "default": False},
    }
)
def patch(path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        content = p.read_text(encoding="utf-8")
        if old_string not in content:
            return {"error": "old_string not found in file"}
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        diff = _generate_diff(old_string, new_string)
        return {"status": "ok", "path": path, "diff": diff}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def _generate_diff(old: str, new: str) -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff = []
    for line in old_lines[:3]:
        diff.append(f"- {line}")
    diff.append("---")
    for line in new_lines[:3]:
        diff.append(f"+ {line}")
    return "\n".join(diff)


# ── Process Tools ───────────────────────────────────────────────────────────

@dataclass
class ProcessInfo:
    session_id: str
    command: str
    pid: int | None = None
    running: bool = True
    workdir: str = ""


_processes: dict[str, dict[str, Any]] = {}


@register_tool(
    "process_start", "process",
    "Start a background process. Returns a session_id for managing it.",
    {
        "command": {"type": "string", "description": "Command to run"},
        "workdir": {"type": "string", "description": "Working directory"},
    }
)
def process_start(command: str, workdir: str = "") -> dict[str, Any]:
    import uuid
    session_id = str(uuid.uuid4())[:8]
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=workdir or None,
        )
        _processes[session_id] = {
            "process": proc,
            "command": command,
            "workdir": workdir,
            "pid": proc.pid,
            "running": True,
            "output": "",
        }
        return {"status": "ok", "session_id": session_id, "pid": proc.pid, "command": command}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@register_tool(
    "process_poll", "process",
    "Check status and get new output from a background process.",
    {
        "session_id": {"type": "string", "description": "Process session ID"},
    }
)
def process_poll(session_id: str) -> dict[str, Any]:
    info = _processes.get(session_id)
    if not info:
        return {"error": f"Process not found: {session_id}"}
    proc = info["process"]
    # Read non-blocking output
    output = ""
    if proc.stdout:
        import select
        import fcntl
        # Set non-blocking
        fd = proc.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            ready, _, _ = select.select([proc.stdout], [], [], 0.5)
            if ready:
                output = proc.stdout.read(4096) or ""
        except Exception:
            pass
    if output:
        info["output"] += output
    running = proc.poll() is None
    info["running"] = running
    return {
        "session_id": session_id,
        "running": running,
        "exit_code": proc.returncode if not running else None,
        "new_output": output,
        "total_output_length": len(info["output"]),
    }


@register_tool(
    "process_kill", "process",
    "Kill a background process.",
    {
        "session_id": {"type": "string", "description": "Process session ID"},
    }
)
def process_kill(session_id: str) -> dict[str, Any]:
    info = _processes.get(session_id)
    if not info:
        return {"error": f"Process not found: {session_id}"}
    proc = info["process"]
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    info["running"] = False
    return {"status": "ok", "session_id": session_id, "exit_code": proc.returncode}


@register_tool(
    "process_list", "process",
    "List all background processes.",
    {}
)
def process_list() -> dict[str, Any]:
    processes = []
    for sid, info in _processes.items():
        proc = info["process"]
        processes.append({
            "session_id": sid,
            "command": info["command"],
            "running": proc.poll() is None,
            "pid": info.get("pid"),
        })
    return {"processes": processes, "count": len(processes)}


# ── Utility ─────────────────────────────────────────────────────────────────

def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"
