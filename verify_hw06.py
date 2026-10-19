"""Run an HW6 smoke test and write an objective verification.json."""

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
PORT_BASE = 8081
BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
OUTPUT = ROOT / "verification.json"
REPORT_COPY = ROOT / "reports" / "hw06" / "verification.json"
SERVER_LOG = ROOT / "reports" / "hw06" / "raw" / "verification_server.log"


def git_value(*args: str) -> str:
    """Read a Git identifier without altering repository state."""
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        check=True,
    )
    return result.stdout.strip()


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    """Call a local API endpoint and return its JSON object."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urlopen(request, timeout=240) as response:
            if response.status != 200:
                raise RuntimeError(f"Expected HTTP 200; got {response.status}")
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read(700).decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Expected a JSON object")
    return result


def assert_server_free() -> None:
    """Require the test to start its own FastAPI process."""
    with socket.socket() as sock:
        sock.settimeout(1)
        if sock.connect_ex(("127.0.0.1", PORT_BASE)) == 0:
            raise RuntimeError(
                f"Port {PORT_BASE} is occupied. Stop the existing FastAPI "
                "server with Control+C before verification."
            )


def start_server() -> tuple[subprocess.Popen, object]:
    """Launch the real HW6 FastAPI app for smoke testing."""
    assert_server_free()
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_handle = SERVER_LOG.open("w", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "code")])
    env["SHORT_TERM_N"] = "12"
    env["HW6_MEMORY_POLICY"] = ""  # Test the unmodified default chat behavior.
    env["HW6_EXPERIMENT_NAME"] = "hw6_smoke_test"

    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app", "--app-dir", "code",
            "--host", "127.0.0.1", "--port", str(PORT_BASE),
        ],
        cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
    )

    for _ in range(60):
        if process.poll() is not None:
            break
        try:
            with urlopen(f"{BASE_URL}/docs", timeout=2) as response:
                if response.status == 200:
                    return process, log_handle
        except Exception:
            pass
        time.sleep(1)

    if process.poll() is None:
        process.terminate()
        process.wait(timeout=15)
    log_handle.close()
    raise RuntimeError(f"FastAPI did not start. Inspect {SERVER_LOG}")


def run_check(name: str, function) -> dict:
    """Record a behavior check as PASS or FAIL with details."""
    try:
        details = function()
        result = {"check": name, "passed": True, "details": details}
    except Exception as exc:
        result = {"check": name, "passed": False, "details": str(exc)}
    print(f"{'PASS' if result['passed'] else 'FAIL'}: {name} — {result['details']}", flush=True)
    return result


def verify_docs() -> str:
    """Ensure FastAPI responds on the required port."""
    with urlopen(f"{BASE_URL}/docs", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
    return f"FastAPI GET /docs returned HTTP 200 on PORT_BASE={PORT_BASE}"


def verify_help(user_id: str) -> str:
    """Verify the file-memory command reaches the actual chat API."""
    result = request_json("POST", "/api/chat", {
        "user_id": user_id, "message": "/help",
    })
    if not all(x in result.get("reply", "") for x in (
        "/memory", "/compact", "/dream", "/help",
    )):
        raise RuntimeError("Command response did not list all four commands")
    return "POST /api/chat accepted /help and returned all four commands"


def verify_chat(user_id: str, session_id: str) -> str:
    """Verify a real locally generated reply and memory metadata."""
    result = request_json("POST", "/api/chat", {
        "user_id": user_id,
        "session_id": session_id,
        "message": "This is a smoke test. Please acknowledge receipt.",
    })
    if not isinstance(result.get("reply"), str) or not result["reply"].strip():
        raise RuntimeError("Chat returned an empty reply")
    if result.get("session_id") != session_id:
        raise RuntimeError("Incorrect session_id in chat response")
    if not isinstance(result.get("memory_used"), dict):
        raise RuntimeError("Missing memory_used object")
    return "POST /api/chat returned a nonempty Ollama reply and memory_used"


def verify_memory(user_id: str) -> str:
    """Verify that chat messages persist in MongoDB."""
    result = request_json("GET", f"/api/memory/{user_id}")
    roles = [m.get("role") for m in result.get("messages", [])]
    if "user" not in roles or "assistant" not in roles:
        raise RuntimeError("MongoDB memory did not contain both user and assistant records")
    return "GET /api/memory returned persisted user and assistant messages"


def verify_aggregate(user_id: str) -> str:
    """Verify that the daily message aggregation endpoint works."""
    result = request_json("GET", f"/api/aggregate/{user_id}")
    daily = result.get("daily_message_counts")
    if not isinstance(daily, list) or sum(x.get("count", 0) for x in daily) < 2:
        raise RuntimeError("Aggregate did not include the two new chat messages")
    return "GET /api/aggregate returned daily message counts"


def main() -> int:
    """Execute smoke tests, save recorded outcomes, and exit on failure."""
    print("Timothy Song | DATA 260 HW6 | Verification", flush=True)
    print("Starting a fresh FastAPI process for the smoke test.\n", flush=True)

    user_id = f"hw6_verify_{uuid4().hex[:12]}"
    session_id = f"verify_session_{uuid4().hex[:12]}"
    checks = []
    process = None
    log_handle = None

    try:
        process, log_handle = start_server()
        checks.append(run_check("FastAPI on port 8081", verify_docs))
        checks.append(run_check("Memory /help command", lambda: verify_help(user_id)))
        chat = run_check("POST /api/chat local-model reply", lambda: verify_chat(user_id, session_id))
        checks.append(chat)
        if chat["passed"]:
            checks.append(run_check("MongoDB memory persistence", lambda: verify_memory(user_id)))
            checks.append(run_check("Daily aggregate endpoint", lambda: verify_aggregate(user_id)))
    except Exception as exc:
        checks.append({"check": "FastAPI startup", "passed": False, "details": str(exc)})
        print(f"FAIL: FastAPI startup — {exc}", flush=True)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if log_handle is not None:
            log_handle.close()

    try:
        commit_hash = git_value("rev-parse", "HEAD")
    except Exception:
        commit_hash = "unavailable"

    result = {
        "homework": 6,
        "student": "Timothy Song",
        "sid4": 9981,
        "commit_hash": commit_hash,
        "model": "qwen3:8b",
        "configuration": {
            "port_base": PORT_BASE,
            "prefix": "s9981",
            "domain_id": 5,
            "domain": "Local restaurant inspections",
            "embedding_model": "nomic-embed-text",
            "short_term_n": 12,
            "memory_policy": "default",
        },
        "seed": 9981,
        "verify_seed": 269981,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "overall_pass": bool(checks) and all(x["passed"] for x in checks),
        "server_log": str(SERVER_LOG.relative_to(ROOT)),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT_COPY.parent.mkdir(parents=True, exist_ok=True)
    REPORT_COPY.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("\nOVERALL:", "PASS" if result["overall_pass"] else "FAIL")
    print("Saved:", OUTPUT.relative_to(ROOT))
    print("Copy:", REPORT_COPY.relative_to(ROOT))
    if not result["overall_pass"]:
        print("Server log:", SERVER_LOG.relative_to(ROOT))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
