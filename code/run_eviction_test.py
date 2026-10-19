import json
import os

# Enable the policy before starting FastAPI.
os.environ["HW6_MEMORY_POLICY"] = "evict_assistant"

import run_memory_sweep as sweep


def main():
    print("Timothy Song | DATA 260 HW6 | Part 3.4")
    print("Policy: Evict historical assistant messages")
    print("SHORT_TERM_N=12")
    print("30 conversation messages + 5 probes\n")

    baseline_path = (
        sweep.RAW / "short_term_sweep_summary.json"
    )

    baseline_results = json.loads(
        baseline_path.read_text(encoding="utf-8")
    )

    baseline = next(
        result
        for result in baseline_results
        if result["short_term_n"] == 12
    )

    # Run the same conversation and probes with eviction.
    result = sweep.run_setting(12)

    # Preserve the detailed results under a policy-specific name.
    original_path = (
        sweep.RAW / f"sweep_n12_{sweep.STAMP}.json"
    )
    output_path = (
        sweep.RAW / f"eviction_n12_{sweep.STAMP}.json"
    )

    details = json.loads(
        original_path.read_text(encoding="utf-8")
    )

    details["summary"]["setting"] = (
        "SHORT_TERM_N=12 + assistant-message eviction"
    )
    details["summary"]["memory_policy"] = "evict_assistant"
    details["memory_policy"] = "evict_assistant"

    for record in details["usage_records"]:
        record["memory_policy"] = "evict_assistant"

    output_path.write_text(
        json.dumps(details, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    original_path.unlink()

    # Compare measured prompt-token averages.
    baseline_tokens = baseline["mean_prompt_tokens_per_turn"]
    eviction_tokens = result["mean_prompt_tokens_per_turn"]

    token_savings = baseline_tokens - eviction_tokens
    savings_percent = token_savings / baseline_tokens * 100

    comparison = {
        "policy": "evict_assistant",
        "short_term_n": 12,
        "baseline_mean_prompt_tokens": baseline_tokens,
        "eviction_mean_prompt_tokens": eviction_tokens,
        "token_savings_per_turn": round(token_savings, 2),
        "token_savings_percent": round(savings_percent, 2),
        "eviction_mean_latency_ms": result["mean_latency_ms"],
        "eviction_automated_probe_quality": (
            result["mean_probe_quality"]
        ),
        "baseline_reviewed_probe_quality": 3.4,
        "quality_review_pending": True,
        "raw_results": str(output_path),
    }

    summary_path = sweep.RAW / "eviction_n12_summary.json"
    summary_path.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    print("\n========== PART 3.4 RESULTS ==========")
    print(f"Baseline prompt tokens: {baseline_tokens:.2f}")
    print(f"Eviction prompt tokens: {eviction_tokens:.2f}")
    print(f"Token savings/turn: {token_savings:.2f}")
    print(f"Token savings: {savings_percent:.2f}%")
    print(f"Eviction latency (ms): {result['mean_latency_ms']:.2f}")
    print(
        "Eviction preliminary quality:",
        result["mean_probe_quality"],
    )
    print("Final quality delta: Pending manual probe review")
    print("Raw results:", output_path)
    print("Summary:", summary_path)
    print("PASS: Eviction experiment completed.")


if __name__ == "__main__":
    main()