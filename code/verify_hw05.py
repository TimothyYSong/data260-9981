import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SID4 = 9981
PORT_BASE = 8081
SEED = 9981
VERIFY_SEED = 269981
MODEL = "qwen3:8b"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "reports" / "hw05" / "verification.json"


def get_commit_hash():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def run_check(name, function):
    try:
        details = function()

        return {
            "check": name,
            "passed": True,
            "details": details,
        }

    except Exception as error:
        return {
            "check": name,
            "passed": False,
            "details": str(error),
        }


def check_fastapi():
    import requests

    url = f"http://127.0.0.1:{PORT_BASE}/docs"

    response = requests.get(
        url,
        timeout=5,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"FastAPI returned HTTP {response.status_code}"
        )

    return (
        f"FastAPI responded on PORT_BASE {PORT_BASE} "
        f"with HTTP {response.status_code}"
    )


def check_meals_mcp():
    sys.path.insert(
        0,
        str(ROOT / "code"),
    )

    import meals_server

    result = meals_server.search_meals_by_name(
        "Arrabiata",
        1,
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "search_meals_by_name did not return a list"
        )

    if len(result) < 1:
        raise RuntimeError(
            "search_meals_by_name returned no results"
        )

    return (
        "Meals MCP tool search_meals_by_name "
        "returned at least one result"
    )


def check_domain_mcp():
    sys.path.insert(
        0,
        str(ROOT / "code"),
    )

    import domain_server

    result = domain_server.restaurant_inspection_summary(
        1
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "domain tool did not return a dictionary"
        )

    if result.get("ok") is not True:
        raise RuntimeError(
            f"domain tool returned failure: {result}"
        )

    return (
        "Domain MCP tool restaurant_inspection_summary "
        "returned ok=true"
    )


def check_offline_tests():
    result = subprocess.run(
        [
            sys.executable,
            "code/test_tools.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    output = (
        result.stdout
        + "\n"
        + result.stderr
    )

    if result.returncode != 0:
        raise RuntimeError(
            "offline test runner exited with non-zero status"
        )

    if "FINAL SUMMARY: 8/8 tests passed" not in output:
        raise RuntimeError(
            "offline test runner did not report 8/8 passed"
        )

    return "Offline test suite passed 8/8 tests"


def check_raw_artifacts():
    required_files = [
        "reports/hw05/raw/fault_injection_calls.csv",
        "reports/hw05/raw/agent_runs.jsonl",
        "reports/hw05/raw/meals_search_output.json",
        "reports/hw05/raw/meals_ingredient_output.json",
        "reports/hw05/raw/meals_random_output.json",
        "reports/hw05/raw/meals_detail_output.json",
        "reports/hw05/raw/domain_search_output.json",
        "reports/hw05/raw/domain_detail_output.json",
        "reports/hw05/raw/domain_summary_output.json",
    ]

    missing = []

    for relative_path in required_files:
        path = ROOT / relative_path

        if not path.exists():
            missing.append(relative_path)

    if missing:
        raise RuntimeError(
            "missing required raw artifacts: "
            + ", ".join(missing)
        )

    return (
        f"All {len(required_files)} required raw "
        "artifact files are present"
    )


def main():
    checks = [
        run_check(
            "FastAPI smoke test",
            check_fastapi,
        ),
        run_check(
            "Meals MCP tool smoke test",
            check_meals_mcp,
        ),
        run_check(
            "Domain MCP tool smoke test",
            check_domain_mcp,
        ),
        run_check(
            "Offline test suite",
            check_offline_tests,
        ),
        run_check(
            "Required raw artifacts",
            check_raw_artifacts,
        ),
    ]

    overall_pass = all(
        check["passed"]
        for check in checks
    )

    verification = {
        "homework": 5,
        "student": "Timothy Song",
        "sid4": SID4,
        "commit_hash": get_commit_hash(),
        "model": MODEL,
        "configuration": {
            "port_base": PORT_BASE,
            "prefix": "s9981",
            "domain": "Local Restaurant Inspections",
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
        "overall_pass": overall_pass,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            verification,
            file,
            indent=2,
        )

    print("Student: Timothy Song")
    print("Homework 5 Verification")
    print()

    for check in checks:
        status = (
            "PASS"
            if check["passed"]
            else "FAIL"
        )

        print(
            f"{status}: "
            f"{check['check']} - "
            f"{check['details']}"
        )

    print()

    print(
        "OVERALL:",
        "PASS" if overall_pass else "FAIL",
    )

    print(
        "Verification file:",
        OUTPUT_FILE,
    )

    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()