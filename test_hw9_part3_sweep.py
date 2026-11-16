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


# ============================================================
# DEMO 1 — CONFIGURATION
# Test five similarity thresholds from 0.75 to 0.95.
# Use a separate Redis index to avoid affecting Part 2.
# ============================================================

THRESHOLDS = (0.75, 0.80, 0.85, 0.90, 0.95)
PREFIX = "s9981"
INDEX = f"{PREFIX}:hw09sweep:index"
KEY_PREFIX = f"{PREFIX}:hw09sweep:entry:"
VERSION = "v1"
OUT = Path("reports/hw09/raw")


# Helper: Return current UTC timestamp for logging.
def utc_now():
    return datetime.now(timezone.utc).isoformat()


# Helper: Convert Redis byte values into readable text.
def get_text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


# Helper: Run the HW8 agent on a cache miss.
# Only accept successfully completed answers.
def agent_answer(question):
    result = run_agent(question)
    if result.get("stop_reason") != "normal_completion" or not result.get("answer"):
        raise RuntimeError(
            f"HW8 agent failed for {question!r}: "
            f"{result.get('stop_reason')} / {result.get('error')}"
        )
    return str(result["answer"])


# ============================================================
# DEMO 2 — CREATE SEPARATE REDIS VECTOR INDEX
# Create an experimental cache using cosine distance.
# Keep the Part 2 production cache untouched.
# ============================================================

def create_separate_index(r, dimensions):
    try:
        # Check whether the experimental index already exists.
        r.ft(INDEX).info()
        return
    except ResponseError as exc:
        if "unknown index" not in str(exc).lower():
            raise

    # Define the fields stored in each experimental cache entry.
    schema = [
        TextField("query"),
        TextField("answer"),
        TagField("data_version"),
        VectorField("embedding", "FLAT", {
            "TYPE": "FLOAT32",
            "DIM": dimensions,
            "DISTANCE_METRIC": "COSINE",
        }),
    ]

    # Create the index using the student-specific key prefix.
    r.ft(INDEX).create_index(
        schema,
        definition=IndexDefinition(
            prefix=[KEY_PREFIX],
            index_type=IndexType.HASH
        ),
    )


# ============================================================
# DEMO 3 — COSINE SIMILARITY SEARCH
# Find the closest question in the fixed seed cache.
# Convert cosine distance into similarity: 1 - distance.
# Unlike Part 2, entity safeguards are disabled here
# to measure the raw similarity threshold trade-off.
# ============================================================

def search_fixed_seeds(r, embedding):
    # Search for the single nearest cached embedding.
    q = (
        Query("(@data_version:{v1})=>[KNN 1 @embedding $vec AS distance]")
        .sort_by("distance")
        .return_fields("query", "answer", "distance")
        .paging(0, 1)
        .dialect(2)
    )

    result = r.ft(INDEX).search(
        q,
        query_params={"vec": embedding}
    )

    # No cached candidate found.
    if not result.docs:
        return None

    doc = result.docs[0]

    # Return the cached question, answer, and cosine similarity.
    return {
        "cached_query": get_text(doc.query),
        "cached_answer": get_text(doc.answer),
        "similarity": max(
            -1.0,
            min(1.0, 1.0 - float(doc.distance))
        ),
    }


# ============================================================
# DEMO 4 — LOAD THE 40 LABELED TEST QUESTIONS
# 10 exact duplicates (should hit)
# 10 paraphrases (should hit)
# 10 similar-but-different questions (should miss)
# 10 unrelated questions (should miss)
#
# Labels are predefined and never changed after testing.
# ============================================================

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Load the committed test dataset.
    data = yaml.safe_load(
        Path("cache_cases.yaml").read_text(encoding="utf-8")
    )

    seeds = data["seed_queries"]
    cases = data["cases"]

    # Verify the dataset contains 10 seeds and 40 unique cases.
    assert len(seeds) == 10 and len(cases) == 40
    assert len({case["id"] for case in cases}) == 40

    # Exactly 20 cases should hit:
    # 10 duplicates + 10 paraphrases.
    assert sum(case["expected_hit"] for case in cases) == 20

    print("Timothy Song | DATA 260 | HW9 Part 3.2", flush=True)
    print(
        "MODE: raw cosine-only search "
        "(entity safeguard disabled for experiment)",
        flush=True
    )
    print(
        "CACHE POLICY: fixed 10 seed answers; "
        "no case adds a cache entry",
        flush=True
    )
    print(
        "DATASET: committed cache_cases.yaml; "
        "labels not modified",
        flush=True
    )

    # ========================================================
    # DEMO 5 — PRELOAD THE FIXED CACHE
    # Initialize Redis and the SentenceTransformer model.
    # Load 10 seed questions and their HW8 agent answers.
    #
    # Keep these same 10 cached answers for all thresholds.
    # This ensures a fair comparison.
    # ========================================================

    cache = SemanticCache()
    r = cache.redis_client

    create_separate_index(r, cache.dimensions)

    # Clear ONLY the experimental sweep entries.
    # Part 1 and Part 2 data remain untouched.
    old_keys = list(r.scan_iter(match=f"{KEY_PREFIX}*"))
    if old_keys:
        r.delete(*old_keys)

    # Generate the 10 initial answers using the HW8 agent.
    # Store their embeddings and answers in Redis.
    print(
        "\n=== Preloading 10 seed answers with the HW8 agent ===",
        flush=True
    )

    for seed in seeds:
        print(
            f"Preload {seed['id']}: {seed['query']}",
            flush=True
        )

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

    # ========================================================
    # DEMO 6 — THRESHOLD SWEEP (MAIN EXPERIMENT)
    # Test all 40 questions at each of the five thresholds.
    #
    # Convert question -> embedding -> cosine similarity.
    #
    # HIT: similarity >= threshold -> return cached answer.
    # MISS: similarity < threshold -> run HW8 agent.
    #
    # Do not store misses in the experimental cache.
    # ========================================================

    records = []
    summaries = []

    # Repeat the same experiment at each threshold.
    for threshold in THRESHOLDS:
        print(
            f"\n=== Threshold {threshold:.2f} | 40 cases ===",
            flush=True
        )

        threshold_records = []

        # Evaluate all 40 questions.
        for index, case in enumerate(cases, 1):
            begin_at = utc_now()
            start = perf_counter()

            # Convert the incoming question to an embedding.
            embedding = cache.embed(case["query"])

            # Find the most similar cached seed question.
            match = search_fixed_seeds(r, embedding)

            similarity = match["similarity"] if match else None

            # Decide HIT or MISS using the current threshold.
            is_cached = bool(match and similarity >= threshold)

            if is_cached:
                # CACHE HIT:
                # Reuse the stored answer without running HW8.
                answer = match["cached_answer"]
            else:
                # CACHE MISS:
                # Run the existing HW8 agent.
                #
                # Do NOT store the new answer because the
                # experimental cache must remain fixed.
                answer = agent_answer(case["query"])

            # Measure total response latency in milliseconds.
            latency_ms = (perf_counter() - start) * 1000

            # A false hit occurs when the cache returns an answer
            # for a question labeled as requiring a cache miss.
            false_hit = is_cached and not case["expected_hit"]

            # Record the result for this question.
            row = {
                "threshold": threshold,
                "case_id": case["id"],
                "category": case["category"],
                "question": case["query"],
                "reference_id": case["reference_id"],
                "expected_hit": case["expected_hit"],
                "is_cached": is_cached,
                "false_hit": false_hit,
                "similarity": (
                    round(similarity, 6)
                    if similarity is not None
                    else None
                ),
                "latency_ms": round(latency_ms, 2),
                "cached_query": (
                    match["cached_query"] if match else None
                ),
                "answer_returned": answer,
                "started_at_utc": begin_at,
                "finished_at_utc": utc_now(),
            }

            records.append(row)
            threshold_records.append(row)

            # Print whether the query was a hit or miss,
            # whether it was a false hit, and its latency.
            print(
                f"{index:02d}/40 {case['id']:14s} "
                f"hit={str(is_cached):5s} "
                f"expected={str(case['expected_hit']):5s} "
                f"false_hit={str(false_hit):5s} "
                f"sim={str(row['similarity']):8s} "
                f"ms={latency_ms:.2f}",
                flush=True,
            )

            # Save progress after each query.
            # Useful if Ollama or the agent fails during testing.
            (
                OUT / "part3_sweep_results.json"
            ).write_text(
                json.dumps(
                    records,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

        # ====================================================
        # DEMO 7 — CALCULATE PERFORMANCE METRICS
        # After each threshold, calculate:
        # - Number of cache hits
        # - Number of misses
        # - Number of false hits
        # - Hit rate
        # - False-hit rate
        # - Mean latency
        # ====================================================

        hits = sum(
            rw["is_cached"] for rw in threshold_records
        )

        false_hits = sum(
            rw["false_hit"] for rw in threshold_records
        )

        summary = {
            "threshold": threshold,
            "total": len(threshold_records),
            "hits": hits,
            "misses": 40 - hits,
            "false_hits": false_hits,

            # Percentage of all 40 queries served from cache.
            "hit_rate_pct": round(hits / 40 * 100, 2),

            # Percentage of all 40 queries incorrectly cached.
            "false_hit_rate_pct": round(
                false_hits / 40 * 100, 2
            ),

            # Average response time across the 40 queries.
            "mean_latency_ms": round(
                mean(
                    rw["latency_ms"]
                    for rw in threshold_records
                ),
                2
            ),
        }

        summaries.append(summary)

        # Save the summary for each tested threshold.
        (
            OUT / "part3_sweep_summary.json"
        ).write_text(
            json.dumps(summaries, indent=2),
            encoding="utf-8"
        )

    # ========================================================
    # DEMO 8 — DISPLAY AND SAVE FINAL RESULTS
    # Print the comparison table for all five thresholds.
    # Save detailed query results and threshold summaries.
    #
    # The cost model is calculated separately in Part 3.4.
    # ========================================================

    print(
        "\n=== FINAL THRESHOLD TABLE "
        "(cost to be added in 3.4) ===",
        flush=True
    )

    print(
        "Threshold | Hit rate | False-hit rate | "
        "Mean latency (ms)",
        flush=True
    )

    for s in summaries:
        print(
            f"{s['threshold']:.2f} | "
            f"{s['hit_rate_pct']:.2f}% | "
            f"{s['false_hit_rate_pct']:.2f}% | "
            f"{s['mean_latency_ms']:.2f}",
            flush=True,
        )

    print(
        f"Saved: {OUT / 'part3_sweep_results.json'}",
        flush=True
    )

    print(
        f"Saved: {OUT / 'part3_sweep_summary.json'}",
        flush=True
    )


if __name__ == "__main__":
    main()