# Homework 2 Metrics

## Schema Validation Experiment

| Outcome over 30 runs | Count | Mean Latency (ms) |
|---|---:|---:|
| Valid first attempt | 30 | 16938.84 |
| Valid after 1 retry | 0 | N/A |
| Valid after 2+ retries | 0 | N/A |
| Hit turn ceiling | 0 | N/A |

## Turn Ceiling Comparison

| Turn Ceiling | Runs | Completed | Completion Rate | Mean Latency (ms) |
|---|---:|---:|---:|---:|
| 2 | 20 | 0 | 0% | 9699.24 |
| 10 | 20 | 20 | 100% | 16958.60 |

## Adversarial Experiment

| Runs | Ceiling Hits | Ceiling-Hit Rate |
|---:|---:|---:|
| 5 | 0 | 0% |