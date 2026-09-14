import json
import time
from pathlib import Path
from agents_demo import build_graph
ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "reports" / "hw02" / "cases" / "adversarial_input.json"
OUTPUT_PATH = ROOT / "reports" / "hw02" / "raw" / "adversarial_5_runs.json"
with open(INPUT_PATH) as f:
    adversarial_input = json.load(f)
app = build_graph()
results = []
for run_number in range(1, 6):
    initial_state = {
        "title": adversarial_input["title"],
        "content": adversarial_input["content"],
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
    completed = (
        bool(final_state["planner_proposal"])
        and bool(final_state["reviewer_feedback"])
        and final_state["reviewer_feedback"].get("has_issue") is False
    )
    hit_ceiling = (
        final_state["turn_count"] >= 10
        and not completed
    )
    result = {
        "run": run_number,
        "completed": completed,
        "hit_ceiling": hit_ceiling,
        "turn_count": final_state["turn_count"],
        "planner_attempts": final_state["planner_attempts"],
        "validation_failures": final_state["validation_failures"],
        "latency_ms": round(latency_ms, 2)
    }
    results.append(result)
    print(result)
ceiling_hits = sum(
    1 for result in results
    if result["hit_ceiling"]
)
summary = {
    "runs": 5,
    "ceiling_hits": ceiling_hits,
    "ceiling_hit_rate_percent": round(ceiling_hits / 5 * 100, 2)
}
output = {
    "input": adversarial_input,
    "model_settings": {
        "model": "qwen3:8b",
        "temperature": 0.0,
        "max_turns": 10
    },
    "runs": results,
    "summary": summary
}
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)
print(json.dumps(summary, indent=2))
print(f"Saved results to {OUTPUT_PATH}")