import json
import subprocess
import sys
from pathlib import Path

import requests


HW = 4
SID4 = 9981
SEED = 9981
VERIFY_SEED = 269981
PORT_BASE = 8081

BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
OUTPUT_PATH = Path("reports/hw04/verification.json")


def get_commit_hash():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def run_check(name, function):
    try:
        passed, details = function()

        return {
            "name": name,
            "passed": passed,
            "details": details,
        }

    except Exception as exc:
        return {
            "name": name,
            "passed": False,
            "details": str(exc),
        }


def check_backend():
    response = requests.get(
        f"{BASE_URL}/docs",
        timeout=5,
    )

    return (
        response.status_code == 200,
        f"HTTP {response.status_code}",
    )


def login_session():
    session = requests.Session()

    response = session.post(
        f"{BASE_URL}/login",
        json={
            "email": "test@example.com",
            "password": "Test123!",
        },
        timeout=5,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Login failed with HTTP {response.status_code}: "
            f"{response.text}"
        )

    return session


def check_naive_endpoint():
    session = login_session()

    response = session.get(
        f"{BASE_URL}/records/part3/nplus1",
        params={"page_size": 10},
        timeout=10,
    )

    if response.status_code != 200:
        return (
            False,
            f"HTTP {response.status_code}",
        )

    data = response.json()

    return (
        isinstance(data, list) and len(data) > 0,
        f"HTTP 200, returned {len(data)} records",
    )


def check_fixed_endpoint():
    session = login_session()

    response = session.get(
        f"{BASE_URL}/records/part3/fixed",
        params={"page_size": 10},
        timeout=10,
    )

    if response.status_code != 200:
        return (
            False,
            f"HTTP {response.status_code}",
        )

    data = response.json()

    return (
        isinstance(data, list) and len(data) > 0,
        f"HTTP 200, returned {len(data)} records",
    )


def main():
    checks = [
        run_check(
            "FastAPI backend responds on PORT_BASE",
            check_backend,
        ),
        run_check(
            "Naive N+1 endpoint returns data",
            check_naive_endpoint,
        ),
        run_check(
            "Fixed endpoint returns data",
            check_fixed_endpoint,
        ),
    ]

    verification = {
        "homework": HW,
        "sid4": SID4,
        "commit_hash": get_commit_hash(),
        "model_configuration": {
            "llm": "qwen3:8b",
            "embedding_model": "nomic-embed-text",
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "port_base": PORT_BASE,
        "checks": checks,
        "overall_passed": all(
            check["passed"]
            for check in checks
        ),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            verification,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            verification,
            indent=2,
        )
    )

    if not verification["overall_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()