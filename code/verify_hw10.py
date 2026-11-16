"""HW10 objective smoke test; does not modify application code."""

import csv
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "hw10"
API = "http://127.0.0.1:8082/api/hw10/ask"

checks = []


def check(name, condition, detail=""):
    passed = bool(condition)
    checks.append({
        "name": name,
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "detail": str(detail),
    })
    print(f"{'PASS' if passed else 'FAIL'}: {name}", flush=True)


def load_json(name):
    return json.loads((REPORTS / name).read_text(
        encoding="utf-8"
    ))


def send(question, version):
    payload = {
        "question": question,
        "threshold": 0.95,
        "data_version": version,
        "evaluate": False,
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.status, json.load(response)


def read_spans(trace_id):
    path = REPORTS / "traces.jsonl"
    with path.open(encoding="utf-8") as f:
        return [
            obj for line in f if line.strip()
            if (obj := json.loads(line)).get("trace_id") == trace_id
        ]


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def main():
    commit = git("rev-parse", "HEAD")
    started = datetime.now(timezone.utc).isoformat()

    print("DATA 260 HW10 SMOKE TEST")
    print("Commit:", commit)
    print("API:", API)

    question = "Retrieve inspection details for inspection 10023."
    version = "hw10_verify_" + uuid4().hex

    miss = None
    hit = None

    try:
        status, miss = send(question, version)
        check(
            "Cold-cache Kafka request succeeds",
            status == 200
            and miss.get("is_cached") is False
            and miss.get("reviewer_status") == "approved"
            and bool(miss.get("answer")),
            f"HTTP {status}",
        )
    except Exception as exc:
        check("Cold-cache Kafka request succeeds", False, repr(exc))

    if miss:
        try:
            spans = read_spans(miss["trace_id"])
            stages = {s["stage"] for s in spans}
            required = {
                "cache_lookup",
                "inbox_publish",
                "planner",
                "writer",
                "reviewer",
                "final_response_wait",
                "cache_store",
            }
            check(
                "Trace ID propagated across Kafka stages",
                required.issubset(stages)
                and all(s.get("correlation_id") == miss["trace_id"]
                        for s in spans)
                and all(s.get("status") == "success"
                        for s in spans),
                f"trace_id={miss['trace_id']}; stages={sorted(stages)}",
            )
            check(
                "Three Kafka queue-wait spans",
                len([s for s in spans
                     if s["stage"] == "queue_wait"]) == 3,
            )
            check(
                "Cache miss recorded in tracing",
                any(s.get("cache_result") == "miss"
                    for s in spans),
            )
            check(
                "Smoke test skips GEval",
                not any(s["stage"] == "evaluation" for s in spans),
            )
        except Exception as exc:
            check("Kafka trace inspection", False, repr(exc))

        try:
            status, hit = send(question, version)
            check(
                "Repeated request returns semantic-cache hit",
                status == 200
                and hit.get("is_cached") is True
                and hit.get("answer") == miss.get("answer"),
                f"HTTP {status}",
            )
            hit_spans = read_spans(hit["trace_id"])
            check(
                "Cache hit bypasses Kafka agents",
                any(s.get("cache_result") == "hit"
                    for s in hit_spans)
                and not any(
                    s["stage"] in {"planner", "writer", "reviewer"}
                    for s in hit_spans
                ),
                f"trace_id={hit['trace_id']}",
            )
        except Exception as exc:
            check("Cache-hit smoke test", False, repr(exc))

    try:
        judge = load_json("judge_validation_summary.json")
        check(
            "Judge validation has 20 cases and 60 runs",
            judge.get("cases") == 20
            and judge.get("judge_runs") == 60,
        )
    except Exception as exc:
        check("Judge validation evidence", False, repr(exc))

    try:
        benchmark = load_json("hw10_benchmark_summary.json")
        with (REPORTS / "hw10_benchmark_50.csv").open(
            encoding="utf-8", newline=""
        ) as f:
            rows = list(csv.DictReader(f))
        check(
            "50 recorded confirmed cache misses",
            benchmark.get("confirmed_misses") == 50
            and benchmark.get("failed_attempts") == 0
            and len(rows) == 50
            and len({r["trace_id"] for r in rows}) == 50,
        )
    except Exception as exc:
        check("Benchmark evidence", False, repr(exc))

    try:
        full_id = "0d0a40af-21ca-4dfd-9c1e-c3e4852e6a9b"
        evaluation = json.loads(
            (REPORTS / "live_evaluations"
             / f"{full_id}.json").read_text(encoding="utf-8")
        )
        check(
            "Saved live GEval output matches trace",
            evaluation.get("trace_id") == full_id
            and all(
                "score_1_to_5" in evaluation.get("metrics", {}).get(name, {})
                for name in (
                    "plan_quality",
                    "writer_helpfulness",
                    "final_helpfulness",
                )
            ),
        )
    except Exception as exc:
        check("Saved GEval evidence", False, repr(exc))

    try:
        failure_spans = read_spans(
            "f9931c32-45ea-463b-b4f7-540e1e4d13fc"
        )
        check(
            "Failure trace includes stage error",
            any(
                s.get("stage") == "kafka_round_trip"
                and s.get("status") == "error"
                and s.get("error")
                for s in failure_spans
            ),
        )
    except Exception as exc:
        check("Failure-trace evidence", False, repr(exc))

    result = {
        "homework_number": 10,
        "sid4": "9981",
        "domain": "Local Restaurant Inspection",
        "prefix": "s9981",
        "commit_hash": commit,
        "model_configuration": {
            "judge": "qwen3:8b",
            "temperature": 0,
            "num_predict": 2048,
            "smoke_test_evaluation_enabled": False,
        },
        "seed": 9981,
        "verify_seed": 269981,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "api": API,
        "checks": checks,
        "passed": sum(c["passed"] for c in checks),
        "failed": sum(not c["passed"] for c in checks),
        "overall_status": (
            "PASS" if all(c["passed"] for c in checks)
            else "FAIL"
        ),
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    output = REPORTS / "verification.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print("SMOKE TEST:", result["overall_status"])
    print(f"Checks: {result['passed']} PASS / "
          f"{result['failed']} FAIL")
    print("Output:", output)

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
