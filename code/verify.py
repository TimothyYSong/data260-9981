import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
OUTPUT = ROOT / "reports" / "hw02" / "verification.json"
SID4 = 9981
PORT_BASE = 8081
PREFIX = "s9981"
SEED = 9981
VERIFY_SEED = 269981
DOMAIN_ID = 5
MODEL = "qwen3:8b"
TEMPERATURE = 0.0
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CODE))
checks = {}
def record(name, passed, details=""):
    checks[name] = {
        "passed": bool(passed),
        "details": details
    }
def get_commit_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True
        ).strip()
    except Exception:
        return "unknown"
required_files = [
    "code/main.py",
    "code/agents_demo.py",
    "src/model_client.py",
    "reports/hw02/cases/schema_input.json",
    "reports/hw02/cases/adversarial_input.json",
    "reports/hw02/raw/schema_30_runs.json",
    "reports/hw02/raw/ceiling_comparison.json",
    "reports/hw02/raw/adversarial_5_runs.json",
    "reports/hw02/RUN_LOG.txt",
    "reports/hw02/METRICS.md",
    "reports/hw02/AI_USE.md",
    "reports/hw02/reproducible_run_instructions.md"
]
missing_files = [
    path for path in required_files
    if not (ROOT / path).exists()
]
record(
    "required_files_exist",
    len(missing_files) == 0,
    "All required HW2 files exist."
    if not missing_files
    else f"Missing files: {missing_files}"
)
server = None
try:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    server = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=CODE,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    backend_responded = False
    status_code = None
    for _ in range(20):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{PORT_BASE}/api/restaurants",
                timeout=2
            ) as response:
                status_code = response.status
                backend_responded = status_code == 200
                break
        except Exception:
            time.sleep(0.5)
    record(
        "fastapi_responds_on_port_base",
        backend_responded,
        f"GET /api/restaurants returned HTTP {status_code}."
        if backend_responded
        else f"FastAPI did not return HTTP 200 on port {PORT_BASE}."
    )
finally:
    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
try:
    from agents_demo import build_graph
    input_path = ROOT / "reports" / "hw02" / "cases" / "schema_input.json"
    with open(input_path, "r") as file:
        fixed_input = json.load(file)
    app = build_graph()
    initial_state = {
        "title": fixed_input["title"],
        "content": fixed_input["content"],
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "max_turns": 10,
        "planner_attempts": 0,
        "validation_failures": 0
    }
    start = time.perf_counter()
    final_state = app.invoke(initial_state)
    elapsed_seconds = time.perf_counter() - start
    graph_finished = isinstance(final_state, dict)
    record(
        "langgraph_finishes",
        graph_finished,
        f"LangGraph finished in {elapsed_seconds:.2f} seconds."
        if graph_finished
        else "LangGraph did not return a final state."
    )
    proposal = final_state.get("planner_proposal", {})
    tags = proposal.get("tags", [])
    summary = proposal.get("summary", "")
    valid_tags = (
        isinstance(tags, list)
        and len(tags) == 3
        and all(
            isinstance(tag, str)
            and 3 <= len(tag) <= 30
            for tag in tags
        )
    )
    record(
        "planner_returns_exactly_three_valid_tags",
        valid_tags,
        f"Planner returned {len(tags)} tags."
    )
    valid_summary = (
        isinstance(summary, str)
        and len(summary.split()) <= 25
    )
    record(
        "planner_summary_within_25_words",
        valid_summary,
        f"Planner summary contains {len(summary.split())} words."
    )
    reviewer_feedback = final_state.get("reviewer_feedback", {})
    reviewer_completed = (
        isinstance(reviewer_feedback, dict)
        and "has_issue" in reviewer_feedback
    )
    record(
        "reviewer_completes",
        reviewer_completed,
        "Reviewer returned structured feedback."
        if reviewer_completed
        else "Reviewer feedback was missing."
    )
    within_turn_ceiling = (
        final_state.get("turn_count", 0) <= 10
    )
    record(
        "graph_respects_turn_ceiling",
        within_turn_ceiling,
        f"Graph finished with turn_count={final_state.get('turn_count')}."
    )
except Exception as error:
    record(
        "langgraph_smoke_test",
        False,
        str(error)
    )
overall_pass = all(
    check["passed"]
    for check in checks.values()
)
verification = {
    "homework": "HW2",
    "sid4": SID4,
    "commit_hash": get_commit_hash(),
    "configuration": {
        "port_base": PORT_BASE,
        "prefix": PREFIX,
        "domain_id": DOMAIN_ID,
        "model": MODEL,
        "temperature": TEMPERATURE
    },
    "seed": SEED,
    "verify_seed": VERIFY_SEED,
    "checks": checks,
    "overall_pass": overall_pass
}
with open(OUTPUT, "w") as file:
    json.dump(verification, file, indent=2)
print(json.dumps(verification, indent=2))
print(f"\nSaved verification results to: {OUTPUT}")