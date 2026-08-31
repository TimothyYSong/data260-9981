import json
import py_compile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
checks = {}
def record(name, passed, details=""):
    checks[name] = {
        "passed": bool(passed),
        "details": details
    }
required_files = [
    "AGENT.md",
    "DOMAIN_SCHEMA.md",
    "README.md",
    "code/agents_demo.py",
    "code/hw1_client.py",
    "code/run_pipeline.py",
    "code/Dockerfile",
    "src/model_client.py",
    "reports/hw01/RUN_LOG.txt",
    "reports/hw01/METRICS.md",
    "reports/hw01/AI_USE.md",
    "reports/hw01/cases/nondeterminism_input.json",
    "reports/hw01/raw/nondeterminism_results.json",
    "reports/hw01/raw/token_counts.json"
]
missing_files = [
    path for path in required_files
    if not (ROOT / path).exists()
]
record(
    "required_files_exist",
    len(missing_files) == 0,
    "All required files exist."
    if not missing_files
    else f"Missing files: {missing_files}"
)
python_files = [
    ROOT / "code/agents_demo.py",
    ROOT / "code/hw1_client.py",
    ROOT / "code/run_pipeline.py",
    ROOT / "src/model_client.py"
]
compile_errors = []
for file in python_files:
    try:
        py_compile.compile(str(file), doraise=True)
    except Exception as error:
        compile_errors.append(f"{file.name}: {error}")
record(
    "python_files_compile",
    len(compile_errors) == 0,
    "All Python files compiled successfully."
    if not compile_errors
    else str(compile_errors)
)
try:
    from src.model_client import ModelClient

    record(
        "model_client_complete_interface",
        hasattr(ModelClient, "complete"),
        "ModelClient defines the complete method."
    )
except Exception as error:
    record(
        "model_client_complete_interface",
        False,
        str(error)
    )
input_path = ROOT / "reports/hw01/cases/nondeterminism_input.json"
try:
    with open(input_path, "r") as file:
        fixed_input = json.load(file)
    valid_input = (
        isinstance(fixed_input.get("title"), str)
        and len(fixed_input["title"]) > 0
        and isinstance(fixed_input.get("content"), str)
        and len(fixed_input["content"]) > 0
    )
    record(
        "nondeterminism_input_valid",
        valid_input,
        "Fixed input contains a non-empty title and content."
    )
except Exception as error:
    record(
        "nondeterminism_input_valid",
        False,
        str(error)
    )
results_path = ROOT / "reports/hw01/raw/nondeterminism_results.json"
try:
    with open(results_path, "r") as file:
        results = json.load(file)

    record(
        "nondeterminism_total_runs",
        len(results) == 40,
        f"Found {len(results)} runs; expected 40."
    )
    temp_07 = [
        run for run in results
        if run.get("temperature") == 0.7
    ]
    temp_00 = [
        run for run in results
        if run.get("temperature") == 0.0
    ]
    record(
        "temperature_0_7_runs",
        len(temp_07) == 20,
        f"Found {len(temp_07)} runs at temperature 0.7; expected 20."
    )
    record(
        "temperature_0_0_runs",
        len(temp_00) == 20,
        f"Found {len(temp_00)} runs at temperature 0.0; expected 20."
    )
    exactly_three_tags = all(
        isinstance(run.get("tags"), list)
        and len(run["tags"]) == 3
        for run in results
    )
    record(
        "three_tags_per_run",
        exactly_three_tags,
        "Every nondeterminism run contains exactly 3 tags."
    )
    valid_latencies = all(
        isinstance(run.get("latency_ms"), (int, float))
        and run["latency_ms"] >= 0
        for run in results
    )
    record(
        "latency_values_valid",
        valid_latencies,
        "Every nondeterminism run contains a valid non-negative latency."
    )
except Exception as error:
    record(
        "nondeterminism_results_valid",
        False,
        str(error)
    )
token_path = ROOT / "reports/hw01/raw/token_counts.json"
try:
    with open(token_path, "r") as file:
        token_counts = json.load(file)
    record(
        "token_count_turns",
        len(token_counts) == 5,
        f"Found {len(token_counts)} token-count turns; expected 5."
    )
    correct_turn_numbers = [
        item.get("turn") for item in token_counts
    ] == [1, 2, 3, 4, 5]
    record(
        "token_turn_numbers",
        correct_turn_numbers,
        "Token-count records contain turns 1 through 5."
    )
    totals_match = all(
        item.get("total_tokens")
        == item.get("input_tokens", 0)
        + item.get("output_tokens", 0)
        for item in token_counts
    )
    record(
        "token_totals_match",
        totals_match,
        "Each total token count equals input tokens plus output tokens."
    )
except Exception as error:
    record(
        "token_counts_valid",
        False,
        str(error)
    )
overall_pass = all(
    check["passed"]
    for check in checks.values()
)
verification = {
    "homework": "HW1",
    "overall_pass": overall_pass,
    "checks": checks
}
output_path = ROOT / "reports/hw01/verification.json"
with open(output_path, "w") as file:
    json.dump(verification, file, indent=2)
print(json.dumps(verification, indent=2))
print(f"\nSaved verification results to: {output_path}")