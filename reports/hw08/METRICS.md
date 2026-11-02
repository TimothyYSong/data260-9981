# DATA 260 — Homework 8 Metrics

**SID4:** 9981  
**PREFIX:** `s9981`  
**SEED:** 9981  
**VERIFY_SEED:** 269981  
**Domain:** Local Restaurant Inspections  
**Evidence source:** Recorded execution in `reports/hw08/RUN_LOG.txt` and experiment files in `reports/hw08/raw/`. Results below summarize the prior runs; no new Kafka tests were performed to create this document.

## Part 1 — Kafka Backend Request/Response

| Check | Recorded result | Outcome | Evidence |
|---|---|---|---|
| `CREATE_INSPECTION` | Worker returned `success: true` and generated inspection UUID `2473033f-0b19-457c-b2fa-30071989a84e` | PASS | `raw/part1_message_flow.txt` |
| `GET_INSPECTION` | Retrieved the entity with the same inspection UUID and recorded restaurant fields | PASS | `raw/part1_message_flow.txt` |
| CREATE correlation ID | Request and response both used `2ba46f4e-dd0b-44ac-bd6e-06801e12fa00` | PASS | `raw/part1_message_flow.txt` |
| GET correlation ID | Request and response both used `a85ffa6f-169e-4753-abe8-3f5bf7e2d790` | PASS | `raw/part1_message_flow.txt` |
| End-to-end CREATE → GET round trip | Demo logged `CREATE -> GET round trip: PASS` | PASS | `RUN_LOG.txt`, Part 1 |
| Worker message handling | Both operations logged request received, operation processed, response sent | PASS | `raw/part1_worker_flow.txt` |

**Interpretation:** Each independent Kafka request retained its own correlation ID; the generated *inspection ID* was carried from CREATE into GET. No throughput or latency benchmark was conducted.

## Part 2 — Three-Agent Kafka Pipeline

| Stage | Input topic | Output topic | Recorded result |
|---|---|---|---|
| Question producer | — | `s9981_inbox` | Question published |
| Planner | `s9981_inbox` | `s9981_tasks` | Three-step inspection plan published |
| Writer | `s9981_tasks` | `s9981_drafts` | Draft answer published |
| Reviewer | `s9981_drafts` | `s9981_final` | Final JSON with `status: approved` and nonempty `answer` published |

| Check | Recorded result | Outcome |
|---|---|---|
| Topics in message journey | 4 / 4 | PASS |
| Separate agent roles observed | Planner, Writer, Reviewer | PASS |
| Correlation ID preservation across stages | `da401bf5-0ad9-4fb5-a3f2-f8180aa0e7c8` unchanged in all four topic messages | PASS |
| Final message | JSON includes original correlation ID, `status: approved`, and answer | PASS |

**Evidence:** `raw/part2_agent_logs.txt`, `raw/part2_message_journey.txt`, and `raw/part2_final.json`.

## Part 3 — Failure Experiments

| Scenario | Before fix — observed | After fix — observed | Result |
|---|---|---|---|
| Duplicate delivery | 2 deliveries of same correlation ID → **2 drafts published** | 2 deliveries → **1 draft published**, **1 duplicate skipped** | PASS for in-process replay |
| Consumer killed mid-work | Writer terminated after beginning task at partition 0, offset 3; task not committed before termination | Restarted Writer received same correlation ID, published draft, logged commit of message offset 3; recorded recovery check showed lag cleared | PASS |
| Poison message | Task without `steps` crashed Writer with `KeyError` | **3 attempts**, **1 dead-letter publication** to `s9981_dead_letter`; following valid task published and committed | PASS |
| Two partitions / two Writers | 20 related messages split **10** on partition 0 and **10** on partition 1 | 20 related messages routed to partition 1, processed sequences **1–20** in order by one Writer | PASS |

### Part 3.I — Duplicate Delivery

| Metric | Before | After |
|---|---:|---:|
| Input deliveries tested | 2 | 2 |
| Drafts published | 2 | 1 |
| Duplicate deliveries skipped | 0 | 1 |
| Extra draft publications from replay | 1 | 0 |

**Evidence:** `raw/part3_duplicate_before.txt`; `raw/part3_duplicate_after.txt`.

**Scope:** The implementation uses a per-process in-memory `processed_ids` set. This experiment does **not** demonstrate durable idempotency across restarts or shared idempotency across multiple Writers.

### Part 3.II — Consumer Death / Offset Recovery

| Measurement | Recorded value |
|---|---|
| Killed task correlation ID | `6f145446-d7ca-4fb3-b614-47ec84fbeda3` |
| Kafka topic partition / message offset | `s9981_tasks`, partition 0, offset **3** |
| Crash evidence | `PROCESSING LOG DETECTED`; `WRITER KILLED DURING PROCESSING` |
| Restart evidence | Same correlation ID received, draft published, `WRITER OFFSET COMMITTED ... offset=3` |
| Recovery observation | Consumer group advanced to next offset **4**, clearing the one-message lag (captured during test) |
| Later final consumer-group snapshot | Partition 0: current/end **16/16**, lag **0**; partition 1: **33/33**, lag **0** |

**Evidence:** `raw/part3_consumer_death_crash.txt`; `raw/part3_consumer_death_after.txt`; `raw/part3_consumer_offsets_final.txt`. The **final** zero-lag snapshot was taken after subsequent ordering experiments; it is not the immediate post-crash snapshot. The original `raw/part3_consumer_death_before.txt` is empty and is not used as supporting evidence.

### Part 3.III — Poison Message / Dead Letter

| Metric | Recorded result |
|---|---|
| Invalid input | `steps` field missing |
| Before-fix behavior | Writer `KeyError: 'steps'` |
| Configured maximum attempts | **3** |
| Logged retry attempts | **1/3**, **2/3**, **3/3** |
| Dead-letter publications recorded | **1** (`s9981_dead_letter`) |
| Subsequent valid task | Received, draft published, offset committed |

**Evidence:** `raw/part3_poison_before.txt`; `raw/part3_poison_after.txt`; `raw/part3_poison_valid_after.txt`.

### Part 3.IV — Related-Message Ordering

**Test parameters:** `VERIFY_SEED=269981`, `entity_id=restaurant-9981`, 20 messages per run, `s9981_tasks` configured with two partitions, two Writer instances in group `s9981_writers`.

| Metric | Before entity key | After entity key |
|---|---:|---:|
| Related messages sent | 20 | 20 |
| Partition 0 messages | 10 | 0 |
| Partition 1 messages | 10 | 20 |
| Partitions used | 2 | 1 |
| Writer instances handling these messages | 2 | 1 |
| All 20 related messages preserved in a single partition in sequence | No | Yes (1 through 20) |
| Observed partition 1 offsets for this run | 3–12 | 13–32 |

**Baseline methodology:** The unkeyed baseline **explicitly assigned partitions** using a 20-message, seeded shuffle (10 messages per partition); it does **not** measure Kafka's default unkeyed partitioner. In the after-key run, all 20 messages used the same entity key and no explicit partition assignment.

**Evidence:** `raw/part3_ordering_before.csv`, `raw/part3_ordering_after.csv`, `raw/part3_ordering_before_logs.txt`, `raw/part3_ordering_after_clean.txt`.

## Measurement Limitations

- These are observed functional counts and outcomes, **not** a throughput, average-latency, or load benchmark. No unmeasured performance figures are asserted.
- Kafka partition ordering does not imply a global order across multiple partitions.
- A zero-lag consumer-group snapshot shows the observed group was caught up at that moment, not a perpetual guarantee of exactly-once processing.
- Data and timestamps were taken from the prior saved logs and CSVs; this report was not generated from a new execution.