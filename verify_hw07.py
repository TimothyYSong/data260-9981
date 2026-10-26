#!/usr/bin/env python3
"""DATA 260 HW7 objective smoke tests."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reports/hw07/verification.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

checks = []

def check(name, passed, detail):
    checks.append({
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "detail": str(detail),
    })
    print(f'{"PASS" if passed else "FAIL"}: {name}')

def get_json(url):
    with urlopen(url, timeout=10) as response:
        return json.load(response)

def git(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True
    ).strip()

def run():
    commit = git("rev-parse", "HEAD")
    try:
        tag_commit = git("rev-parse", "hw7^{commit}")
    except subprocess.CalledProcessError:
        tag_commit = None

    check(
        "Tagged commit",
        commit == tag_commit,
        f"HEAD={commit}; hw7={tag_commit}",
    )

    try:
        spec = get_json("http://127.0.0.1:8081/openapi.json")
        paths = spec.get("paths", {})
        check(
            "FastAPI authentication routes",
            "/auth/login" in paths and "/auth/me" in paths,
            "OpenAPI routes inspected",
        )
    except Exception as exc:
        check("FastAPI authentication routes", False, repr(exc))

    try:
        request = Request(
            "http://127.0.0.1:8081/auth/me",
            method="GET",
        )
        try:
            with urlopen(request, timeout=10) as response:
                status = response.status
        except HTTPError as exc:
            status = exc.code
        check("Unauthenticated access rejected", status == 401, f"HTTP {status}")
    except Exception as exc:
        check("Unauthenticated access rejected", False, repr(exc))

    try:
        payload = json.dumps({
            "username": "hw7_nonexistent_user_9981",
            "password": "invalid_password_test_9981",
        }).encode()
        request = Request(
            "http://127.0.0.1:8081/auth/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                status = response.status
        except HTTPError as exc:
            status = exc.code
        check("Invalid login rejected", status == 401, f"HTTP {status}")
    except Exception as exc:
        check("Invalid login rejected", False, repr(exc))

    try:
        models = get_json("http://127.0.0.1:11434/api/tags")
        names = [m.get("name") for m in models.get("models", [])]
        check("Ollama qwen3:8b available", "qwen3:8b" in names, names)
    except Exception as exc:
        check("Ollama qwen3:8b available", False, repr(exc))

    try:
        from agent import run_agent

        cases = json.loads(
            (ROOT / "reports/hw07/raw/verification_cases.json").read_text()
        )
        case = next(c for c in cases if c["case_id"] == "A")
        result = run_agent(case["question"], max_steps=8, max_repairs=1)

        history = result.get("history", [])
        tools = [
            item.get("tool") for item in history
            if item.get("result", {}).get("ok") is True
        ]
        required = case["expected_tools"]
        matched = any(
            tools[i:i + len(required)] == required
            for i in range(max(0, len(tools) - len(required) + 1))
        )
        passed = (
            result.get("stop_reason") == "normal_completion"
            and matched
            and bool(result.get("answer"))
        )
        check(
            "Agent verification task A",
            passed,
            f"stop_reason={result.get('stop_reason')}; "
            f"successful_tools={tools}; expected={required}",
        )
    except Exception as exc:
        check("Agent verification task A", False, repr(exc))

    try:
        from part6_safety_gate import confirm_bash

        safe = confirm_bash("pwd")
        unsafe = confirm_bash("rm -rf test_folder")

        # Accept only explicit approval/rejection represented by booleans.
        check(
            "Command safety gate",
            isinstance(safe, dict)
            and isinstance(unsafe, dict)
            and safe.get("allowed") is True
            and unsafe.get("allowed") is False,
            f"safe_result={safe!r}; unsafe_result={unsafe!r}",
        )
    except Exception as exc:
        check("Command safety gate", False, repr(exc))

    report = {
        "homework": 7,
        "sid4": "9981",
        "commit_hash": commit,
        "git_tag": "hw7",
        "tag_commit_hash": tag_commit,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": "qwen3:8b",
        "configuration": {
            "port_base": 8081,
            "prefix": "s9981",
            "domain_id": 5,
        },
        "seed": 9981,
        "verify_seed": 269981,
        "checks": checks,
        "overall_status": (
            "PASS" if all(c["status"] == "PASS" for c in checks)
            else "FAIL"
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nOverall: {report['overall_status']}")
    print(f"Report: {OUTPUT.relative_to(ROOT)}")

if __name__ == "__main__":
    run()
