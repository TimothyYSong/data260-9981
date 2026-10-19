
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

METRICS_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "hw06"
    / "raw"
    / "memory_usage.jsonl"
)


def extract_section(prompt, start, end):
    """
    Extract a labeled section from the composed prompt.
    """
    if start not in prompt or end not in prompt:
        raise ValueError("Expected prompt section not found")

    return prompt.split(start, 1)[1].split(end, 1)[0]

def estimate_tokens(text):
    """
    Approximate section token count using four
    characters per token. These are estimates,
    not exact Qwen3 tokenizer measurements.
    """
    return math.ceil(len(text) / 4) if text else 0

def calculate_component_tokens(prompt):
    """
    Estimate the token contribution from each
    memory component in the existing prompt.
    """

    system = extract_section(
        prompt,
        "SYSTEM PRIMER:\n",
        "\n\nLIFETIME SUMMARY:\n",
    )

    long_term = extract_section(
        prompt,
        "LIFETIME SUMMARY:\n",
        "\n\nSHORT-TERM WINDOW:\n",
    )

    short_term = extract_section(
        prompt,
        "SHORT-TERM WINDOW:\n",
        "\n\nCURRENT USER MESSAGE:\n",
    )

    current_message = extract_section(
        prompt,
        "CURRENT USER MESSAGE:\n",
        "\n\nEPISODIC FACTS:\n",
    )

    episodic = extract_section(
        prompt,
        "EPISODIC FACTS:\n",
        "\n\nASSISTANT RESPONSE:",
    )

    return {
        "system_primer_tokens_est": estimate_tokens(system),
        "long_term_summary_tokens_est": estimate_tokens(long_term),
        "short_term_window_tokens_est": estimate_tokens(short_term),
        "current_message_tokens_est": estimate_tokens(current_message),
        "episodic_facts_tokens_est": estimate_tokens(episodic),
    }


def log_chat_usage(
    *,
    user_id,
    session_id,
    prompt,
    prompt_tokens,
    completion_tokens,
    latency_ms,
):
    """
    Append one memory-usage record per completed chat
    request to a machine-readable JSONL file.
    """

    components = calculate_component_tokens(prompt)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "model": "qwen3:8b",
        "experiment": os.getenv(
            "HW6_EXPERIMENT_NAME", "baseline"
        ),
        "short_term_n": int(os.getenv("SHORT_TERM_N", "12")),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        **components,
        "latency_ms": round(latency_ms, 2),
        "component_token_method": "estimated_chars_divided_by_4",
    }

    METRICS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with METRICS_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )

    return record
