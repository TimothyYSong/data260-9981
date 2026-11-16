"""HW10: 50 verified semantic-cache misses with Kafka stage timings."""

import csv
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "hw10"
TRACE_FILE = REPORT_DIR / "traces.jsonl"
API_URL = "http://127.0.0.1:8082/api/hw10/ask"

TARGET = 50
MAX_ATTEMPTS = 65
RUN_ID = uuid4().hex[:10]

STAGES = [
    "cache_lookup",
    "inbox_publish",
    "planner",
    "writer",
    "reviewer",
    "final_response_wait",
    "cache_store",
]

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return round(
        values[lower]
        + (values[upper] - values[lower])
        * (position - lower),
        3,
    )


def load_spans():
    records = []
    with TRACE_FILE.open(encoding="utf-8") as file:
        for line in file:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def send_request(attempt):
    payload = {
        "question": (
            "Retrieve inspection details for inspection 10023."
        ),
        "threshold": 0.95,
        "data_version": f"hw10_bench_{RUN_ID}_{attempt}",
        "evaluate": False,
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=35) as response:
        body = json.loads(response.read().decode("utf-8"))
    client_ms = (time.perf_counter() - started) * 1000

    return body, client_ms, payload


def main():
    successful = []
    failures = []
    started_at = datetime.now(timezone.utc).isoformat()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if len(successful) == TARGET:
            break

        try:
            response, client_ms, payload = send_request(attempt)

            trace_id = response["trace_id"]
            spans = [
                span for span in load_spans()
                if span.get("trace_id") == trace_id
            ]

            by_stage = defaultdict(list)
            for span in spans:
                by_stage[span["stage"]].append(span)

            assert response.get("is_cached") is False, (
                "Response was a cache hit"
            )
            assert response.get("reviewer_status") == "approved"
            assert "Inspection details for ID 10023" in response["answer"]
            assert all(
                len(by_stage[stage]) == 1
                for stage in STAGES
            ), "Missing or duplicate stage spans"
            assert len(by_stage["queue_wait"]) == 3, (
                "Expected three queue-wait spans"
            )
            assert len(by_stage["evaluation"]) == 0, (
                "GEval should be disabled"
            )
            assert all(
                span["status"] == "success"
                for span in spans
            ), "Unsuccessful trace span"
            assert by_stage["cache_lookup"][0].get(
                "cache_result"
            ) == "miss"

            queue_by_consumer = {
                span["consumer_stage"]: span["duration_ms"]
                for span in by_stage["queue_wait"]
            }

            assert set(queue_by_consumer) == {
                "planner", "writer", "reviewer"
            }

            stage_ms = {
                stage: by_stage[stage][0]["duration_ms"]
                for stage in STAGES
            }

            row = {
                "number": len(successful) + 1,
                "attempt": attempt,
                "trace_id": trace_id,
                "data_version": payload["data_version"],
                "api_latency_ms": response["latency_ms"],
                "client_latency_ms": round(client_ms, 3),
                "queue_wait_total_ms": round(
                    sum(queue_by_consumer.values()), 3
                ),
                **{
                    f"{stage}_ms": duration
                    for stage, duration in stage_ms.items()
                },
                **{
                    f"queue_{consumer}_ms": duration
                    for consumer, duration
                    in queue_by_consumer.items()
                },
            }

            successful.append(row)
            print(
                f"{len(successful):02d}/{TARGET} PASS "
                f"API={row['api_latency_ms']:.2f}ms "
                f"queue={row['queue_wait_total_ms']:.2f}ms",
                flush=True,
            )

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            failures.append({
                "attempt": attempt,
                "error": error,
            })
            print(
                f"Attempt {attempt} FAILED: {error}",
                flush=True,
            )

        # Save progress even if the experiment is interrupted.
        (REPORT_DIR / "hw10_benchmark_progress.json").write_text(
            json.dumps({
                "run_id": RUN_ID,
                "successful": successful,
                "failures": failures,
            }, indent=2),
            encoding="utf-8",
        )

    if successful:
        csv_path = REPORT_DIR / "hw10_benchmark_50.csv"
        with csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=list(successful[0])
            )
            writer.writeheader()
            writer.writerows(successful)

    series = {
        "api_latency_ms": [
            row["api_latency_ms"] for row in successful
        ],
        "queue_wait_total_ms": [
            row["queue_wait_total_ms"] for row in successful
        ],
        **{
            f"{stage}_ms": [
                row[f"{stage}_ms"] for row in successful
            ]
            for stage in STAGES
        },
        **{
            f"queue_{name}_ms": [
                row[f"queue_{name}_ms"]
                for row in successful
            ]
            for name in ("planner", "writer", "reviewer")
        },
    }

    summary = {
        "run_id": RUN_ID,
        "started_at": started_at,
        "finished_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "target_confirmed_misses": TARGET,
        "confirmed_misses": len(successful),
        "failed_attempts": len(failures),
        "attempts": len(successful) + len(failures),
        "evaluation_executed": False,
        "workload": (
            "Same inspection question; distinct data_version "
            "per request to guarantee cold-cache misses"
        ),
        "timing_notes": (
            "Kafka queue waits use record timestamps. "
            "final_response_wait overlaps agent and queue "
            "spans, so stage durations must not all be summed."
        ),
        "statistics": {
            key: {
                "mean_ms": round(
                    statistics.mean(values), 3
                ) if values else None,
                "p50_ms": percentile(values, 50),
                "p95_ms": percentile(values, 95),
                "min_ms": round(min(values), 3)
                if values else None,
                "max_ms": round(max(values), 3)
                if values else None,
            }
            for key, values in series.items()
        },
        "queue_wait_percent_of_e2e": round(
            100 * sum(
                row["queue_wait_total_ms"]
                for row in successful
            ) / sum(
                row["api_latency_ms"]
                for row in successful
            ),
            3,
        ) if successful else None,
        "failures": failures,
    }

    summary_path = REPORT_DIR / "hw10_benchmark_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\n=== HW10 BENCHMARK SUMMARY ===")
    print("Confirmed misses:", len(successful))
    print("Failed attempts:", len(failures))
    print("Queue / E2E:", summary["queue_wait_percent_of_e2e"], "%")

    for name, values in summary["statistics"].items():
        print(
            f"{name:27s} "
            f"p50={values['p50_ms']} ms  "
            f"p95={values['p95_ms']} ms"
        )

    print("Saved:", summary_path)

    if len(successful) != TARGET:
        raise SystemExit(
            f"INCOMPLETE: {len(successful)}/{TARGET} "
            "confirmed misses"
        )

    print("PASS: All 50 cache misses verified")


if __name__ == "__main__":
    main()
