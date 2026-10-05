import csv
import os
import random
import statistics
import time

from database import SessionLocal
from domain_server import run_with_retry
from models import RestaurantInspection


VERIFY_SEED = 269981

FAILURE_RATES = [0.0, 0.2, 0.5]
CALLS_PER_RATE = 50

RAW_DIR = "reports/hw05/raw"
RAW_FILE = os.path.join(
    RAW_DIR,
    "fault_injection_calls.csv",
)


def database_operation():
    db = SessionLocal()

    try:
        count = db.query(RestaurantInspection).count()

        return {
            "inspection_count": count,
        }

    finally:
        db.close()


def percentile_99(values):
    sorted_values = sorted(values)

    if not sorted_values:
        return 0.0

    index = int(0.99 * (len(sorted_values) - 1))

    return sorted_values[index]


def run_experiment():
    os.makedirs(RAW_DIR, exist_ok=True)

    all_records = []
    summary_rows = []

    print("Student: Timothy Song")
    print(f"VERIFY_SEED: {VERIFY_SEED}")
    print()

    for failure_rate in FAILURE_RATES:
        # Reset to exactly the same VERIFY_SEED for each rate.
        # This makes every rate reproducible independently.
        rng = random.Random(VERIFY_SEED)

        rate_records = []

        print(
            f"Running failure rate: "
            f"{int(failure_rate * 100)}%"
        )

        for call_number in range(1, CALLS_PER_RATE + 1):

            def failure_injector():
                return rng.random() < failure_rate

            start = time.perf_counter()

            result = run_with_retry(
                database_operation,
                max_attempts=3,
                timeout_seconds=2.0,
                base_delay=0.1,
                max_delay=0.5,
                failure_injector=failure_injector,
            )

            end = time.perf_counter()

            latency_ms = (end - start) * 1000

            record = {
                "verify_seed": VERIFY_SEED,
                "failure_rate": failure_rate,
                "call_number": call_number,
                "ok": result["ok"],
                "attempts": result["attempts"],
                "latency_ms": round(latency_ms, 3),
                "error": result["error"] or "",
            }

            all_records.append(record)
            rate_records.append(record)

        successes = sum(
            1 for record in rate_records
            if record["ok"]
        )

        success_rate = (
            successes / CALLS_PER_RATE
        ) * 100

        latencies = [
            record["latency_ms"]
            for record in rate_records
        ]

        mean_latency = statistics.mean(latencies)

        p99_latency = percentile_99(latencies)

        summary = {
            "failure_rate":
                f"{int(failure_rate * 100)}%",
            "success_rate":
                round(success_rate, 2),
            "mean_latency_ms":
                round(mean_latency, 3),
            "p99_latency_ms":
                round(p99_latency, 3),
        }

        summary_rows.append(summary)

        print(
            f"  Success rate: "
            f"{summary['success_rate']}%"
        )
        print(
            f"  Mean latency: "
            f"{summary['mean_latency_ms']} ms"
        )
        print(
            f"  p99 latency: "
            f"{summary['p99_latency_ms']} ms"
        )
        print()

    with open(
        RAW_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "verify_seed",
                "failure_rate",
                "call_number",
                "ok",
                "attempts",
                "latency_ms",
                "error",
            ],
        )

        writer.writeheader()
        writer.writerows(all_records)

    print(
        f"Saved {len(all_records)} raw call records "
        f"to {RAW_FILE}"
    )

    print()
    print("SUMMARY")
    print(
        "Failure Rate | Success Rate | "
        "Mean Latency (ms) | p99 Latency (ms)"
    )

    for row in summary_rows:
        print(
            f"{row['failure_rate']:>12} | "
            f"{row['success_rate']:>11}% | "
            f"{row['mean_latency_ms']:>17} | "
            f"{row['p99_latency_ms']:>16}"
        )


if __name__ == "__main__":
    run_experiment()