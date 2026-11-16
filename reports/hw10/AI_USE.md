# DATA 260 — Homework 10 AI Use Disclosure

**SID4:** 9981
**Domain:** Local Restaurant Inspection

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT to help plan, implement, debug, and document Homework 10. This included generating and revising Python code for the Streamlit dashboard, GEval integration, judge validation, distributed tracing, Kafka request handling, performance benchmarking, and repository verification. I also used an AI/LLM assistant to generate the 20 reference helpfulness labels for Part 3, which the assignment does not allow (see question 2). I used Claude (Anthropic) to draft this written report from my saved evidence files (metrics, traces, judge outputs, benchmark CSVs, and dashboard screenshots) and to produce the charts in Figures 5, 8, 9, and 10 from those files.

I operated the development environment, executed commands, ran the Kafka and Redis services, collected experimental outputs, inspected terminal errors, tested API endpoints, captured the dashboard screenshots, and reviewed the dashboard and performance measurements. All results come from running the implementation in my local environment. No measurements were invented.

## 2. What was one AI-produced output that was wrong or unsuitable, or one result you independently verified?

The Part 3 reference labels in `human_labels.csv` were generated with an AI/LLM assistant rather than assigned by hand. The labels themselves looked plausible, but using them was unsuitable: Part 3 requires human reference labels and explicitly says not to generate them with an LLM. I carried the LLM-judging approach from Part 2 into Part 3 and did not notice that rule until after the judge had already scored the cases.

Separately, an AI-generated verification script expected the judge-validation summary to contain `judge_runs == 3`, but the experiment had 20 cases with three judge evaluations each (60 in total).

## 3. How did you detect or verify the problem?

I found the label problem when rereading the Part 3 requirements after the judge runs were complete. My own validation script also recorded `reference_label_provenance` as an item that had to be documented accurately in the report.

For the verification script, I ran it and inspected the failed assertion. I compared it with `judge_validation_summary.json` and `judge_validation_cases.csv`, which recorded 20 cases, 60 evaluations, and three non-null judge scores per case. I also recomputed the Spearman correlation and MAD from the per-case CSV with `scipy.stats.spearmanr`, and they matched the saved summary.

## 4. What did you change, and why does it work now?

The handout forbids relabeling after seeing judge results, and I did not have time to collect and hand-label a fresh case set before the deadline, so I did not replace the labels. Instead, I disclose their provenance in Part 3.1 and describe the results as agreement between the judge and an LLM-generated reference, not human validation. I kept the dashboard warning that states the same limitation (Figure 3), and I list genuine human labels on a fresh case set as the first evidence required before trusting the judge. The report now describes accurately what the experiment does and does not show.

I corrected the verification assertion to check for 20 distinct cases, three non-null judge predictions per case, and 60 total evaluations, and the corrected check passed. The check now matches the real experiment design.
