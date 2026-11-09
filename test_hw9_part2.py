import json
from pathlib import Path
from statistics import mean

from semantic_cache import SemanticCache, KEY_PREFIX

questions = [
    "Find inspections for Restaurant 13.",
    "Find inspections for Restaurant 13.",
    "Show inspections associated with Restaurant 13.",
    "Find inspections for Restaurant 14.",
    "Find inspections for Restaurant 14.",
    "Show inspection records for Restaurant 14.",
    "Retrieve inspection details for inspection 10017.",
    "Retrieve inspection details for inspection 10017.",
    "Show the details of inspection 10017.",
    "Find inspections for Restaurant 15.",
]

cache = SemanticCache()

# Clear only Part 2 semantic cache entries.
keys = list(cache.redis_client.scan_iter(match=f"{KEY_PREFIX}*"))
if keys:
    cache.redis_client.delete(*keys)

results = []

print("Timothy Song | DATA 260 | HW9 Part 2")
print("=== Semantic Cache Test ===", flush=True)

for number, question in enumerate(questions, start=1):
    result = cache.ask(
        question,
        threshold=0.85,
        data_version="v1",
    )

    results.append(result)

    print(
        f"Query #{number} | "
        f"Cached={result['is_cached']} | "
        f"Similarity={result['similarity']} | "
        f"Latency={result['latency_ms']:.2f} ms",
        flush=True,
    )

hits = [r for r in results if r["is_cached"]]
misses = [r for r in results if not r["is_cached"]]

print("\n=== Performance Summary ===")
print(f"Total queries: {len(results)}")
print(f"Cache hits: {len(hits)}")
print(f"Cache misses: {len(misses)}")
print(f"Hit rate: {len(hits) / len(results) * 100:.2f}%")

print(
    "Average cached latency:",
    round(mean(r["latency_ms"] for r in hits), 2)
    if hits else "N/A",
    "ms",
)

print(
    "Average non-cached latency:",
    round(mean(r["latency_ms"] for r in misses), 2)
    if misses else "N/A",
    "ms",
)

output = Path("reports/hw09/raw/part2_results.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, indent=2))

print(f"\nSaved results to {output}")