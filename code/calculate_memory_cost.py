
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw06" / "raw"

INPUT_PRICE = 1.00
OUTPUT_PRICE = 5.00
CONVERSATIONS = 10_000

settings = [
    ("N=4", "sweep_n4_*.json", 3.60),
    ("N=12", "sweep_n12_*.json", 3.40),
    ("N=30", "sweep_n30_*.json", 4.00),
    ("N=12 + eviction", "eviction_n12_*.json", 4.20),
]

rows = []

for name, pattern, quality in settings:
    files = sorted(
        p for p in RAW.glob(pattern)
        if not p.name.endswith("_summary.json")
    )
    if not files:
        raise FileNotFoundError(f"Missing results: {pattern}")

    data = json.loads(files[-1].read_text(encoding="utf-8"))
    usage = data["usage_records"]

    assert len(usage) == 35, f"{name}: Expected 35 records"

    # Only the 30 conversation turns, excluding five probes.
    turns = usage[:30]

    input_tokens = sum(int(r["prompt_tokens"]) for r in turns)
    output_tokens = sum(int(r["completion_tokens"]) for r in turns)

    cost_per_conversation = (
        input_tokens * INPUT_PRICE
        + output_tokens * OUTPUT_PRICE
    ) / 1_000_000

    cost_10k = cost_per_conversation * CONVERSATIONS

    rows.append({
        "setting": name,
        "mean_prompt_tokens": round(input_tokens / 30, 2),
        "mean_completion_tokens": round(output_tokens / 30, 2),
        "reviewed_probe_quality": quality,
        "cost_per_30_turn_conversation": round(
            cost_per_conversation, 6
        ),
        "cost_for_10000_conversations": round(cost_10k, 2),
        "source_file": files[-1].name,
    })

best = max(rows, key=lambda r: r["reviewed_probe_quality"])
worst = min(rows, key=lambda r: r["reviewed_probe_quality"])

print("Timothy Song | DATA 260 HW6 | Part 3.5")
print("Estimated hosted-model inference cost")
print("Input: $1/M tokens | Output: $5/M tokens\n")

for row in rows:
    print(f"Setting: {row['setting']}")
    print(f"  Mean input tokens/turn: {row['mean_prompt_tokens']}")
    print(f"  Mean output tokens/turn: {row['mean_completion_tokens']}")
    print(f"  Cost per conversation: ${row['cost_per_30_turn_conversation']:.6f}")
    print(f"  Cost for 10,000 conversations: ${row['cost_for_10000_conversations']:.2f}")
    print()

print("BEST BY RECALL QUALITY:", best["setting"])
print("WORST BY RECALL QUALITY:", worst["setting"])

output = RAW / "memory_cost_table.json"
output.write_text(
    json.dumps({
        "pricing": {
            "input_per_million": INPUT_PRICE,
            "output_per_million": OUTPUT_PRICE,
        },
        "conversation_turns": 30,
        "number_of_conversations": CONVERSATIONS,
        "settings": rows,
        "best_by_recall_quality": best["setting"],
        "worst_by_recall_quality": worst["setting"],
        "scope": (
            "Primary chat-model inference only; additional "
            "summarization and extraction calls excluded."
        ),
    }, indent=2),
    encoding="utf-8",
)

print("\nPASS: Cost estimates calculated.")
print("Saved:", output)
