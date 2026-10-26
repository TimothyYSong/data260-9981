import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from agent import LOG_FILE, run_agent  # noqa: E402


RAW = ROOT / "reports/hw07/raw"
CASES = RAW / "verification_cases.json"


def get_events(run_id):
    if not LOG_FILE.exists():
        return []

    events = []
    with LOG_FILE.open(encoding="utf-8") as file:
        for line in file:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("run_id") == run_id:
                events.append(item)
    return events


def verify_chain(case, history):
    expected = case["expected_tools"]
    names = [item["tool"] for item in history]

    if names != expected:
        return False

    if not all(
        item["result"].get("ok") is True
        for item in history
    ):
        return False

    search_data = history[0]["result"].get("data") or []
    if not search_data:
        return False

    if case["case_id"] == "A":
        return (
            history[1]["inputs"].get("inspection_id")
            == search_data[0]["id"]
        )

    if case["case_id"] == "B":
        return (
            history[1]["inputs"].get("restaurant_id")
            == search_data[0]["restaurant_id"]
            and history[2]["inputs"].get("inspection_id")
            == search_data[0]["id"]
        )

    if case["case_id"] == "C":
        if len(search_data) < 2:
            return False
        actual = [
            history[1]["inputs"].get("inspection_id"),
            history[2]["inputs"].get("inspection_id"),
        ]
        expected_ids = [
            search_data[0]["id"],
            search_data[1]["id"],
        ]
        return actual == expected_ids

    return False


def classify(events, result, passed):
    failures = []

    for event in events:
        kind = event.get("event")

        if kind == "invalid_tool_call":
            failures.append("malformed_arguments")

        elif kind == "tool_validation_failed":
            problem = str(event.get("problem", "")).lower()
            if "unknown tool" in problem:
                failures.append("unknown_tool")
            else:
                failures.append("malformed_arguments")

        elif kind == "text_without_tool":
            failures.append("text_when_tool_required")

    if not passed:
        if result["stop_reason"] == "model_error":
            failures.append("model_error")
        elif (
            result["tool_calls"] > 0
            or result["stop_reason"] == "normal_completion"
        ):
            failures.append("lost_multi_step_chain")
        elif not failures:
            failures.append("lost_multi_step_chain")

    return sorted(set(failures))


def run_one(case, trial, mode):
    repairs = 0 if mode == "before" else 1

    result = run_agent(
        case["question"],
        max_steps=8,
        max_repairs=repairs,
    )

    events = get_events(result["run_id"])
    history = result["history"]

    chain_ok = verify_chain(case, history)
    passed = (
        chain_ok
        and bool(result.get("answer"))
        and result["stop_reason"] == "normal_completion"
    )

    invalid_count = sum(
        event.get("event") in (
            "invalid_tool_call",
            "tool_validation_failed",
        )
        for event in events
    )

    valid_count = sum(
        not item.get("validation_error", False)
        for item in history
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case["case_id"],
        "trial": trial,
        "mode": mode,
        "model": "qwen3:8b",
        "temperature": 0.0,
        "max_steps": 8,
        "max_repairs": repairs,
        "run_id": result["run_id"],
        "tool_sequence": [item["tool"] for item in history],
        "tool_calls": result["tool_calls"],
        "valid_calls": valid_count,
        "invalid_calls": invalid_count,
        "repair_attempts": result["repairs"],
        "stop_reason": result["stop_reason"],
        "task_success": passed,
        "failure_types": classify(events, result, passed),
        "answer": result.get("answer"),
        "error": result.get("error"),
    }


def summarize(records):
    summary = {}

    for mode in ("before", "after"):
        rows = [row for row in records if row["mode"] == mode]
        valid = sum(row["valid_calls"] for row in rows)
        invalid = sum(row["invalid_calls"] for row in rows)
        total = valid + invalid
        successes = sum(row["task_success"] for row in rows)

        failures = Counter()
        for row in rows:
            failures.update(row["failure_types"])

        summary[mode] = {
            "attempts": len(rows),
            "task_successes": successes,
            "task_success_rate": (
                successes / len(rows) if rows else None
            ),
            "valid_tool_calls": valid,
            "invalid_tool_calls": invalid,
            "well_formed_call_rate": (
                valid / total if total else None
            ),
            "failure_classification": dict(failures),
        }

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=1)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.pairs < 1:
        parser.error("--pairs must be at least 1")

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    prefix = "smoke_" if args.smoke else ""

    jsonl_path = RAW / f"{prefix}part2_reliability.jsonl"
    csv_path = RAW / f"{prefix}part2_reliability.csv"
    summary_path = RAW / f"{prefix}part2_summary.json"

    records = []

    # Same fixed task and model settings for each paired comparison.
    # Only the permitted repair count changes.
    with jsonl_path.open("w", encoding="utf-8") as file:
        for trial in range(1, args.pairs + 1):
            for case in cases:
                for mode in ("before", "after"):
                    row = run_one(case, trial, mode)
                    records.append(row)

                    file.write(
                        json.dumps(row, ensure_ascii=False) + "\n"
                    )
                    file.flush()

                    status = (
                        "PASS" if row["task_success"] else "FAIL"
                    )
                    print(
                        f"Task {row['case_id']} "
                        f"trial {trial} {mode}: {status} "
                        f"| calls={row['tool_calls']} "
                        f"| errors={row['failure_types']}",
                        flush=True,
                    )

    columns = [
        key for key in records[0]
        if key not in ("answer", "error")
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for row in records:
            writer.writerow(
                {
                    key: json.dumps(row[key])
                    if isinstance(row[key], (list, dict))
                    else row[key]
                    for key in columns
                }
            )

    summary = summarize(records)
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== RELIABILITY SUMMARY ===")
    print(json.dumps(summary, indent=2))

    print("\nSaved:")
    print(jsonl_path.relative_to(ROOT))
    print(csv_path.relative_to(ROOT))
    print(summary_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
