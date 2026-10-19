# DATA 260 — Homework 6 Metrics

**Student:** Timothy Song  
**SJSU ID suffix (SID4):** 9981  
**Date:** October 19, 2026  
**Domain:** Local restaurant inspections (`DOMAIN_ID=5`)  
**Hardware:** MacBook Pro M4 Pro (14 CPU cores, 24 GB RAM)  
**Models:** Ollama `qwen3:8b` (chat / summaries / fact extraction); `nomic-embed-text` (768-dimensional embeddings)  
**Configuration:** `PORT_BASE=8081`, `PREFIX=s9981`, `SEED=9981`, `VERIFY_SEED=269981`  
**MongoDB database:** `s9981_doc`

This file records the observed HW6 results, not projected test outcomes. The Part 3 model-usage data and cost figures below are calculated from the saved per-request raw experiment JSON; the Part 1, Part 2 and Part 4 test outcomes are supported by the report and recorded terminal evidence in `RUN_LOG.txt`.

## Part 1 — MongoDB Document API and Validation

| Test / behavior | Recorded result |
|---|---|
| Create inspection (`POST /api/inspections`) | HTTP 201 Created |
| Retrieve all inspections (`GET /api/inspections`) | HTTP 200 OK |
| Retrieve inspection by ID (`GET /api/inspections/{inspection_id}`) | HTTP 200 OK |
| Replace inspection (`PUT /api/inspections/{inspection_id}`) | HTTP 200 OK; creation timestamp preserved, update timestamp refreshed |
| Delete inspection (`DELETE /api/inspections/{inspection_id}`) | HTTP 200 OK; subsequent MongoDB lookup returned `null` |
| Malformed inspection ID | HTTP 400 Bad Request |
| Nonexistent inspection | HTTP 404 Not Found |
| Missing required data / invalid types, lengths, enums or dates | HTTP 422 validation errors |
| MongoDB unavailable (intentional failure test) | HTTP 500 Internal Server Error |
| CORS preflight for React origin | HTTP 200 OK |

**Evidence:** `reports/hw06/report.pdf`, Part 1 (Figures 1–21). These are observed HTTP outcomes, not aggregate benchmark latency or throughput figures; no Part 1 throughput experiment was required.

## Part 2 — Short-Term, Long-Term and Episodic Memory

| Measurement / check | Recorded result |
|---|---|
| MongoDB memory collections | `messages`, `summaries`, `episodes` created in `s9981_doc` |
| Main demonstration | 10 user requests in one session, producing 10 assistant replies (20 stored conversation messages) |
| Short-term memory | Configurable last-`N` messages per user/session (default `SHORT_TERM_N=12`) |
| Session summaries | Generated every 5 user turns in the demonstration; 2 session summaries observed |
| Lifetime summary mechanism | Implemented; triggered after multiple session summaries, not claimed as produced by the single-session demonstration |
| Episodic facts | Embedded with `nomic-embed-text`; retrieval by cosine similarity, top `k=3` |
| Chat endpoint | `POST /api/chat` returned a reply and `memory_used` |
| Memory endpoint | `GET /api/memory/{user_id}` tested |
| Aggregate endpoint | `GET /api/aggregate/{user_id}` tested |

**Evidence:** `reports/hw06/raw/part2_ten_turns_1792395654.jsonl` (10 saved API responses); report Figures 22–46. The 3-response partial run (`part2_ten_turns_1792395309.jsonl`) is retained separately as diagnostic evidence and is not counted as the completed 10-turn test.

## Part 3 — What Memory Costs

### 3.1 Token and Latency Instrumentation

Every *completed* `/api/chat` call logs its UTC timestamp, model, user/session, memory setting, prompt and completion token counts, end-to-end latency, and estimated component contributions into `reports/hw06/raw/memory_usage.jsonl`.

Example actual log record from the initial instrumentation check:

| Metric | Value |
|---|---:|
| Model-reported prompt tokens | 109 |
| Model-reported completion tokens | 243 |
| System primer tokens (estimated) | 73 |
| Long-term summary tokens (estimated) | 8 |
| Short-term window tokens (estimated) | 2 |
| Current user message tokens (estimated) | 14 |
| Episodic facts tokens (estimated) | 2 |
| Request latency | 19,236.10 ms |

**Measurement method:** `prompt_tokens` and `completion_tokens` come from the Ollama/LangChain model response metadata. The component token fields use a *rough* four-characters-per-token calculation, **not** the model tokenizer; they should not be treated as exact or assumed to sum to the model-reported prompt token count. Latency covers the endpoint's full processing, including supporting memory operations. The token costs in Section 3.5 cover the primary model response only (not separate summarization, extraction or embedding operations). Failed calls that do not finish logging are not included.

### 3.2 Five Fixed Memory Probes

The five questions and their expected fact criteria are defined in the repository-root `memory_probes.yaml`. Each probe was scored on a **1–5** rubric. Scores from the experiment runner are **preliminary automated keyword scores**; reviewed scores were obtained by checking actual responses against the same two-fact expectations.

| Probe | Expected information | Seed turns |
|---|---|---|
| P1 | Oakland; routine restaurant inspections | 1, 2 |
| P2 | Cross-contamination; pest activity | 7, 9 |
| P3 | Last 12 months; comparison of multiple restaurants | 14, 16 |
| P4 | Concise bullet points; repeat violation counts | 21, 23 |
| P5 | Temescal; most recent routine inspection date first | 26, 28 |

### 3.3 Short-Term Memory Window Sweep and 3.4 Eviction

**Experiment design:** Each setting used the same fixed 30-message conversation in a fresh user/session, followed by the same five probes. There were **30 conversation turns and 5 probe calls per setting**, or **120 conversation turns plus 20 probes across all four configurations**. The reported token and latency means use *only the first 30 conversation turns* of each run, while quality averages use the five subsequent probes.

| Setting | Mean prompt tokens/turn | Mean completion tokens/turn | Mean latency (ms) | Automated quality (1–5) | Reviewed quality (1–5) |
|---|---:|---:|---:|---:|---:|
| `N=4` | 2,166.17 | 1,018.93 | 42,648.34 | 3.60 | **3.60** |
| `N=12` | 1,848.50 | 1,113.67 | 45,597.09 | 3.80 | **3.40** |
| `N=30` | 1,839.27 | 1,071.23 | 44,651.92 | 4.20 | **4.00** |
| `N=12 + eviction` | 441.37 | 560.40 | 24,382.33 | 4.00 | **4.20** |

**Per-probe quality scoring (manual review):**

| Setting | P1 | P2 | P3 | P4 | P5 | Mean |
|---|---:|---:|---:|---:|---:|---:|
| `N=4` | 5 | 5 | 3 | 2 | 3 | **3.60** |
| `N=12` | 2 | 5 | 4 | 3 | 3 | **3.40** |
| `N=30` | 5 | 5 | 3 | 4 | 3 | **4.00** |
| `N=12 + eviction` | 5 | 5 | 5 | 3 | 3 | **4.20** |

**Eviction policy:** With `SHORT_TERM_N=12`, `HW6_MEMORY_POLICY=evict_assistant` excludes historical assistant replies from the short-term prompt window while retaining user messages, MongoDB records, summaries and episodic memory.

| Comparison metric | N=12 baseline | N=12 with assistant-message eviction | Change |
|---|---:|---:|---:|
| Mean input/prompt tokens per conversation turn | 1,848.50 | 441.37 | **-1,407.13** (76.12% fewer) |
| Mean request latency (ms) | 45,597.09 | 24,382.33 | **-21,214.76 ms** (46.53% decrease) |
| Mean reviewed probe quality (1–5) | 3.40 | 4.20 | **+0.80** points |

The observed quality increase is specific to this experiment, not a guarantee of better recall across arbitrary conversations. Several actual model answers contained unsupported inspection details, so the probe rubric measures recall of requested facts rather than general factual accuracy. Prompt-token averages are not monotonic in N because the assembled prompts and generated memory summaries can differ between independently executed runs.

**Source files:** `raw/sweep_n4_1792399369.json`, `raw/sweep_n12_1792401498.json`, `raw/sweep_n30_1792401498.json`, `raw/eviction_n12_1792435165.json`, `raw/short_term_sweep_summary.json`, `raw/eviction_probe_review.json`, and `raw/memory_usage.jsonl`, all relative to `reports/hw06/`.

### 3.5 Cost Projection for 10,000 Conversations

**Pricing assumption:** $1.00 per million input tokens and $5.00 per million output tokens. Every conversation contains 30 user turns. Cost uses the measured 30-turn input and output totals for each setting; probe calls are excluded.

`Cost per 30-turn conversation = (input_tokens × $1 + output_tokens × $5) / 1,000,000`

`Projected 10,000-conversation cost = cost_per_conversation × 10,000`

| Setting | 30-turn input tokens | 30-turn output tokens | Cost / 30-turn conversation | Cost / 10,000 conversations | Reviewed probe quality |
|---|---:|---:|---:|---:|---:|
| `N=4` | 64,985 | 30,568 | $0.217825 | **$2,178.25** | 3.60 |
| `N=12` | 55,455 | 33,410 | $0.222505 | **$2,225.05** | 3.40 |
| `N=30` | 55,178 | 32,137 | $0.215863 | **$2,158.63** | 4.00 |
| `N=12 + eviction` | 13,241 | 16,812 | $0.097301 | **$973.01** | 4.20 |

**Best by reviewed recall quality:** `N=12 + eviction` (quality 4.20/5; projected cost **$973.01**).  
**Worst by reviewed recall quality:** `N=12` without eviction (quality 3.40/5; projected cost **$2,225.05**).  
**Eviction cost reduction versus N=12 baseline:** **$1,252.04** (56.27%) per 10,000 conversations.

These are hypothetical hosted-model equivalents from local `qwen3:8b` run statistics, not charges incurred or a complete system-cost estimate. Separate fact extraction, summarization and embedding token usage was not included in the projected primary-inference cost. No paid hosted-model run was performed.

**Cost data:** `reports/hw06/raw/memory_cost_table.json`; script: `code/calculate_memory_cost.py`.

## Part 4 — File-Based Memory and Consolidation

### 4.1–4.4 File Memory and Command Tests

| Check | Observed result |
|---|---|
| `AGENT.md` instructions | 8 instructions spanning all 5 assignment categories; prior HW1 bullet-only review instruction retained |
| `MEMORY.md` | Durable Markdown facts with `last_consolidated` metadata |
| File loader and model prompt | Both Markdown files loaded and included in prompt; direct tests passed |
| Consolidation thresholds | Exactly 40 qualifying lines with recent timestamp: no trigger; 41 lines: trigger; timestamp over 24 hours: trigger |
| Part 4.2 function checks | 7 PASS messages in terminal test |
| `/help` and `/memory` | Function tests passed; both also passed through `POST /api/chat` |
| `/compact` | Temporary-file function test passed and reported before/after counts; actual 55-line consolidation run documented below |
| `/dream` | Temporary-file test with stored episodic facts mocked: new durable fact added |
| AGENT.md-compliant sample function | `format_inspection_record()` tested with valid and invalid input, snake_case, type hints, docstring, and no invented dates or violations |

### 4.5 Consolidation Experiment

| Measurement | Result |
|---|---:|
| Original `MEMORY.md` physical lines | 55 |
| Original qualifying non-comment lines | 54 |
| Original memory fact entries | 52 |
| Distinct duplicated facts constructed | 3 |
| Deliberately contradictory fact pairs | 3 |
| Duplicate entries removed during automatic consolidation | 30 |
| Automatic-consolidation fact entries | 19 |
| Automatic-consolidation physical lines | 29 |
| Automatic-consolidation qualifying lines | 25 |
| Incorrect automatic contradiction resolutions | 3 |
| Explicit manual corrections | 3 |
| Final corrected physical lines | **32** |
| Final qualifying non-comment lines | **28** |
| Requirement: fewer than 40 lines | **PASS** |

**Incorrect automatic resolutions identified and corrected:**

| Fact key | Incorrect value retained by automatic latest-entry rule | Correct value restored |
|---|---|---|
| `priority_city` | Berkeley | Oakland |
| `inspection_type` | complaint | routine |
| `report_format` | long paragraphs | concise bullet points |

The initial automated resolution log and the final correction notes remain in the consolidated file; conflicting entries were **not silently discarded**. The initial and final versions, including the original 55-line file, are preserved at `reports/hw06/raw/MEMORY_original_55.md`, `MEMORY_initial_consolidated.md`, and `MEMORY_consolidated.md`, respectively.

| Git commit | Preserved content |
|---|---|
| `f7c2363` | Original 55-line `MEMORY.md` |
| `0fc7dda` | Corrected 32-line `MEMORY.md` and versioned evidence |

### 4.6 Comparison of Both Systems

| Criterion | MongoDB-backed memory | File-based memory |
|---|---|---|
| Inspectability | Structured queries and MongoDB Compass | Plain Markdown inspection and editing |
| Persistence | Durable if the MongoDB storage is preserved | Durable on disk; Git provides version history |
| Scalability | Better suited to many users and session-specific records | Simpler but less suitable for large numbers of users/sessions using shared files |
| Facts that must not be forgotten | Persistent data; retrieval depends on selection/query logic | Stable instructions and facts inserted directly in prompts; manual review protects against consolidation mistakes |

**Conclusion:** A hybrid approach is appropriate: MongoDB stores scalable conversation and episodic data while `AGENT.md` and `MEMORY.md` provide directly inspectable, version-controlled durable instructions and stable facts.

## Evidence and Scope

- **Real run output:** `reports/hw06/RUN_LOG.txt` and console logs `part3_sweep_console.log`, `part34_eviction_console.log`, and `part35_cost_console.log`.
- **Raw experiment measurements:** `reports/hw06/raw/` (the sweep, eviction, per-turn usage and cost JSON/JSONL records).
- **Probe definition:** root `memory_probes.yaml`; score outputs in the experiment JSON files and `raw/eviction_probe_review.json`.
- **Implementation:** `code/memory_metrics.py`, `code/run_memory_sweep.py`, `code/run_eviction_test.py`, `code/calculate_memory_cost.py`, `code/file_memory.py`, `code/file_memory_commands.py`, and `code/chat_prompt.py`.
- **Observed screenshots and narrative:** `reports/hw06/report.pdf`.
- **Model and deployment:** local inference with Ollama, no paid-hosted-model comparison. Any final tagged-commit smoke test and its `verification.json` are distinct submission requirements and are not claimed to have been completed by this metrics file.
