"""DATA 260 HW7 Part 6: Sandbox-restricted file tools."""

import json
from pathlib import Path


def get_sandbox() -> Path:
    """Load the temporary course sandbox from saved metadata."""
    metadata = Path(
        "reports/hw07/raw/part6_sandbox_metadata.json"
    )
    data = json.loads(metadata.read_text(encoding="utf-8"))

    sandbox = Path(data["sandbox_path"]).resolve(strict=True)

    if not sandbox.is_dir():
        raise ValueError("Sandbox directory is unavailable.")

    if not sandbox.name.startswith("data260_hw07_part6_"):
        raise ValueError("Invalid course sandbox.")

    return sandbox


def safe_path(path: str) -> Path:
    """Resolve a path and prevent access outside the sandbox."""
    sandbox = get_sandbox()
    candidate = Path(path)

    if not candidate.is_absolute():
        candidate = sandbox / candidate

    resolved = candidate.resolve()

    if not resolved.is_relative_to(sandbox):
        raise PermissionError("Path is outside the course sandbox.")

    return resolved


def read_file(path: str, max_lines: int = 100) -> dict:
    """Read up to max_lines from a sandboxed text file."""
    if isinstance(max_lines, bool) or not isinstance(max_lines, int):
        raise ValueError("max_lines must be an integer.")

    if not 1 <= max_lines <= 1000:
        raise ValueError("max_lines must be between 1 and 1000.")

    target = safe_path(path)

    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target.name}")

    with target.open("r", encoding="utf-8") as stream:
        lines = []
        for _ in range(max_lines):
            line = stream.readline()
            if not line:
                break
            lines.append(line)

    return {
        "path": str(target),
        "content": "".join(lines),
        "lines_returned": len(lines),
        "max_lines": max_lines,
    }


def write_file(path: str, content: str) -> dict:
    """Write a UTF-8 text file inside the course sandbox."""
    if not isinstance(content, str):
        raise ValueError("content must be a string.")

    target = safe_path(path)

    if target.exists() and not target.is_file():
        raise ValueError("Target is not a regular file.")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return {
        "path": str(target),
        "success": True,
        "bytes_written": len(content.encode("utf-8")),
    }


def edit_file(path: str, old_text: str, new_text: str) -> dict:
    """Replace one exact text occurrence and return a short unified diff."""
    import difflib

    if not isinstance(old_text, str) or not old_text:
        raise ValueError("old_text must be a nonempty string.")
    if not isinstance(new_text, str):
        raise ValueError("new_text must be a string.")

    target = safe_path(path)

    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target.name}")

    original = target.read_text(encoding="utf-8")
    matches = original.count(old_text)

    if matches != 1:
        raise ValueError(
            f"Expected exactly one matching occurrence; found {matches}."
        )

    updated = original.replace(old_text, new_text, 1)

    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{target.name}",
            tofile=f"b/{target.name}",
            n=2,
        )
    )

    target.write_text(updated, encoding="utf-8")

    return {
        "success": True,
        "path": str(target),
        "replacements": 1,
        "diff": "".join(diff_lines[:30]),
    }


def glob_files(pattern: str = "*.py") -> dict:
    """Find matching files inside the temporary course sandbox."""
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("pattern must be a nonempty string.")

    sandbox = get_sandbox()

    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        raise PermissionError("Glob pattern must stay inside the sandbox.")

    matches = []

    for candidate in sandbox.glob(pattern):
        resolved = candidate.resolve()

        if resolved.is_relative_to(sandbox) and resolved.is_file():
            matches.append(str(resolved.relative_to(sandbox)))

    matches = sorted(set(matches))

    return {
        "pattern": pattern,
        "files": matches,
        "count": len(matches),
    }


def search_in_files(query: str, file_pattern: str = "**/*.py") -> dict:
    """Search matching sandbox files and return matching lines."""
    if not isinstance(query, str) or not query:
        raise ValueError("query must be a nonempty string.")

    candidates = glob_files(file_pattern)["files"]
    matches = []

    for relative_path in candidates:
        target = safe_path(relative_path)

        try:
            with target.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if query in line:
                        matches.append({
                            "file": relative_path,
                            "line_number": line_number,
                            "text": line.rstrip("\r\n"),
                        })
        except UnicodeDecodeError:
            continue

    return {
        "query": query,
        "file_pattern": file_pattern,
        "matches": matches,
        "match_count": len(matches),
    }


def bash(command: str, auto_approve: bool = False) -> dict:
    """Run approved read-only commands inside the course sandbox."""
    import shlex
    import subprocess

    from part6_safety_gate import confirm_bash

    decision = confirm_bash(command, auto_approve=auto_approve)

    if not decision["allowed"]:
        return {
            "success": False,
            "blocked": True,
            "reason": decision["reason"],
        }

    # The bash execution layer is intentionally more restrictive
    # than the confirmation gate.
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {
            "success": False,
            "blocked": True,
            "reason": "Invalid command syntax.",
        }

    supported = {"pwd", "ls", "echo", "cat", "head", "tail", "grep"}

    if not tokens or tokens[0] not in supported:
        return {
            "success": False,
            "blocked": True,
            "reason": "Command unsupported by sandbox execution policy.",
        }

    if any(c in command for c in (";", "&", "|", "<", ">", "`", "$", "\n")):
        return {
            "success": False,
            "blocked": True,
            "reason": "Shell operators are prohibited.",
        }

    # No absolute paths or traversal components may be passed.
    for arg in tokens[1:]:
        if arg.startswith("/") or ".." in Path(arg).parts:
            return {
                "success": False,
                "blocked": True,
                "reason": "Absolute paths and traversal are prohibited.",
            }

    try:
        result = subprocess.run(
            tokens,
            cwd=str(get_sandbox()),
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "success": False,
            "blocked": False,
            "reason": str(exc),
        }

    return {
        "success": result.returncode == 0,
        "blocked": False,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
