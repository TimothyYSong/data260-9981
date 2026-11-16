# DATA 260 — Homework 10 AI Use Disclosure

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT to help plan, implement, debug, and document Homework 10.
This included generating and revising Python code for the Streamlit
dashboard, GEval integration, judge validation, distributed tracing,
Kafka request handling, performance benchmarking, and repository
verification. I also used an AI/LLM assistant to generate the 20
reference helpfulness labels for Part 3, which the assignment does not
allow (see question 2). I used Claude (Anthropic) to draft this written
report from my saved evidence files (metrics, traces, judge outputs,
benchmark CSVs, and dashboard screenshots) and to produce the charts in
Figures 4, 7, 8, and 9 from those files.

I operated the development environment, executed commands, ran the Kafka
and Redis services, collected experimental outputs, inspected terminal
errors, tested API endpoints, and reviewed the dashboard and performance
measurements. All results come from running the implementation in my
local environment. No measurements were invented.

**Part 3 reference labels.** The helpfulness labels in human_labels.csv
were generated with an AI/LLM assistant rather than assigned by hand.
The output itself looked plausible, but using it was unsuitable: Part 3
requires human reference labels and explicitly says not to generate them
with an LLM. I carried the LLM-judging approach from Part 2 into Part 3
and did not see that rule until after the judge had already scored the
cases.

**Verification script.** Separately, an AI-generated verification script
expected the judge-validation summary to contain judge_runs == 3, but
the experiment had 20 cases with three judge evaluations each (60 in
total). An unavailable Kafka connection also initially caused the API to
return HTTP 400 (client error) instead of a server-side failure status.

An AI-generated verification script expected the judge-validation
summary to contain judge_runs == 3. The experiment actually consisted of
20 cases with three judge evaluations per case, for 60 total.
Separately, an unavailable Kafka connection initially caused the API to
return HTTP 400 (client error) rather than a server-side failure status.

I found the label problem when rereading the Part 3 requirements after
the judge runs were complete. My own validation script also recorded
reference_label_provenance as an item that had to be documented
accurately. For the verification script, I ran it, inspected the failed
assertion, and compared it with judge_validation_summary.json and
judge_validation_cases.csv, which showed 20 cases and three non-null
judge scores per case. For the Kafka failure, I pointed the HW10 API at
an intentionally unavailable Kafka port and inspected the HTTP response
and the recorded error span. The Spearman correlation and MAD in this
report were also recomputed independently from the per-case CSV.

For judge validation, I ran the audit script, inspected the failed
assertion, and compared it with judge_validation_summary.json and
judge_validation_cases.csv. The summary recorded 20 cases and 60
evaluations, and the CSV contained three non-null judge scores per case.
For the Kafka failure, I pointed the HW10 API at an intentionally
unavailable Kafka port and inspected the actual HTTP response and the
recorded error span. The Spearman correlation and MAD in this report
were also recomputed independently from the per-case CSV.

The handout forbids relabeling after seeing judge results, and I did not
have time to collect and hand-label a fresh case set before the
deadline. I therefore did not replace the labels. Instead I disclose
their provenance in Part 3, describe the results as agreement between
the judge and an LLM-generated reference rather than human validation,
keep the dashboard warning that states the same limitation, and list
genuine human labels on a fresh case set as the first evidence required
before trusting the judge. I also corrected the verification assertion
to check 20 cases, three predictions each, and 60 evaluations, and it
passed. I changed the Kafka bridge to treat the transport-level
ValueError as a server-side failure, and the re-run failure test (trace
f9931c32…) returned HTTP 502 with the matching trace ID and error.

I corrected the assertion to check for 20 distinct cases, three non-null
judge predictions per case, and 60 total evaluations, and the corrected
verification passed. I changed the Kafka bridge to treat the
transport-level ValueError as a server-side runtime failure. The re-run
failure test (trace f9931c32…) returned HTTP 502 with the matching trace
ID and Kafka error. Both fixes make the checks match the real experiment
design and separate infrastructure failures from invalid client
requests.

## 2. Identify an AI-produced output that was wrong or unsuitable, or something independently verified.

One AI-generated verification script incorrectly expected the judge-validation summary to contain `judge_runs == 3`.

The experiment actually consisted of 20 evaluation cases with three judge evaluations per case, producing 60 total judge evaluations.

Another issue appeared during distributed tracing: an unavailable Kafka connection initially caused the API to return HTTP 400 rather than the appropriate server-side failure status.

## 3. How did you detect the problem or verify the result?

For judge validation, I executed the audit script and inspected its failed assertion. I then compared the assertion against the saved `judge_validation_summary.json` and `judge_validation_cases.csv` files.

The summary recorded 20 distinct cases and 60 total judge evaluations. The per-case CSV contained three completed judge predictions for every case.

For the Kafka failure, I tested the HW10 API using an intentionally unavailable Kafka port and inspected its actual HTTP response and recorded error span.

## 4. What did you change, and why does it work now?

I corrected the judge-validation assertion to verify 20 distinct cases, three non-null judge predictions per case, and 60 total evaluations. The corrected verification passed.

I also changed the Kafka bridge to classify the transport-level `ValueError` as a server-side runtime failure. A subsequent failure test returned HTTP 502 and preserved the matching trace ID and Kafka error.

These corrections align the verification criteria with the actual experiment design and distinguish infrastructure failures from invalid client requests.
