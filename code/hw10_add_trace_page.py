"""Add Part 1.3 Trace Lookup without replacing existing pages."""

from pathlib import Path

path = Path("code/hw10_dashboard.py")
source = path.read_text()

old_menu = '["Summary", "Evaluation"],'
new_menu = '["Summary", "Evaluation", "Trace Lookup"],'

assert source.count(old_menu) == 1
source = source.replace(old_menu, new_menu, 1)

old_branch = 'else:\n    st.subheader("Part 2 — Pipeline evaluation")'
new_branch = 'elif page == "Evaluation":\n    st.subheader("Part 2 — Pipeline evaluation")'

assert source.count(old_branch) == 1
source = source.replace(old_branch, new_branch, 1)

trace_page = '''

else:
    st.subheader("Part 1.3 — Distributed Trace Lookup")

    trace_path = PROJECT_ROOT / "reports" / "hw10" / "traces.jsonl"
    reports_dir = PROJECT_ROOT / "reports" / "hw10"

    @st.cache_data(ttl=5)
    def load_spans(path, modified_ns):
        records = []
        invalid = 0
        file_path = Path(path)

        if file_path.exists():
            for line in file_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise ValueError("Not a JSON object")
                    if not item.get("trace_id"):
                        raise ValueError("Missing trace ID")
                    records.append(item)
                except (ValueError, TypeError):
                    invalid += 1

        return records, invalid

    modified_ns = (
        trace_path.stat().st_mtime_ns
        if trace_path.exists()
        else 0
    )

    spans, invalid_count = load_spans(
        str(trace_path), modified_ns
    )

    st.caption(
        f"Source: {trace_path} | "
        "Cache refresh: 5 seconds | "
        "Times displayed in UTC"
    )

    if not spans:
        st.warning("No distributed tracing records found.")
        st.stop()

    trace_ids = sorted(
        {span["trace_id"] for span in spans},
        key=lambda tid: max(
            s.get("start_time", "")
            for s in spans
            if s["trace_id"] == tid
        ),
        reverse=True,
    )

    st.caption(
        f"Available traces: {len(trace_ids)} | "
        f"Recorded spans: {len(spans)} | "
        f"Malformed records: {invalid_count}"
    )

    selected_id = st.text_input(
        "Trace ID",
        value=trace_ids[0],
        help="Paste an API response trace_id to inspect its journey.",
    ).strip()

    if selected_id not in trace_ids:
        st.warning("Trace ID not found in the tracing file.")
        st.stop()

    journey = sorted(
        [
            span for span in spans
            if span["trace_id"] == selected_id
        ],
        key=lambda s: (
            s.get("start_time", ""),
            s.get("end_time", ""),
        ),
    )

    cache_spans = [
        span for span in journey
        if span.get("stage") == "cache_lookup"
    ]

    cache_result = (
        cache_spans[-1].get("cache_result", "unknown")
        if cache_spans
        else "not recorded"
    )

    failed = [
        span for span in journey
        if span.get("status") == "error"
    ]

    queue_spans = [
        span for span in journey
        if span.get("stage") == "queue_wait"
    ]

    evaluation_spans = [
        span for span in journey
        if span.get("stage") == "evaluation"
    ]

    total_queue = sum(
        float(span.get("duration_ms", 0))
        for span in queue_spans
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Cache result", cache_result.upper())
    c2.metric("Recorded spans", len(journey))
    c3.metric("Total queue wait", f"{total_queue:.2f} ms")
    c4.metric("Failed spans", len(failed))

    if cache_result == "hit":
        st.success(
            "Cache hit: downstream Kafka agents were not "
            "required for this request."
        )
    elif cache_result == "miss":
        st.info(
            "Cache miss: inspect the Kafka stages below "
            "for the full request journey."
        )

    if failed:
        st.error(
            "At least one stage failed. "
            "Inspect its error details below."
        )

    st.subheader("Chronological request journey")

    rows = []

    for position, span in enumerate(journey, 1):
        rows.append({
            "Order": position,
            "Stage": span.get("stage"),
            "Consumer": span.get("consumer_stage", ""),
            "Start (UTC)": span.get("start_time"),
            "End (UTC)": span.get("end_time"),
            "Duration (ms)": span.get("duration_ms"),
            "Status": span.get("status"),
            "Error": span.get("error") or "",
        })

    journey_df = pd.DataFrame(rows)

    st.dataframe(
        journey_df,
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "Stages are sorted by start timestamp. "
        "Some intervals overlap, especially "
        "final_response_wait and individual Kafka stages; "
        "do not sum overlapping durations."
    )

    st.subheader("Agent and queue latency")

    timing_rows = []

    for span in journey:
        if span.get("stage") in {
            "planner",
            "writer",
            "reviewer",
            "evaluation",
            "queue_wait",
        }:
            timing_rows.append({
                "Stage": span["stage"],
                "Consumer": span.get("consumer_stage", ""),
                "Duration (ms)": span.get("duration_ms", 0),
            })

    if timing_rows:
        timing_df = pd.DataFrame(timing_rows)
        st.dataframe(
            timing_df,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption(
            "No downstream processing stages were recorded."
        )

    st.subheader("Evaluator scores and explanations")

    result_path = (
        reports_dir / "live_evaluations"
        / f"{selected_id}.json"
    )

    if result_path.exists():
        evaluation = json.loads(
            result_path.read_text(encoding="utf-8")
        )

        if evaluation.get("trace_id") == selected_id:
            score_rows = []

            for name, metric in evaluation.get(
                "metrics", {}
            ).items():
                score_rows.append({
                    "Metric": name,
                    "Score (1–5)": metric.get(
                        "score_1_to_5"
                    ),
                    "Score difference": metric.get(
                        "score_difference"
                    ),
                    "Reason": metric.get(
                        "reason",
                        metric.get(
                            "interpretation",
                            metric.get("error", ""),
                        ),
                    ),
                })

            st.dataframe(
                pd.DataFrame(score_rows),
                hide_index=True,
                use_container_width=True,
            )

            with st.expander(
                "Original Planner, Writer and Reviewer content"
            ):
                st.json({
                    "question": evaluation.get("question"),
                    "plan": evaluation.get("plan"),
                    "draft": evaluation.get("draft"),
                    "final_answer": evaluation.get(
                        "final_answer"
                    ),
                    "reviewer_status": evaluation.get(
                        "reviewer_status"
                    ),
                })
        else:
            st.error("Saved evaluation trace ID mismatch.")
    elif evaluation_spans:
        st.warning(
            "An evaluation span exists, but its "
            "corresponding results file is missing."
        )
    else:
        st.caption(
            "No GEval evaluation was recorded for this trace. "
            "Benchmark requests intentionally disable it."
        )

    with st.expander("Raw tracing records"):
        st.json(journey)

    st.divider()
    st.subheader("Part 4 — 50-request latency experiment")

    summary_path = (
        reports_dir / "hw10_benchmark_summary.json"
    )

    if summary_path.exists():
        summary = json.loads(
            summary_path.read_text(encoding="utf-8")
        )

        b1, b2, b3 = st.columns(3)
        b1.metric(
            "Confirmed cache misses",
            summary.get("confirmed_misses", 0),
        )
        b2.metric(
            "Failed attempts",
            summary.get("failed_attempts", 0),
        )
        b3.metric(
            "Queue wait / E2E",
            str(
                summary.get(
                    "queue_wait_percent_of_e2e", 0
                )
            ) + "%",
        )

        stats_rows = []

        for stage, values in summary.get(
            "statistics", {}
        ).items():
            stats_rows.append({
                "Stage": stage,
                "Mean (ms)": values.get("mean_ms"),
                "p50 (ms)": values.get("p50_ms"),
                "p95 (ms)": values.get("p95_ms"),
            })

        st.dataframe(
            pd.DataFrame(stats_rows),
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "50 verified cold-cache requests, with a unique "
            "data version per request. GEval was disabled "
            "for this Kafka latency experiment."
        )
    else:
        st.info("No 50-request benchmark summary available.")
'''

source += trace_page

path.write_text(source, encoding="utf-8")

print("PASS: Trace Lookup page added")
print("PASS: Summary and Evaluation pages preserved")
