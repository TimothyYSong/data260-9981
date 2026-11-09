"""HW9 3.2: fixed-cache, raw cosine threshold sweep.

Run from repository root:
  PYTHONPATH=code:src python -u test_hw9_part3_sweep.py 2>&1 \
    | tee reports/hw09/raw/part3_sweep_log.txt

The 40 pre-registered cases are NEVER relabeled. This script uses a separate
s9981-prefixed Redis vector index so the production Part 2 cache is untouched.
The ten seed answers are populated by the existing HW8 agent once, and the
cache then remains fixed during all five sweeps. Every miss calls HW8, but
miss answers are deliberately not inserted into the experimental seed cache.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter

import yaml
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from agent import run_agent
from semantic_cache import SemanticCache

THRESHOLDS = (0.75, 0.80, 0.85, 0.90, 0.95)
PREFIX = "s9981"
INDEX = f"{PREFIX}:hw09sweep:index"
KEY_PREFIX = f"{PREFIX}:hw09sweep:entry:"
VERSION = "v1"
OUT = Path("reports/hw09/raw")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def agent_answer(question):
    result = run_agent(question)
    if result.get("stop_reason") != "normal_completion" or not result.get("answer"):
        raise RuntimeError(
            f"HW8 agent failed for {question!r}: "
            f"{result.get('stop_reason')} / {result.get('error')}"
        )
    return str(result["answer"])


def create_separate_index(r, dimensions):
    try:
        r.ft(INDEX).info()
        return
    except ResponseError as exc:
        if "unknown index" not in str(exc).lower():
            raise
    schema = [
        TextField("query"),
        TextField("answer"),
        TagField("data_version"),
        VectorField("embedding", "FLAT", {
            "TYPE": "FLOAT32", "DIM": dimensions,
            "DISTANCE_METRIC": "COSINE",
        }),
    ]
    r.ft(INDEX).create_index(
        schema,
        definition=IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH),
    )


def search_fixed_seeds(r, embedding):
    q = (
        Query("(@data_version:{v1})=>[KNN 1 @embedding $vec AS distance]")
        .sort_by("distance")
        .return_fields("query", "answer", "distance")
        .paging(0, 1)
        .dialect(2)
    )
    result = r.ft(INDEX).search(q, query_params={"vec": embedding})
    if not result.docs:
        return None
    doc = result.docs[0]
    return {
        "cached_query": get_text(doc.query),
        "cached_answer": get_text(doc.answer),
        "similarity": max(-1.0, min(1.0, 1.0 - float(doc.distance))),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(Path("cache_cases.yaml").read_text(encoding="utf-8"))
    seeds = data["seed_queries"]
    cases = data["cases"]
    assert len(seeds) == 10 and len(cases) == 40
    assert len({case["id"] for case in cases}) == 40
    assert sum(case["expected_hit"] for case in cases) == 20

    print("Timothy Song | DATA 260 | HW9 Part 3.2", flush=True)
    print("MODE: raw cosine-only search (entity safeguard disabled for experiment)", flush=True)
    print("CACHE POLICY: fixed 10 seed answers; no case adds a cache entry", flush=True)
    print("DATASET: committed cache_cases.yaml; labels not modified", flush=True)

    cache = SemanticCache()  # Reuse the existing embedding model and Redis connection.
    r = cache.redis_client
    create_separate_index(r, cache.dimensions)

    # This deletion targets only the dedicated sweep namespace, NOT Part 1 or 2.
    old_keys = list(r.scan_iter(match=f"{KEY_PREFIX}*"))
    if old_keys:
        r.delete(*old_keys)

    # Compute embeddings once, outside the timed query handler.
    # Inference on a request is timed separately to reflect real ingress latency.
    print("\n=== Preloading 10 seed answers with the HW8 agent ===", flush=True)
    for seed in seeds:
        print(f"Preload {seed['id']}: {seed['query']}", flush=True)
        answer = agent_answer(seed["query"])
        r.hset(
            f"{KEY_PREFIX}{seed['id']}",
            mapping={
                "query": seed["query"],
                "answer": answer,
                "data_version": VERSION,
                "embedding": cache.embed(seed["query"]),
            },
        )
    assert len(list(r.scan_iter(match=f"{KEY_PREFIX}*"))) == 10
    print("Seed cache ready: 10 entries", flush=True)

    records = []
    summaries = []
    for threshold in THRESHOLDS:
        print(f"\n=== Threshold {threshold:.2f} | 40 cases ===", flush=True)
        threshold_records = []
        for index, case in enumerate(cases, 1):
            begin_at = utc_now()
            start = perf_counter()
            embedding = cache.embed(case["query"])
            match = search_fixed_seeds(r, embedding)
            similarity = match["similarity"] if match else None
            is_cached = bool(match and similarity >= threshold)
            if is_cached:
                answer = match["cached_answer"]
            else:
                # Real miss: HW8 agent is invoked. Do NOT store its response,
                # or later test cases and thresholds would see different seeds.
                answer = agent_answer(case["query"])
            latency_ms = (perf_counter() - start) * 1000
            false_hit = is_cached and not case["expected_hit"]
            row = {
                "threshold": threshold,
                "case_id": case["id"],
                "category": case["category"],
                "question": case["query"],
                "reference_id": case["reference_id"],
                "expected_hit": case["expected_hit"],
                "is_cached": is_cached,
                "false_hit": false_hit,
                "similarity": round(similarity, 6) if similarity is not None else None,
                "latency_ms": round(latency_ms, 2),
                "cached_query": match["cached_query"] if match else None,
                "answer_returned": answer,
                "started_at_utc": begin_at,
                "finished_at_utc": utc_now(),
            }
            records.append(row)
            threshold_records.append(row)
            print(
                f"{index:02d}/40 {case['id']:14s} "
                f"hit={str(is_cached):5s} expected={str(case['expected_hit']):5s} "
                f"false_hit={str(false_hit):5s} "
                f"sim={str(row['similarity']):8s} "
                f"ms={latency_ms:.2f}",
                flush=True,
            )
            # Persist progress after EVERY query in case Ollama fails later.
            (OUT / "part3_sweep_results.json").write_text(
                json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        hits = sum(rw["is_cached"] for rw in threshold_records)
        false_hits = sum(rw["false_hit"] for rw in threshold_records)
        summary = {
            "threshold": threshold,
            "total": len(threshold_records),
            "hits": hits,
            "misses": 40 - hits,
            "false_hits": false_hits,
            "hit_rate_pct": round(hits / 40 * 100, 2),
            # Denominator: all 40 incoming questions, not only hits.
            "false_hit_rate_pct": round(false_hits / 40 * 100, 2),
            "mean_latency_ms": round(mean(rw["latency_ms"] for rw in threshold_records), 2),
        }
        summaries.append(summary)
        (OUT / "part3_sweep_summary.json").write_text(
            json.dumps(summaries, indent=2), encoding="utf-8"
        )

    print("\n=== FINAL THRESHOLD TABLE (cost to be added in 3.4) ===", flush=True)
    print("Threshold | Hit rate | False-hit rate | Mean latency (ms)", flush=True)
    for s in summaries:
        print(
            f"{s['threshold']:.2f} | {s['hit_rate_pct']:.2f}% | "
            f"{s['false_hit_rate_pct']:.2f}% | {s['mean_latency_ms']:.2f}",
            flush=True,
        )
    print(f"Saved: {OUT / 'part3_sweep_results.json'}", flush=True)
    print(f"Saved: {OUT / 'part3_sweep_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
