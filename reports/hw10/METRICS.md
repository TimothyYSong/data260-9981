# DATA 260 — Homework 10 Metrics and Experimental Results

**SID4:** 9981
**Domain:** Local Restaurant Inspection
**Kafka topic prefix:** s9981
**Judge model:** Ollama qwen3:8b
**Experiment date:** November 16, 2026

## 1. Streamlit Operations Dashboard

The Streamlit dashboard contains three pages:

- **Summary:** Recent request counts, cache hits/misses, hit rate, error rate, and end-to-end latency.
- **Evaluation:** GEval results by pipeline stage, judge-validation metrics, repeatability, and Reviewer impact.
- **Trace Lookup:** Trace-ID lookup, chronological stage records, durations, failures, evaluator scores, and benchmark statistics.

The Summary page reads `reports/hw10/request_metrics.jsonl` and offers 1-, 6-, 24-, 72-, and 168-hour windows. Its data reader uses `st.cache_data(ttl=5)`.

The Summary page measures the existing HW9 `/api/hw09/ask` endpoint. The later HW10 Kafka/evaluator path is measured separately through structured tracing and the benchmark files. These populations should not be conflated.

Cache hit rate is calculated using successfully classified hits and misses; requests failing before cache classification remain unclassified.

## 2. Automated Kafka Pipeline Evaluation

The evaluator uses GEval/DeepEval with a local Ollama `qwen3:8b` judge. Evaluation inputs preserve the original question, Planner plan, Writer draft, Reviewer final answer, and matching correlation/trace ID.

### 2.1 Recorded evaluation example

| Criterion | Score (1–5) |
|---|---:|
| Plan Quality | 3.4 |
| Writer Helpfulness | 5.0 |
| Final Answer Helpfulness | 5.0 |
| Final-vs-Draft Improvement | 0.0 |

Source: `reports/hw10/evaluation_case_03.json`.

The Writer produced a helpful response despite the Planner receiving a lower plan-quality score. The Reviewer did not change the draft, so there was no demonstrated textual improvement. The interpretation does not assume that Reviewer coordination always improves output quality.

### 2.2 Live end-to-end evaluation

**Trace ID:** `0d0a40af-21ca-4dfd-9c1e-c3e4852e6a9b`

| Criterion | Score (1–5) |
|---|---:|
| Plan Quality | 5.0 |
| Writer Helpfulness | 5.0 |
| Final Answer Helpfulness | 5.0 |
| Final-vs-Draft Improvement | 0.0 |

Source: `reports/hw10/live_evaluations/0d0a40af-21ca-4dfd-9c1e-c3e4852e6a9b.json`.

The evaluator ran with a bounded subprocess timeout and saved its results using the same trace ID as the Kafka request. The final answer was approved but did not show measurable improvement over the Writer draft.

## 3. Judge Validation

### 3.1 Experiment configuration

| Parameter | Value |
|---|---|
| Judge model | qwen3:8b |
| Temperature | 0 |
| Maximum generated tokens | 2048 |
| Evaluation cases | 20 |
| Runs per case | 3 |
| Total judge evaluations | 60 |
| Score scale | 1 + 4 × normalized GEval score |

The 20 cases and reference-label file were frozen in an earlier Git commit before the judge-validation runs.

### 3.2 Agreement and repeatability

| Metric | Result |
|---|---:|
| Spearman rank correlation | 0.894273 |
| Spearman p-value | 1.0621e-7 |
| Mean absolute difference | 0.510 |
| Cases with changed scores | 0/20 |
| Score change rate | 0.0% |
| Mean pairwise absolute change | 0.000 |
| Maximum pairwise absolute change | 0.000 |

Sources:

- `reports/hw10/judge_validation_summary.json`
- `reports/hw10/judge_validation_cases.csv`
- `reports/hw10/judge_runs/`

All 60 evaluations completed. Under the tested deterministic settings, the judge produced identical scores across the three runs of each case.

This supports repeatability under these conditions, but deterministic output does not establish that the ratings are always correct.

## 4. Distributed Tracing

### 4.1 Trace propagation

The Kafka correlation ID is reused as the trace ID across cache lookup, Kafka inbox, Planner, Writer, Reviewer, and evaluator processing.

Each structured JSON span includes a trace ID, stage, start and end timestamps, duration, status, and an error field.

Source: `reports/hw10/traces.jsonl`.

### 4.2 Required trace examples

| Path | Trace ID | Result |
|---|---|---|
| Cache hit | 50470ced-148e-44a6-86d7-b70757fb96b7 | Successful hit, no Kafka processing |
| Successful cache miss | 7c287cc0-1d2b-4c6e-a1c9-962567dbbdef | Planner, Writer, Reviewer completed |
| Evaluator-inclusive miss | 0d0a40af-21ca-4dfd-9c1e-c3e4852e6a9b | Kafka and GEval completed |
| Kafka failure | f9931c32-45ea-463b-b4f7-540e1e4d13fc | Kafka transport failure, HTTP 502 |

The failure experiment deliberately used an unavailable local Kafka endpoint. The resulting error identified the failing transport operation without stopping the production test Kafka cluster.

## 5. Stage-Latency Experiment

### 5.1 Methodology

Experiment ID: `9caacad92c`

- Start: 2026-11-16 21:33:47 UTC
- End: 2026-11-16 21:33:54 UTC
- Target: 50 confirmed cache misses
- Completed: 50 confirmed misses
- Failed attempts: 0
- Cache hits: 0
- GEval execution during benchmark: Disabled

The same inspection question was submitted with a distinct semantic-cache data version for each request. Each request was verified to be a cache miss and to complete Planner, Writer, and Reviewer processing.

This was a controlled cold-cache workload, not a test of 50 diverse questions.

### 5.2 End-to-end performance

| Metric | Result |
|---|---:|
| Mean E2E latency | 140.091 ms |
| E2E p50 | 136.750 ms |
| E2E p95 | 149.879 ms |
| Minimum E2E | 124.800 ms |
| Maximum E2E | 262.610 ms |
| Confirmed misses | 50/50 |
| Failed attempts | 0 |

### 5.3 Required stage-level results

The stage percentage is calculated as:

`100 × mean stage duration / 140.091 ms`

| Stage | Mean (ms) | p50 (ms) | p95 (ms) | Share of E2E |
|---|---:|---:|---:|---:|
| Cache lookup | 12.767 | 10.008 | 12.654 | 9.11% |
| Planner | 2.030 | 1.944 | 3.305 | 1.45% |
| Writer | 3.799 | 3.646 | 5.452 | 2.71% |
| Reviewer | 1.623 | 1.629 | 2.172 | 1.16% |
| Queue wait (total) | 9.037 | 8.303 | 12.967 | 6.45% |
| Evaluation | Not run | N/A | N/A | N/A |

Additional measured stages:

| Stage | Mean (ms) | p50 (ms) | p95 (ms) | Share of E2E |
|---|---:|---:|---:|---:|
| Inbox publication | 108.878 | 108.466 | 112.836 | 77.72% |
| Cache storage | 0.815 | 0.787 | 1.144 | 0.58% |
| Final-response wait | 10.108 | 9.626 | 14.913 | Overlapping interval |

Final-response wait overlaps Kafka agent processing and queue wait; it is not an independent additive stage and is excluded from the stage-share total.

Kafka queue wait is estimated from record creation timestamps and consumer receipt timestamps. It includes broker delivery and consumer scheduling overhead, rather than network transit alone.

### 5.4 Queue wait by consumer

| Consumer | Mean (ms) | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|
| Planner | 3.478 | 3.180 | 5.611 |
| Writer | 2.878 | 2.702 | 4.103 |
| Reviewer | 2.681 | 2.552 | 3.495 |
| Total | 9.037 | 8.303 | 12.967 |

Aggregate queue wait represented 6.451% of aggregate cache-miss E2E latency.

### 5.5 Dominant contributor and optimization

Kafka inbox publication was the dominant measured component at approximately 77.72% of average Kafka-only latency.

The current bridge constructs Kafka producer/consumer resources for each request. A first optimization would be reusing persistent Kafka clients and measuring producer initialization separately from send acknowledgement and broker overhead.

This optimization targets a measured bottleneck; it should be verified by rerunning the same benchmark after implementation.

## 6. Separate Evaluator-Inclusive Latency

The full evaluation path was measured in one successful request.

| Measurement | Duration |
|---|---:|
| Full request E2E | 65,778.63 ms |
| GEval evaluation | 65,550.77 ms |
| GEval share of full E2E | 99.65% |

Trace ID: `0d0a40af-21ca-4dfd-9c1e-c3e4852e6a9b`

GEval inference dominated evaluator-inclusive request latency. Potential improvements include a smaller or faster local model, optimized inference settings, or asynchronous evaluation outside the user-facing request path.

The evaluation result is a single observation. It is **not** a 50-run evaluation p50 or p95. The evaluator-inclusive measurement is therefore reported separately from the 50-request Kafka-only experiment.

A dedicated evaluator-inclusive repeated-run experiment would be required to estimate evaluation-stage p50 and p95 reliably.

## 7. Machine-Readable Evidence

- `reports/hw10/hw10_benchmark_50.csv`
- `reports/hw10/hw10_benchmark_summary.json`
- `reports/hw10/judge_validation_cases.csv`
- `reports/hw10/judge_validation_summary.json`
- `reports/hw10/judge_runs/`
- `reports/hw10/evaluation_case_03.json`
- `reports/hw10/live_evaluations/`
- `reports/hw10/traces.jsonl`
- `reports/hw10/request_metrics.jsonl`

All reported experimental values above are drawn from the recorded HW10 outputs. No missing evaluator percentile is imputed.
