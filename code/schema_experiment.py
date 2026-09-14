import json
import time
from pathlib import Path
from agents_demo import build_graph
ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "reports" / "hw02" / "cases" / "schema_input.json"
OUTPUT_PATH = ROOT / "reports" / "hw02" / "raw" / "schema_30_runs.json"
with open(INPUT_PATH) as f:
    fixed_input = json.load(f)
app = build_graph()
results = []
for run_number in range(1, 31):
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
    latency_ms = (time.perf_counter() - start) * 1000
    failures = final_state["validation_failures"]
    if not final_state["planner_proposal"]:
        classification = "abandoned_at_ceiling"
    elif failures == 0:
        classification = "valid_first_attempt"
    elif failures == 1:
        classification = "valid_after_1_retry"
    else:
        classification = "valid_after_2_or_more_retries"
    result = {
        "run": run_number,
        "classification": classification,
        "planner_attempts": final_state["planner_attempts"],
        "validation_failures": failures,
        "turn_count": final_state["turn_count"],
        "latency_ms": round(latency_ms, 2)
    }
    results.append(result)
    print(result)
classifications = [
    "valid_first_attempt",
    "valid_after_1_retry",
    "valid_after_2_or_more_retries",
    "abandoned_at_ceiling"
]
summary = {}
for classification in classifications:
    matching = [
        result for result in results
        if result["classification"] == classification
    ]
    summary[classification] = {
        "count": len(matching),
        "mean_latency_ms": round(
            sum(result["latency_ms"] for result in matching) / len(matching),
            2
        ) if matching else None
    }
output = {
    "input": fixed_input,
    "runs": results,
    "summary": summary
}
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)
print(json.dumps(summary, indent=2))
print(f"Saved results to {OUTPUT_PATH}")