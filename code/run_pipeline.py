import json
import time
from agents_demo import pipeline
from collections import Counter
import numpy as np
with open(
    "reports/hw01/cases/nondeterminism_input.json",
    "r"
) as file:
    fixed_input = json.load(file)
title = fixed_input["title"]
content = fixed_input["content"]
results = []
for temperature in [0.7, 0.0]:
    print(f"\nTemperature: {temperature}")
    for trial in range(1, 21):
        start_time = time.perf_counter()
        result = pipeline(
            title,
            content,
            temperature
        )
        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000
        print(
            f"Run {trial}: "
            f"{result['tags']} "
            f"{latency_ms:.2f} ms"
        )
        results.append({
            "temperature": temperature,
            "trial": trial,
            "tags": result["tags"],
            "latency_ms": latency_ms
        })
with open(
    "reports/hw01/raw/nondeterminism_results.json",
    "w"
) as file:
    json.dump(results, file, indent=2)
for temperature in [0.7, 0.0]:
    temp_results = [
        r for r in results
        if r["temperature"] == temperature
    ]
    tag_sets = {
        tuple(sorted(r["tags"]))
        for r in temp_results
    }
    tag_counts = Counter()
    for r in temp_results:
        for tag in set(r["tags"]):
            tag_counts[tag] += 1
    tags_all_20 = [
        tag
        for tag, count in tag_counts.items()
        if count == 20
    ]
    tags_once = [
        tag
        for tag, count in tag_counts.items()
        if count == 1
    ]
    latencies = [
        r["latency_ms"]
        for r in temp_results
    ]
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    print(f"\nThe results for temperature {temperature}")
    print(f"The distinct tag sets: {len(tag_sets)}")
    print(f"The tags in all 20 runs: {tags_all_20}")
    print(f"The tags in exactly 1 run: {tags_once}")
    print(f"Latency for p50: {p50:.2f} ms")
    print(f"Latency for p95: {p95:.2f} ms")
    print(f"Latency for p99: {p99:.2f} ms")