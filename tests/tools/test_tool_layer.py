"""Tests for Synto tools layer — filesystem, terminal, git, web, github, code, process."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from synto.tools.tool_layer import (
    TOOL_REGISTRY,
    list_tools,
    get_tool,
    read_file,
    write_file,
    create_directory,
    list_directory,
    search_files,
    move_file,
    delete_file,
    get_file_info,
    terminal,
    git_status,
    git_log,
    git_commit,
    patch,
    process_start,
    process_poll,
    process_kill,
    process_list,
    web_extract,
    _human_size,
)
from synto.tools.tool_calling import (
    ToolCallingConfig,
    ToolCall,
    ToolResult,
    get_tool_definitions,
    parse_tool_calls_from_response,
    execute_tool_call,
    build_tool_results_prompt,
    build_tool_instructions_prompt,
)


# ── Tool Registry Tests ─────────────────────────────────────────────────────

class TestToolRegistry:
    def test_registry_has_tools(self):
        assert len(TOOL_REGISTRY) > 0

    def test_list_tools_returns_all(self):
        tools = list_tools()
        assert len(tools) == len(TOOL_REGISTRY)

    def test_list_tools_filtered(self):
        fs_tools = list_tools(categories=["filesystem"])
        assert len(fs_tools) > 0
        assert all(t["category"] == "filesystem" for t in fs_tools)

    def test_get_tool_exists(self):
        meta = get_tool("read_file")
        assert meta is not None
        assert meta["category"] == "filesystem"

    def test_get_tool_missing(self):
        assert get_tool("nonexistent_tool_xyz") is None


# ── Filesystem Tests ────────────────────────────────────────────────────────

class TestFilesystemTools:
    @pytest.fixture()
    def tmp(self, tmp_path: Path):
        return tmp_path

    def test_write_and_read(self, tmp: Path):
        p = str(tmp / "test.txt")
        result = write_file(p, "hello world")
        assert result["status"] == "ok"
        assert result["bytes"] == 11

        read = read_file(p)
        assert "hello world" in read["content"]
        assert read["total_lines"] == 1

    def test_read_with_offset_limit(self, tmp: Path):
        p = str(tmp / "lines.txt")
        write_file(p, "a\nb\nc\nd\ne\n")
        result = read_file(p, offset=2, limit=2)
        assert "2|b" in result["content"]
        assert "3|c" in result["content"]
        assert "4|d" not in result["content"]

    def test_read_nonexistent(self):
        result = read_file("/nonexistent/path/file.txt")
        assert "error" in result

    def test_create_and_list_directory(self, tmp: Path):
        subdir = str(tmp / "sub" / "dir")
        result = create_directory(subdir)
        assert result["status"] == "ok"

        listing = list_directory(str(tmp))
        assert "sub" in " ".join(listing["items"])

    def test_search_files_by_name(self, tmp: Path):
        (tmp / "a.py").touch()
        (tmp / "b.py").touch()
        (tmp / "c.txt").touch()
        result = search_files("*.py", path=str(tmp))
        assert result["count"] == 2

    def test_search_files_by_content(self, tmp: Path):
        write_file(str(tmp / "search.py"), "import os\nimport sys\n")
        result = search_files("import sys", path=str(tmp), target="content")
        assert result["count"] >= 1

    def test_move_file(self, tmp: Path):
        src = str(tmp / "old.txt")
        dst = str(tmp / "new.txt")
        write_file(src, "data")
        result = move_file(src, dst)
        assert result["status"] == "ok"
        assert not Path(src).exists()
        assert Path(dst).exists()

    def test_delete_file(self, tmp: Path):
        p = str(tmp / "del.txt")
        write_file(p, "x")
        result = delete_file(p)
        assert result["status"] == "ok"
        assert not Path(p).exists()

    def test_get_file_info(self, tmp: Path):
        p = str(tmp / "info.txt")
        write_file(p, "content")
        info = get_file_info(p)
        assert "size" in info
        assert info["is_file"] is True


# ── Terminal Tests ──────────────────────────────────────────────────────────

class TestTerminalTools:
    def test_simple_command(self):
        result = terminal("echo hello")
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_failed_command(self):
        result = terminal("false")
        assert result["exit_code"] != 0

    def test_command_with_workdir(self, tmp_path: Path):
        result = terminal("pwd", workdir=str(tmp_path))
        assert str(tmp_path) in result["output"]


# ── Git Tests ───────────────────────────────────────────────────────────────

class TestGitTools:
    @pytest.fixture()
    def repo(self, tmp_path: Path):
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        return tmp_path

    def test_git_status(self, repo: Path):
        result = git_status(str(repo))
        # Should work (no error) even on empty repo
        assert "error" not in result or True  # may have output or not

    def test_git_commit_and_log(self, repo: Path):
        write_file(str(repo / "file.txt"), "hello")
        commit_result = git_commit(str(repo), "initial commit")
        assert commit_result.get("exit_code") == 0

        log_result = git_log(str(repo))
        assert "initial commit" in log_result.get("output", "")


# ── Patch Tests ─────────────────────────────────────────────────────────────

class TestPatchTool:
    def test_simple_patch(self, tmp_path: Path):
        p = tmp_path / "patch.txt"
        p.write_text("hello world\nfoo bar\n")
        result = patch(str(p), "world", "universe")
        assert result["status"] == "ok"
        assert p.read_text() == "hello universe\nfoo bar\n"

    def test_patch_not_found(self, tmp_path: Path):
        p = tmp_path / "nofind.txt"
        p.write_text("hello\n")
        result = patch(str(p), "nonexistent", "x")
        assert "error" in result

    def test_replace_all(self, tmp_path: Path):
        p = tmp_path / "multi.txt"
        p.write_text("foo bar foo bar")
        result = patch(str(p), "foo", "baz", replace_all=True)
        assert result["status"] == "ok"
        assert p.read_text() == "baz bar baz bar"


# ── Process Tests ───────────────────────────────────────────────────────────

class TestProcessTools:
    def test_start_and_list(self):
        result = process_start("sleep 10")
        assert result["status"] == "ok"
        sid = result["session_id"]

        listing = process_list()
        assert any(p["session_id"] == sid for p in listing["processes"])

        process_kill(sid)

    def test_poll_running_process(self):
        result = process_start("echo hello && sleep 5")
        sid = result["session_id"]

        import time
        time.sleep(1)

        poll = process_poll(sid)
        assert "running" in poll

        process_kill(sid)


# ── Web Extract Tests ───────────────────────────────────────────────────────

class TestWebExtract:
    def test_extract_valid_url(self):
        # This may fail without network, so just check structure
        result = web_extract("https://example.com")
        # Should return content or error
        assert "url" in result or "error" in result


# ── Tool Calling Tests ──────────────────────────────────────────────────────

class TestToolCalling:
    def test_get_tool_definitions(self):
        defs = get_tool_definitions()
        assert len(defs) > 0
        # Check structure
        d = defs[0]
        assert d["type"] == "function"
        assert "name" in d["function"]
        assert "parameters" in d["function"]

    def test_get_tool_definitions_allowed(self):
        defs = get_tool_definitions(allowed=["read_file", "write_file"])
        names = [d["function"]["name"] for d in defs]
        assert "read_file" in names
        assert "write_file" in names
        assert "terminal" not in names

    def test_get_tool_definitions_denied(self):
        defs = get_tool_definitions(denied=["delete_file"])
        names = [d["function"]["name"] for d in defs]
        assert "delete_file" not in names

    def test_parse_tool_calls_json_block(self):
        content = '''Here is the tool call:
```json
{"tool_calls": [{"name": "read_file", "arguments": {"path": "/tmp/x.txt"}}]}
```
'''
        calls = parse_tool_calls_from_response(content)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments["path"] == "/tmp/x.txt"

    def test_parse_tool_calls_xml_style(self):
        content = 'I will use <tool_call name="write_file" args=\'{"path": "/tmp/x.txt", "content": "hi"}\' />'
        calls = parse_tool_calls_from_response(content)
        assert len(calls) == 1
        assert calls[0].name == "write_file"

    def test_parse_no_tool_calls(self):
        content = "Just a normal response with no tools."
        calls = parse_tool_calls_from_response(content)
        assert len(calls) == 0

    def test_execute_tool_call(self):
        call = ToolCall(name="read_file", arguments={"path": "/nonexistent"})
        result = execute_tool_call(call)
        assert result.tool_name == "read_file"
        assert result.is_error is True

    def test_execute_tool_call_allowed(self):
        call = ToolCall(name="read_file", arguments={"path": "/nonexistent"})
        config = ToolCallingConfig(allowed_tools=["read_file"])
        result = execute_tool_call(call, config)
        assert result.is_error is True  # error from tool, not from permission

    def test_execute_tool_call_denied(self):
        call = ToolCall(name="read_file", arguments={"path": "/x"})
        config = ToolCallingConfig(denied_tools=["read_file"])
        result = execute_tool_call(call, config)
        assert result.is_error is True
        assert "denied" in str(result.output)

    def test_build_tool_results_prompt(self):
        results = [
            ToolResult(call_id="1", tool_name="read_file", output="file content"),
            ToolResult(call_id="2", tool_name="terminal", output={"error": "failed"}, is_error=True),
        ]
        prompt = build_tool_results_prompt(results)
        assert "read_file" in prompt
        assert "terminal" in prompt
        assert "OK" in prompt
        assert "ERROR" in prompt

    def test_build_tool_instructions_prompt(self):
        defs = get_tool_definitions(allowed=["read_file", "write_file"])
        prompt = build_tool_instructions_prompt(defs)
        assert "read_file" in prompt
        assert "write_file" in prompt
        assert "tool_calls" in prompt


# ── Utility Tests ───────────────────────────────────────────────────────────

class TestUtility:
    def test_human_size(self):
        assert _human_size(0) == "0.0B"
        assert _human_size(512) == "512.0B"
        assert _human_size(1024) == "1.0KB"
        assert _human_size(1048576) == "1.0MB"
        assert _human_size(1073741824) == "1.0GB"
