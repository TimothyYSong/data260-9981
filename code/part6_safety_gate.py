"""DATA 260 HW7 Part 6: Independent Bash command safety gate."""

import re
import shlex


SAFE_PREFIXES = (
    "pwd",
    "ls",
    "echo",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "python --version",
    "python3 --version",
)


def is_destructive(command: str) -> bool:
    """Detect prohibited or potentially destructive shell operations."""
    if not isinstance(command, str) or not command.strip():
        return False

    patterns = (
        r"\brm\s+(?:-[\w]*r[\w]*\s+|--recursive\b)",
        r"\bsudo\b|\bsu\b|\bdoas\b",
        r"\bchmod\b|\bchown\b|\bchgrp\b",
        r"\b(?:dd|shred)\b",
        r"\b(?:mkdir|mkfs(?:\.\w+)?|diskutil\s+erase\w*|newfs(?:_\w+)?)\b",
        r">\s*/(?:[^\s]*)",
    )

    return any(
        re.search(pattern, command, flags=re.IGNORECASE)
        for pattern in patterns
    )


def confirm_bash(command: str, auto_approve: bool = False) -> dict:
    """Return an allow/block decision without executing the command."""
    if not isinstance(command, str) or not command.strip():
        return {"allowed": False, "reason": "Empty or invalid command."}

    if is_destructive(command):
        if not auto_approve:
            return {
                "allowed": False,
                "reason": "Destructive command requires explicit confirmation.",
            }
        return {
            "allowed": True,
            "reason": "Destructive command explicitly confirmed.",
        }

    try:
        tokens = shlex.split(command)
    except ValueError:
        return {"allowed": False, "reason": "Invalid shell syntax."}

    if not tokens:
        return {"allowed": False, "reason": "No executable provided."}

    safe = any(
        tokens[0] == prefix.split()[0]
        and tokens[:len(prefix.split())] == prefix.split()
        for prefix in SAFE_PREFIXES
    )

    if not safe:
        return {
            "allowed": False,
            "reason": "Command is not in SAFE_PREFIXES.",
        }

    # Block shell operators until an explicit, sandboxed execution policy
    # is implemented by the bash tool.
    if re.search(r"[;&|<>`$\n]", command):
        return {
            "allowed": False,
            "reason": "Shell operators or expansions are not permitted.",
        }

    return {
        "allowed": True,
        "reason": "Command matches SAFE_PREFIXES.",
    }
