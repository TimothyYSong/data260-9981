import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agent import run_agent
from claim_checker import check_unsupported_claims
from reflexion_agent import run_reflexion
from reflexion_verifier import verify_task

ROOT = Path(__file__).resolve().parents[1]


RAW = ROOT / "reports/hw07/raw"
CASES = json.loads(
    (RAW / "verification_cases.json").read_text(encoding="utf-8")
)

TRIALS = 3
ROWS = []


def execute(case, mode, trial):
    start = time.perf_counter()

    if mode == "original":
        result = run_agent(case["question"])
        attempts = [result]
        verification = verify_task(case, result)
        retries = 0
        tool_calls = result["tool_calls"]
        tokens = result["total_tokens"]
        stop_reason = result["stop_reason"]
        run_id = result["run_id"]

    else:
        result = run_reflexion(case)
        attempts = [
            attempt["agent_result"]
            for attempt in result["attempts"]
        ]
        verification = (
            result["attempts"][-1]["verification"]
            if result["attempts"]
            else {"passed": False, "failures": []}
        )
        retries = result["retry_count"]
        tool_calls = result["total_tool_calls"]
        tokens = result["total_tokens"]
        stop_reason = result["stop_reason"]
        run_id = result["reflexion_run_id"]

    latency_ms = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    claims = [
        check_unsupported_claims(attempt)
        for attempt in attempts
    ]

    unsupported = sum(
        item["unsupported_claim_count"]
        for item in claims
    )

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case["case_id"],
        "trial": trial,
        "mode": mode,
        "run_id": run_id,
        "task_success": bool(verification["passed"]),
        "unsupported_claims": unsupported,
        "retry_count": retries,
        "tool_calls": tool_calls,
        "tokens": tokens,
        "latency_ms": latency_ms,
        "stop_reason": stop_reason,
        "verifier_failures": verification["failures"],
        "claim_checks": claims,
        "attempts": attempts,
    }

    return row


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    jsonl_path = RAW / "part3_comparison.jsonl"
    csv_path = RAW / "part3_comparison.csv"

    for output in (
        jsonl_path,
        csv_path,
        RAW / "part3_summary.json",
    ):
        if output.exists():
            raise FileExistsError(
                f"Existing comparison output: {output}. "
                "Review or archive it before rerunning."
            )

    for trial in range(1, TRIALS + 1):
        for case in CASES:
            for mode in ("original", "reflexion"):
                print(
                    f"Running trial={trial} "
                    f"task={case['case_id']} mode={mode}",
                    flush=True,
                )

                row = execute(case, mode, trial)
                ROWS.append(row)

                with jsonl_path.open(
                    "a", encoding="utf-8"
                ) as file:
                    file.write(
                        json.dumps(row, default=str) + "\n"
                    )

                print(
                    f"  Success={row['task_success']} "
                    f"Retries={row['retry_count']} "
                    f"Tools={row['tool_calls']} "
                    f"Tokens={row['tokens']} "
                    f"Latency={row['latency_ms']}ms",
                    flush=True,
                )

    fields = [
        "timestamp",
        "case_id",
        "trial",
        "mode",
        "run_id",
        "task_success",
        "unsupported_claims",
        "retry_count",
        "tool_calls",
        "tokens",
        "latency_ms",
        "stop_reason",
    ]

    with csv_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )
        writer.writeheader()
        for row in ROWS:
            writer.writerow({
                key: row[key]
                for key in fields
            })

    summary = {}

    for mode in ("original", "reflexion"):
        rows = [
            row for row in ROWS
            if row["mode"] == mode
        ]

        count = len(rows)

        summary[mode] = {
            "executions": count,
            "task_success_rate": sum(
                row["task_success"] for row in rows
            ) / count,
            "unsupported_claims": sum(
                row["unsupported_claims"]
                for row in rows
            ),
            "retry_rate": sum(
                row["retry_count"] > 0
                for row in rows
            ) / count,
            "mean_tool_calls": sum(
                row["tool_calls"] for row in rows
            ) / count,
            "mean_tokens": sum(
                row["tokens"] for row in rows
            ) / count,
            "mean_latency_ms": sum(
                row["latency_ms"] for row in rows
            ) / count,
        }

    (RAW / "part3_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n=== PART 3 COMPARISON SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("\nSTEP 5K: COMPLETE")


if __name__ == "__main__":
    main()
