"""File-based memory loading and consolidation checks for HW6."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / "AGENT.md"
MEMORY_PATH = ROOT / "MEMORY.md"


def load_memory_files() -> tuple[str, str]:
    """Load durable agent instructions and conversation facts."""
    agent = AGENT_PATH.read_text(encoding="utf-8")
    memory = MEMORY_PATH.read_text(encoding="utf-8")
    return agent, memory


def build_file_memory_context() -> str:
    """Construct file-based instructions for the model prompt."""
    agent, memory = load_memory_files()

    return (
        f"AGENT FILE INSTRUCTIONS:\n{agent.strip()}\n\n"
        f"DURABLE FILE MEMORY:\n{memory.strip()}"
    )


def read_last_consolidated(memory: str) -> datetime | None:
    """Read the UTC timestamp from MEMORY.md metadata."""
    match = re.search(
        r"<!--\s*last_consolidated:\s*(.*?)\s*-->",
        memory,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    value = match.group(1).strip()
    if value.lower() == "never":
        return None

    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError("Consolidation timestamp needs a timezone")

    return timestamp.astimezone(timezone.utc)


def count_memory_lines(memory: str) -> int:
    """Count non-empty lines, excluding HTML comments."""
    without_comments = re.sub(
        r"<!--.*?-->",
        "",
        memory,
        flags=re.DOTALL,
    )

    return sum(
        1
        for line in without_comments.splitlines()
        if line.strip()
    )


def check_consolidation(
    memory: str,
    now: datetime | None = None,
) -> dict:
    """Check the 40-line and 24-hour consolidation rules."""
    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("Current time needs a timezone")

    last = read_last_consolidated(memory)
    line_count = count_memory_lines(memory)

    over_line_limit = line_count > 40
    timestamp_missing = last is None

    older_than_24_hours = (
        False
        if last is None
        else now - last > timedelta(hours=24)
    )

    required = (
        over_line_limit
        or timestamp_missing
        or older_than_24_hours
    )

    return {
        "non_comment_lines": line_count,
        "last_consolidated": last.isoformat() if last else None,
        "over_40_lines": over_line_limit,
        "timestamp_missing_or_never": timestamp_missing,
        "older_than_24_hours": older_than_24_hours,
        "consolidation_required": required,
    }
