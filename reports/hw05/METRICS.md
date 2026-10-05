# Homework 5 Metrics

Student: Timothy Song  
SID4: 9981  
Domain: Local Restaurant Inspections  
PORT_BASE: 8081  
PREFIX: s9981  
SEED: 9981  
VERIFY_SEED: 269981  

## Part 3 - Retry and Failure Injection Metrics

The storage-operation retry policy used a maximum of 3 attempts, a 2.0-second timeout per attempt, and bounded exponential backoff beginning at 0.10 seconds.

A reproducible failure-injection experiment was run using VERIFY_SEED = 269981.

For each failure rate, 50 calls were executed, for a total of 150 calls.

| Failure Rate | Calls | Success Rate | Mean Latency (ms) | P99 Latency (ms) |
|---:|---:|---:|---:|---:|
| 0% | 50 | 100.0% | 2.305 | 3.079 |
| 20% | 50 | 100.0% | 39.858 | 312.882 |
| 50% | 50 | 86.0% | 85.292 | 312.372 |

Raw failure-injection call records are stored in:

`reports/hw05/raw/fault_injection_calls.csv`

### Retry Policy Evaluation

At a 0% injected failure rate, all calls succeeded with very low latency.

At a 20% injected failure rate, the retry policy maintained a 100% success rate, but mean and p99 latency increased because some requests required retries.

At a 50% injected failure rate, the success rate decreased to 86.0%, while mean latency increased to 85.292 ms and p99 latency reached 312.372 ms.

For interactive requests, the current maximum of 3 attempts and short bounded backoff provide a reasonable balance between reliability and response time. For batch workloads, additional retries and longer timeouts could be considered because latency is less sensitive.

## Part 4 and Part 5 - Offline Test Metrics

The Part 4 offline domain-tool test suite originally contained 6 tests.

After adding the two required Part 5 tests, the complete offline suite contained 8 tests.

| Test Suite | Passed | Total | Pass Rate |
|---|---:|---:|---:|
| Part 4 + Part 5 Offline Tests | 8 | 8 | 100% |

The two Part 5 tests verify:

1. `execute_tool` blocks a call that violates the domain safety rule.
2. `run_agent` using `MockModel` stops after reaching `max_steps`.

These tests run without an API key, live Ollama model, external API, or live database.

## Part 5 - Agent Metrics

Local model: `qwen3:8b`

Four scenarios were run using the local Ollama model.

| Scenario | Prompt | Step Count | Tool-Call Count | Stop Reason |
|---|---|---:|---:|---|
| 1 | Find Restaurant 12 and summarize its inspection history. | 2 | 1 | `normal_completion` |
| 2 | Search for Restaurant 20 and tell me about one inspection. | 2 | 1 | `normal_completion` |
| 3 | Give me the inspection details for inspection 10016. | 2 | 1 | `normal_completion` |
| 4 | Summarize the inspection history for restaurant 5001. | 1 | 1 | `safety_rule_block` |

### Agent Metrics Summary

Scenarios 1 through 3 completed normally in 2 steps with 1 tool call each.

Scenario 4 requested a summary for `restaurant_id = 5001`. This violated the domain safety rule and stopped after 1 step with 1 tool call and the stop reason `safety_rule_block`.

Agent execution logs are stored in:

`reports/hw05/raw/agent_runs.jsonl`

A hosted-model comparison was not performed because it was optional.