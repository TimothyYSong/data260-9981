"""HW10 shared structured tracing.

One correlation_id is reused as trace_id throughout the pipeline.
Writes append-only JSONL spans with cross-process file locking.
"""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]

TRACE_FILE = Path(
    os.getenv(
        "HW10_TRACE_PATH",
        str(ROOT / "reports/hw10/traces.jsonl"),
    )
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_span(
    *,
    trace_id,
    stage,
    start_time,
    end_time,
    duration_ms,
    status,
    error=None,
    **metadata,
):
    """Append a single structured span safely across processes."""

    if not isinstance(trace_id, str) or not trace_id.strip():
        raise ValueError("trace_id is required")

    if not isinstance(stage, str) or not stage.strip():
        raise ValueError("stage is required")

    if status not in ("success", "error", "skipped"):
        raise ValueError("Invalid span status")

    record = {
        "span_id": str(uuid4()),
        "trace_id": trace_id,
        "correlation_id": trace_id,
        "stage": stage,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": round(float(duration_ms), 3),
        "status": status,
        "error": str(error) if error is not None else None,
        **metadata,
    }

    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with TRACE_FILE.open("a", encoding="utf-8") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        try:
            file.write(
                json.dumps(record, ensure_ascii=False, default=str)
                + "\n"
            )
            file.flush()
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    return record


@contextmanager
def trace_stage(trace_id, stage, **metadata):
    """Record real elapsed time, including exceptions."""

    started_at = utc_now()
    started = perf_counter()
    span_metadata = dict(metadata)

    try:
        yield span_metadata
    except Exception as exc:
        write_span(
            trace_id=trace_id,
            stage=stage,
            start_time=started_at,
            end_time=utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
            **span_metadata,
        )
        raise
    else:
        write_span(
            trace_id=trace_id,
            stage=stage,
            start_time=started_at,
            end_time=utc_now(),
            duration_ms=(perf_counter() - started) * 1000,
            status="success",
            **span_metadata,
        )


def read_trace(trace_id):
    """Return all recorded spans for a single trace."""

    if not TRACE_FILE.exists():
        return []

    spans = []

    with TRACE_FILE.open(encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("trace_id") == trace_id:
                spans.append(record)

    return sorted(
        spans,
        key=lambda record: record["start_time"],
    )


def record_kafka_queue_wait(message, trace_id, consumer_stage):
    """Measure elapsed time from Kafka record timestamp to consumption."""

    if not isinstance(trace_id, str) or not trace_id.strip():
        return None

    timestamp_ms = getattr(message, "timestamp", None)
    if timestamp_ms is None or timestamp_ms < 0:
        return None

    started_at = datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    )
    received_at = datetime.now(timezone.utc)

    elapsed_ms = (
        received_at - started_at
    ).total_seconds() * 1000

    return write_span(
        trace_id=trace_id,
        stage="queue_wait",
        start_time=started_at.isoformat(),
        end_time=received_at.isoformat(),
        duration_ms=max(0, elapsed_ms),
        status="success",
        error=None,
        consumer_stage=consumer_stage,
        input_topic=message.topic,
        partition=message.partition,
        offset=message.offset,
        clock_skew_detected=elapsed_ms < 0,
        timing_method="Kafka record timestamp to consumer receive",
    )
