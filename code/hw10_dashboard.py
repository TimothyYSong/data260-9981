"""HW10 Part 1.1: real metrics for existing HW9 API requests.

Start from repository root:
  python -m streamlit run code/hw10_dashboard.py
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = Path(os.getenv('HW10_METRICS_PATH', str(PROJECT_ROOT / 'reports' / 'hw10' / 'request_metrics.jsonl')))

st.set_page_config(page_title='DATA260 HW10 Operations', page_icon='📊', layout='wide')
page = st.sidebar.radio(
    "Dashboard page",
    ["Summary", "Evaluation", "Trace Lookup"],
)
st.title(f"HW10 Operations — {page}")
st.caption('Domain: Local Restaurant Inspection | Prefix: s9981 | Existing HW9 semantic-cache API')

@st.cache_data(ttl=5)
def read_records(path: str, modified_ns: int) -> pd.DataFrame:
    """Read and validate immutable snapshot of the JSONL metrics file."""
    records = []
    invalid = 0
    p = Path(path)
    if p.exists():
        with p.open(encoding='utf-8') as fh:
            for line in fh:
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict) or not {'timestamp', 'latency_ms', 'status_code', 'is_cached'} <= item.keys():
                        raise ValueError('Missing fields')
                    records.append(item)
                except (json.JSONDecodeError, ValueError, TypeError):
                    invalid += 1
    data = pd.DataFrame(records)
    if data.empty:
        return pd.DataFrame(columns=['timestamp', 'latency_ms', 'status_code', 'is_cached'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], utc=True, errors='coerce')
    data['latency_ms'] = pd.to_numeric(data['latency_ms'], errors='coerce')
    data['status_code'] = pd.to_numeric(data['status_code'], errors='coerce')
    data = data.dropna(subset=['timestamp', 'latency_ms', 'status_code'])
    return data

if page == 'Summary':
    hours = st.selectbox('Time window', options=[1, 6, 24, 72, 168], index=2, format_func=lambda v: f'Last {v} hours')
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    mtime = METRICS_PATH.stat().st_mtime_ns if METRICS_PATH.exists() else 0
    all_data = read_records(str(METRICS_PATH), mtime)
    df = all_data[(all_data['timestamp'] >= start) & (all_data['timestamp'] <= now)].copy()

    st.caption(f'Window: {start:%Y-%m-%d %H:%M:%S} UTC to {now:%Y-%m-%d %H:%M:%S} UTC · Source: {METRICS_PATH} · Refresh/cache TTL: 5 seconds')

    if df.empty:
        st.info('No request records in the selected window. Start the API and send requests before interpreting the metrics.')
        st.stop()

    count = len(df)
    errors = int((df['status_code'] >= 400).sum())
    hits = int((df['is_cached'].eq(True)).sum())
    misses = int((df['is_cached'].eq(False)).sum())
    classified = hits + misses

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Recent requests', f'{count:,}')
    m2.metric('Semantic-cache hit rate', f'{100 * hits/classified:.1f}%' if classified else 'N/A')
    m3.metric('Error rate', f'{100 * errors/count:.1f}%')
    m4.metric('E2E p50 latency', f"{df['latency_ms'].median():,.1f} ms")

    st.subheader('Cache hit vs. cache miss')
    c1, c2, c3 = st.columns(3)
    c1.metric('Cache hits', hits)
    c2.metric('Cache misses', misses)
    c3.metric('Unclassified / failed before result', count - classified)
    st.caption('Hit rate denominator = completed cache-classified requests (hits + misses). Error rate denominator = all recorded requests. Pre-cache failures are unclassified, not counted as cache misses.')

    st.subheader('End-to-end API handler latency')
    rows = []
    for label, subset in [('All recorded requests', df), ('Cache hits', df[df['is_cached'].eq(True)]), ('Cache misses', df[df['is_cached'].eq(False)])]:
        if len(subset):
            rows.append({'Path': label, 'Requests': len(subset), 'p50 (ms)': round(subset['latency_ms'].quantile(0.50), 2), 'p95 (ms)': round(subset['latency_ms'].quantile(0.95), 2), 'Mean (ms)': round(subset['latency_ms'].mean(), 2)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption('Latency measures time inside /api/hw09/ask. It includes cache search and any agent execution in the existing HW9 path, but not client/network overhead or the later Kafka/evaluation path.')

    st.subheader('Request records (newest first)')
    visible_cols = [c for c in ['timestamp','trace_id','status_code','is_cached','latency_ms','error'] if c in df.columns]
    st.dataframe(df.sort_values('timestamp', ascending=False)[visible_cols], hide_index=True, use_container_width=True)


elif page == "Evaluation":
    st.subheader("Part 2 — Pipeline evaluation")

    reports = PROJECT_ROOT / "reports" / "hw10"
    evaluation_files = sorted(
        reports.glob("evaluation_case_*.json")
    )

    if not evaluation_files:
        st.warning("No pipeline evaluation results found.")
    else:
        selected = st.selectbox(
            "Evaluated case",
            evaluation_files,
            format_func=lambda p: p.stem,
        )

        evaluation = json.loads(
            selected.read_text(encoding="utf-8")
        )
        metrics = evaluation.get("metrics", {})

        st.caption(
            f"Source: {selected.name} | "
            f"Model: {evaluation.get('judge_model', 'Unknown')} | "
            f"Trace ID: {evaluation.get('trace_id', 'Unknown')}"
        )

        st.write("**Question:**", evaluation.get("question"))

        stage_names = {
            "plan_quality": "Planner",
            "writer_helpfulness": "Writer",
            "final_helpfulness": "Final answer",
        }

        stage_rows = []
        for key, label in stage_names.items():
            value = metrics.get(key, {})
            stage_rows.append({
                "Stage": label,
                "Score (1–5)": value.get("score_1_to_5"),
                "Raw GEval": value.get("raw_geval_score"),
                "Reason": value.get(
                    "reason", value.get("error", "Unavailable")
                ),
                "Judge latency (ms)": value.get("latency_ms"),
            })

        stage_df = pd.DataFrame(stage_rows)

        st.dataframe(
            stage_df,
            hide_index=True,
            use_container_width=True,
        )

        chart_df = stage_df.dropna(
            subset=["Score (1–5)"]
        ).set_index("Stage")[["Score (1–5)"]]

        if not chart_df.empty:
            st.bar_chart(chart_df)

        st.subheader("Reviewer impact")
        improvement = metrics.get("final_vs_draft", {})

        if "score_difference" in improvement:
            a, b, c = st.columns(3)
            a.metric(
                "Writer score",
                f"{improvement['writer_score']:.2f}/5",
            )
            b.metric(
                "Final score",
                f"{improvement['final_score']:.2f}/5",
            )
            c.metric(
                "Final − draft",
                f"{improvement['score_difference']:+.2f}",
            )
            st.write(improvement.get("interpretation", ""))
            st.caption(
                "Draft text changed: "
                + str(improvement.get("text_changed"))
            )
        else:
            st.warning(
                improvement.get(
                    "error", "Improvement data unavailable"
                )
            )

        with st.expander("Original pipeline content"):
            st.json({
                "correlation_id": evaluation.get("correlation_id"),
                "plan": evaluation.get("plan"),
                "draft": evaluation.get("draft"),
                "final_answer": evaluation.get("final_answer"),
                "reviewer_status": evaluation.get("reviewer_status"),
            })

    st.divider()
    st.subheader("Part 3 — Judge validation")

    summary_path = reports / "judge_validation_summary.json"
    cases_path = reports / "judge_validation_cases.csv"

    if not summary_path.exists() or not cases_path.exists():
        st.warning("Judge validation files are not available.")
    else:
        summary = json.loads(
            summary_path.read_text(encoding="utf-8")
        )
        validation = pd.read_csv(cases_path)

        st.caption(
            "Source: judge_validation_summary.json and "
            "judge_validation_cases.csv | "
            f"Model: {summary['model']} | "
            f"Temperature: {summary['temperature']} | "
            f"Cases: {summary['cases']} | "
            f"Judge runs: {summary['judge_runs']}"
        )

        v1, v2, v3, v4 = st.columns(4)

        v1.metric(
            "Spearman correlation",
            f"{summary['spearman_rho']:.3f}",
        )
        v2.metric(
            "Mean absolute difference",
            f"{summary['mean_absolute_difference']:.3f}",
        )
        v3.metric(
            "Cases with score changes",
            f"{summary['cases_with_score_changes']}"
            f"/{summary['cases']}",
        )
        v4.metric(
            "Maximum absolute change",
            f"{summary['max_pairwise_absolute_change']:.3f}",
        )

        st.caption(
            "Mean pairwise absolute change: "
            f"{summary['mean_pairwise_absolute_change']:.3f} | "
            "Score scale: "
            f"{summary['score_scale']}"
        )

        st.subheader("Judge results by case")
        st.dataframe(
            validation,
            hide_index=True,
            use_container_width=True,
        )

        comparison = validation.set_index("case_id")[
            ["human_score", "judge_mean"]
        ]
        st.line_chart(comparison)

        st.subheader("Interpretation")
        st.write(
            "The judge shows strong rank agreement with the "
            "frozen reference labels. Its scores were identical "
            "across three runs for all 20 cases under the tested "
            "settings. The mean absolute score difference was "
            "0.51 points on the 1–5 scale."
        )
        st.write(
            "The example pipeline evaluation shows that the Writer "
            "produced a helpful answer despite a less specific "
            "Planner plan. The Reviewer left that draft unchanged, "
            "so there was no demonstrated textual improvement."
        )
        st.warning(
            "Reference-label limitation: the frozen ratings were "
            "AI-assisted rather than independently hand-assigned. "
            "These results should not be presented as independent "
            "human-judge agreement or sufficient evidence for "
            "automated deployment gating."
        )


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
