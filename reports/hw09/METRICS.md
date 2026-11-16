# DATA 260 — Homework 9 Metrics

**Student:** Timothy Song
**Domain:** Local Restaurant Inspection (`DOMAIN_ID=5`)
**Configuration:** `SID4=9981`, `PREFIX=s9981`, `SEED=9981`, `VERIFY_SEED=269981`
**Inference model:** local `qwen3:8b`
**Semantic embeddings:** SentenceTransformers `all-MiniLM-L6-v2` (384 dimensions); cosine similarity with Redis vector search

## Measurement provenance

These are results of **previously recorded local tests**, not new benchmarks performed when this file was prepared. Results are drawn from saved artifacts in `reports/hw09/raw/`, `hw9_part4/`, and the HW9 report. Timings are wall-clock observations from the specified tests; run-to-run variability is expected. No cloud API inference charges are reported. The Part 3 cost model is illustrative rather than actual expenditure.

## Part 1 — Redis inspection view counter

| Metric / check | Observed result |
|---|---|
| Tested entity | `RestaurantInspection`, inspection `10017` |
| Redis key pattern | `s9981:views:inspection:{id}` |
| Redis operation | `INCR` per access |
| Test accesses | 25 |
| SQL persistence interval | Every 10 increments (`count % 10 == 0`) |
| Observed SQL sync points | 10, 20 |
| Redis count at end | 25 |
| Persisted SQL `view_count` at end | 20 |
| Difference at end | 5 views, expected before next sync |

**Interpretation:** Redis reflects every increment immediately, while SQL intentionally lags until the next 10-view synchronization. No Part 1 throughput or latency benchmark was recorded; do not infer a measured speedup.

**Evidence:** `reports/hw09/raw/part1_counter.txt`; HW9 report, Part 1.

## Part 2 — Semantic response cache (threshold = 0.85)

| Metric | Measured result |
|---|---:|
| Test questions | 10 |
| Cache hits | 5 |
| Cache misses | 5 |
| Hit rate | 50.00% |
| Average hit latency | 44.99 ms |
| Average miss latency | 15,529.68 ms |
| Ratio: mean miss latency / mean hit latency | 345.17× |

The latency ratio compares **observed averages of the two groups**; it is not an end-to-end speedup claim for every user request. Cache misses invoke the existing HW8 agent and successful answers are stored; cache hits return cached answers without invoking that agent. Responses include `is_cached`, similarity (when applicable), and latency.

Selected observations:

- Exact duplicate: cosine similarity **1.0000**, cache hit.
- Paraphrase: cosine similarity **0.9373**, cache hit.
- Valid paraphrase with similarity **0.8444**: cache miss below the 0.85 threshold.
- Entity-aware matching rejects reuse when inspection or restaurant identifiers conflict; Part 3 deliberately examines raw similarity without this safeguard.

**Metric definitions:** hit rate = cache hits / total questions; mean hit/miss latency = arithmetic mean of measured `latency_ms` in each category.

**Evidence:** `reports/hw09/raw/part2_corrected_results.json`, `reports/hw09/raw/part2_corrected_test.txt`; HW9 report, Part 2.

## Part 3.1–3.2 — Fixed labeled set and threshold sweep

The preregistered `cache_cases.yaml` contains **40 labeled cases** (10 exact duplicates, 10 paraphrases, 10 similar-but-different, 10 unrelated), plus 10 reference queries for preloading. The 40-case set was evaluated at five thresholds, yielding **200 query evaluations**. The Redis reference cache was held fixed during the sweep; the raw similarity test omitted entity-aware filtering to expose incorrect reuse.

| Threshold | Hits | Misses | False hits | Hit rate | False-hit rate | Mean latency (ms) | Modeled cost |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.75 | 30 | 10 | 10 | 75.00% | 25.00% | 2,492.84 | $2.60 |
| 0.80 | 30 | 10 | 10 | 75.00% | 25.00% | 2,468.31 | $2.60 |
| 0.85 | 24 | 16 | 10 | 60.00% | 25.00% | 4,512.16 | $2.66 |
| 0.90 | 19 | 21 | 9 | 47.50% | 22.50% | 8,173.39 | $2.46 |
| 0.95 | 15 | 25 | 5 | 37.50% | 12.50% | 10,385.84 | $1.50 |

**Definitions (denominator = 40 for each threshold):**

- Hit rate = number of cache hits / 40 × 100%.
- False-hit rate = incorrect cache hits / 40 × 100% (**not** false hits divided by all hits).
- Mean latency = arithmetic mean over all 40 question latencies at that threshold, including cache hits and HW8-agent misses.

**Evidence:** `cache_cases.yaml`; `reports/hw09/raw/part3_sweep_summary.json`, `part3_sweep_results.json`, and `part3_sweep_log.txt`.

### Part 3.3 — Representative false hit

| Field | Recorded value |
|---|---|
| Cached query | `Find inspections for Restaurant 17.` |
| Incoming query | `Find inspections for Restaurant 18.` |
| Similarity | 0.941031 |
| Threshold | 0.85 |
| Actual outcome | Incorrect cache hit for Restaurant 17 / inspection 10021 / 117 Test Street / 0 violations |
| Correct outcome | Restaurant 18 / inspection 10022 / 118 Test Street / 0 violations |

The queries differ in entity identifier but have nearly identical text. A high cosine similarity therefore did not establish factual interchangeability.

**Evidence:** `reports/hw09/raw/part3_false_hit.txt`; HW9 report, Part 3.3.

### Part 3.4 — Illustrative cost model

**Assumed cache-miss cost:** $0.01 per miss.
**Assumed false-hit/correction cost:** $0.25 per false hit.
**Formula:** modeled total = (misses × $0.01) + (false hits × $0.25).

With these assumptions and this labeled workload, **0.95** had the lowest modeled total (**$1.50**) and was selected. This is **not a measured AWS, electricity, or token bill** and is not necessarily optimal for other workloads. Five false hits remained even at 0.95, so entity-aware checks continue to matter.

**Evidence:** `reports/hw09/raw/part3_cost_model.txt`; HW9 report, Part 3.4.

### Part 3.5 — Stale-answer and invalidation check

For inspection `10017`, a cached **0 violations** answer became stale when the SQL record was changed to **3 violations**. Requests under `hw09stale1` returned the old cached value; advancing the data version to `hw09stale2` caused a miss followed by a fresh **3 violations** answer and a subsequent correct hit. The SQL value was restored to **0** after the demonstration (with a further version advancement noted as necessary).

**Trade-off:** version changes exclude stale entries from retrieval but may invalidate otherwise valid entries, increasing misses and model inference. Version management must be coordinated with data updates.

**Evidence limitation:** the original terminal session was cleared; the HW9 report, Part 3.5, preserves copied execution excerpts rather than full original screenshots.

## Part 4 — Self-improving multi-agent system

**Data split:** reference dataset of 40 distinct inspection records; 8 training, 8 validation, and 8 held-out test questions. Question datasets contain no expected-answer fields, and their inspection IDs do not overlap across splits. The reference dataset serves as evaluator ground truth.

### Part 4.1 — Answer repair and evaluator robustness

| Check | Recorded outcome |
|---|---|
| Controlled initial answer, inspection 10016 | Incorrectly said 3 violations |
| First evaluation | REVISE; reference value = 0 violations |
| Revised answer | 0 violations |
| Second evaluation | PASS |
| Total attempts | 2 (maximum allowed: 2) |
| Controlled repair latency | 12,772.70 ms |
| Normal question, inspection 10017 | PASS on first attempt |
| Normal demonstration latency | 7,863.04 ms |
| Evaluator robustness, initial version | 4/6 cases classified correctly |
| Evaluator robustness, corrected version | 6/6 cases classified correctly |

The evaluator's final decision requires both deterministic ground-truth checks and an independent Qwen3 PASS. The controlled failure is an intentionally injected **development demonstration**, not a naturally observed model error.

**Evidence:** `hw9_part4/evidence/revision_demo.txt`; `hw9_part4/test_evaluator_robustness.py` and recorded console outcomes.

### Part 4.2 — Lesson persistence and reuse

Two controlled failure cases triggered creation of `lesson_001` for the repeated failure pattern **“Missing or incorrect violation count.”** Stored fields: `lesson_id`, `failure_pattern`, `correction`, `created_at`, `use_count`. On a later question about inspection `10018`, the saved lesson was loaded, the Answering Agent returned **0 violations**, and the Evaluator Agent returned **PASS**. The recorded `use_count` became **2** after the later demonstration.

**Interpretation:** successful lesson loading and reuse was observed, but that demonstration alone does not establish a causal accuracy gain.

**Evidence:** `hw9_part4/lessons.json`; `hw9_part4/evidence/lesson_reuse.txt`.

### Part 4.3 — Before/after validation

| Metric | Without lesson | With lesson |
|---|---:|---:|
| Validation cases | 8 | 8 |
| Correct | 8 | 8 |
| Incorrect | 0 | 0 |
| Accuracy | 100% | 100% |
| Observed regressions | — | 0 |
| Observed unrelated failures | — | 0 |

**Lesson decision:** `KEEP`. The rule preserved previously correct answers and caused no observed regression in these eight cases; **no improvement in measured accuracy** was demonstrated.

**Evidence:** `hw9_part4/validation_results.json`.

### Part 4.4 — Held-out four-variant comparison

Eight unchanged held-out questions were evaluated separately on each variant (**32 executions**).

| Variant | Correct | Incorrect | Accuracy | Average attempts | Average latency (ms) |
|---|---:|---:|---:|---:|---:|
| Baseline | 8 | 0 | 100% | 1.000 | 5,396.04 |
| Evaluator Repair | 8 | 0 | 100% | 1.000 | 9,844.12 |
| Lesson Memory | 8 | 0 | 100% | 1.000 | 10,230.15 |
| Validated Improvement | 8 | 0 | 100% | 1.000 | 10,222.26 |

**Latency definition:** time until the variant returns its final answer. For Baseline, offline evaluator grading is **excluded** from latency; for the other variants, evaluator inference and any repairs are included. All final test answers passed on their first attempt, so no actual revision was needed in the held-out comparison. The two lesson-enabled variants used the same approved lesson, which explains their similar results.

**Interpretation:** all variants attained 100% accuracy on this small test; the added evaluator and lesson mechanisms increased latency without a measured accuracy benefit on these specific questions. The controlled repair demonstration separately verifies the ability to correct a failed answer.

**Evidence:** `hw9_part4/variant_results.json`; `hw9_part4/compare_variants.py`.

## Limitations and reproducibility notes

1. Part 2 uses 10 questions, Part 3 uses 40 labeled questions per threshold, and Part 4 uses only 8 held-out questions. Accuracy and latency may not generalize to larger or more difficult sets.
2. The four variant runs were executed sequentially on a local model; timings can vary with warm-up and runtime load. No uncertainty intervals or repeat-run variance were measured.
3. The threshold cost model uses assumed dollar values, not observed monetary expenditures.
4. The stale-answer demonstration is documented with retained textual evidence rather than an independently preserved complete terminal log.
5. Saved results confirm that the Part 4 test dataset and lesson file were unchanged during the comparison; the final result file records the test dataset SHA-256.
6. Reproduction requires the project's running database and Redis services, the installed local Ollama model, and the relevant Python dependencies.

For the execution narrative and related command/evidence references, see `reports/hw09/RUN_LOG.txt` and the final HW9 report.
