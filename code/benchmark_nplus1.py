import csv
import time
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:8081"

PAGE_SIZES = [10, 50, 200]
RUNS_PER_SIZE = 30

EMAIL = "test@example.com"
PASSWORD = "Test123!"

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "reports"
    / "hw04"
    / "raw"
    / "nplus1_naive.csv"
)


def percentile(values, percentile_value):
    values = sorted(values)

    index = (len(values) - 1) * percentile_value / 100
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)

    weight = index - lower

    return (
        values[lower] * (1 - weight)
        + values[upper] * weight
    )


def main():
    session = requests.Session()

    # Log in once so the session cookie is reused.
    login_response = session.post(
        f"{BASE_URL}/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    login_response.raise_for_status()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for page_size in PAGE_SIZES:
        latencies = []
        query_counts = []

        for run_number in range(1, RUNS_PER_SIZE + 1):
            start_time = time.perf_counter()

            response = session.get(
                f"{BASE_URL}/records/part3/nplus1",
                params={
                    "page_size": page_size,
                },
            )

            latency_ms = (
                time.perf_counter() - start_time
            ) * 1000

            response.raise_for_status()

            query_count = int(
                response.headers["X-SQL-Query-Count"]
            )

            latencies.append(latency_ms)
            query_counts.append(query_count)

            rows.append(
                {
                    "version": "naive",
                    "page_size": page_size,
                    "run": run_number,
                    "query_count": query_count,
                    "latency_ms": latency_ms,
                }
            )

        print(f"Page size: {page_size}")
        print(
            "Queries per request: "
            f"{min(query_counts)}-{max(query_counts)}"
        )
        print(
            "p50 latency: "
            f"{percentile(latencies, 50):.2f} ms"
        )
        print(
            "p95 latency: "
            f"{percentile(latencies, 95):.2f} ms"
        )
        print(
            "p99 latency: "
            f"{percentile(latencies, 99):.2f} ms"
        )
        print()

    with OUTPUT_FILE.open(
        "w",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "version",
                "page_size",
                "run",
                "query_count",
                "latency_ms",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Saved {len(rows)} raw requests to:"
    )
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()