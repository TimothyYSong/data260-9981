
"""Commands for durable file-based memory."""

import re
from datetime import datetime, timezone
from pathlib import Path

from file_memory import MEMORY_PATH, count_memory_lines
from memory_store import episodes_collection


def consolidate_memory_file(
    path: Path = MEMORY_PATH,
) -> dict:
    """Merge duplicate facts and document conflicting values."""
    original = path.read_text(encoding="utf-8")
    before_lines = count_memory_lines(original)

    facts = []
    previous_resolutions = []
    in_resolutions = False

    for line in original.splitlines():
        text = line.strip()

        if text == "## Contradiction Resolutions":
            in_resolutions = True
            continue

        if text.startswith("## "):
            in_resolutions = False
            continue

        if not text or text.startswith("#"):
            continue

        if text.startswith("<!--"):
            continue

        if in_resolutions:
            previous_resolutions.append(text)
        elif text.startswith("- "):
            facts.append(text[2:].strip())
        else:
            facts.append(text)

    before_messages = len(facts)

    unique = []
    seen = set()
    keyed_positions = {}
    resolutions = list(previous_resolutions)
    duplicates_removed = 0
    contradictions_resolved = 0

    for fact in facts:
        normalized = " ".join(fact.lower().split())

        if normalized in seen:
            duplicates_removed += 1
            continue

        # Structured facts such as "priority_city: Oakland"
        # can be compared to detect contradictory values.
        match = re.fullmatch(
            r"([a-zA-Z][a-zA-Z0-9_ -]{1,40}):\s*(.+)",
            fact,
        )

        if match:
            key = match.group(1).strip().lower()

            if key in keyed_positions:
                index = keyed_positions[key]
                previous = unique[index]

                if previous.lower() != fact.lower():
                    resolutions.append(
                        f"Resolved {key}: '{previous}' -> "
                        f"'{fact}' (latest entry retained; "
                        "manual verification required)."
                    )
                    unique[index] = fact
                    contradictions_resolved += 1
                else:
                    duplicates_removed += 1

                seen.add(normalized)
                continue

            keyed_positions[key] = len(unique)

        unique.append(fact)
        seen.add(normalized)

    timestamp = datetime.now(timezone.utc).isoformat()

    def render(items):
        output = [
            "# MEMORY.md — Durable Conversation Facts",
            "",
            f"<!-- last_consolidated: {timestamp} -->",
            "",
            "## Remembered Facts",
            *[f"- {fact}" for fact in items],
        ]

        if resolutions:
            output.extend([
                "",
                "## Contradiction Resolutions",
                *resolutions,
            ])

        return "\n".join(output) + "\n"

    # If there are still 40 or more qualifying lines,
    # group adjacent facts while preserving their text.
    while count_memory_lines(render(unique)) >= 40:
        if len(unique) < 2:
            raise ValueError(
                "Unable to consolidate below 40 lines "
                "without removing resolution evidence."
            )

        first = unique.pop()
        second = unique.pop()

        unique.append(f"[Grouped] {second} | {first}")

    consolidated = render(unique)
    path.write_text(consolidated, encoding="utf-8")

    return {
        "message_count_before": before_messages,
        "message_count_after": len(unique),
        "line_count_before": before_lines,
        "line_count_after": count_memory_lines(consolidated),
        "duplicates_removed": duplicates_removed,
        "contradictions_resolved": contradictions_resolved,
    }


def append_dream_facts(
    facts: list[str],
    path: Path = MEMORY_PATH,
) -> int:
    """Append new durable facts without duplicating existing facts."""
    content = path.read_text(encoding="utf-8")
    existing = {
        line.strip()[2:].strip().casefold()
        for line in content.splitlines()
        if line.strip().startswith("- ")
    }

    additions = []

    for fact in facts:
        fact = " ".join(fact.strip().split())

        if not fact or fact.casefold() in existing:
            continue

        existing.add(fact.casefold())
        additions.append(f"- {fact}")

    if additions:
        if "## Dreamed Facts" not in content:
            content = content.rstrip() + "\n\n## Dreamed Facts\n"

        content += "\n".join(additions) + "\n"
        path.write_text(content, encoding="utf-8")

    return len(additions)


def handle_memory_command(
    command: str,
    user_id: str,
    path: Path = MEMORY_PATH,
) -> str | None:
    """Handle file-memory commands without invoking the model."""
    command = command.strip().lower()

    if command == "/help":
        return (
            "Available memory commands:\n"
            "/memory - Display durable file-based memory\n"
            "/compact - Consolidate facts and report counts\n"
            "/dream - Save useful conversation facts\n"
            "/help - Display available commands"
        )

    if command == "/memory":
        return path.read_text(encoding="utf-8")

    if command == "/compact":
        result = consolidate_memory_file(path)

        return (
            "Memory consolidation completed.\n"
            f"Message count before: "
            f"{result['message_count_before']}\n"
            f"Message count after: "
            f"{result['message_count_after']}\n"
            f"Non-comment lines before: "
            f"{result['line_count_before']}\n"
            f"Non-comment lines after: "
            f"{result['line_count_after']}\n"
            f"Duplicates removed: "
            f"{result['duplicates_removed']}\n"
            f"Contradictions documented: "
            f"{result['contradictions_resolved']}"
        )

    if command == "/dream":
        # Part 2 already extracts and stores episodic facts
        # from user conversations.
        episodes = list(
            episodes_collection.find(
                {"user_id": user_id},
                {"_id": 0, "fact": 1, "importance": 1},
            )
            .sort([("created_at", -1), ("_id", -1)])
            .limit(30)
        )

        useful_facts = [
            episode["fact"]
            for episode in episodes
            if episode.get("fact")
            and float(episode.get("importance", 0)) >= 0.6
        ][:5]

        added = append_dream_facts(useful_facts, path)

        return (
            "Dream completed.\n"
            f"Useful facts identified: {len(useful_facts)}\n"
            f"New durable facts added: {added}\n"
            "Memory file: MEMORY.md"
        )

    return None
