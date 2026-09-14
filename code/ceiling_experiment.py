import json
import time
from pathlib import Path
from agents_demo import build_graph
ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "reports" / "hw02" / "cases" / "schema_input.json"
OUTPUT_PATH = ROOT / "reports" / "hw02" / "raw" / "ceiling_comparison.json"
with open(INPUT_PATH) as f:
    fixed_input = json.load(f)

app = build_graph()
results = []
for ceiling in [2, 10]:
    for run_number in range(1, 21):
        initial_state = {
            "title": fixed_input["title"],
            "content": fixed_input["content"],
            "planner_proposal": {},
            "reviewer_feedback": {},
            "turn_count": 0,
            "max_turns": ceiling,
            "planner_attempts": 0,
            "validation_failures": 0
        }
        start = time.perf_counter()
        final_state = app.invoke(initial_state)
        latency_ms = (time.perf_counter() - start) * 1000
        completed = (
            bool(final_state["planner_proposal"])
            and bool(final_state["reviewer_feedback"])
            and final_state["reviewer_feedback"].get("has_issue") is False
        )
        result = {
            "ceiling": ceiling,
            "run": run_number,
            "completed": completed,
            "turn_count": final_state["turn_count"],
            "planner_attempts": final_state["planner_attempts"],
            "validation_failures": final_state["validation_failures"],
            "latency_ms": round(latency_ms, 2)
        }
        results.append(result)
        print(result)
summary = {}
for ceiling in [2, 10]:
    matching = [
        result for result in results
        if result["ceiling"] == ceiling
    ]
    completed_count = sum(
        1 for result in matching
        if result["completed"]
    )
    summary[str(ceiling)] = {
        "runs": len(matching),
        "completed": completed_count,
        "completion_rate_percent": round(
            completed_count / len(matching) * 100,
            2
        ),
        "mean_latency_ms": round(
            sum(result["latency_ms"] for result in matching) / len(matching),
            2
        )
    }
output = {
    "input": fixed_input,
    "model_settings": {
        "model": "qwen3:8b",
        "temperature": 0.0
    },
    "runs": results,
    "summary": summary
}
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)
print(json.dumps(summary, indent=2))
print(f"Saved results to {OUTPUT_PATH}")