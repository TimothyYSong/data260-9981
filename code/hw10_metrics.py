"""Lightweight JSONL request telemetry for HW10 Part 1.1.

Runs in the host FastAPI process; use a centralized store for multiple
processes/hosts. No fabricated data is generated.
"""
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading

LOGGER = logging.getLogger(__name__)
_LOCK = threading.Lock()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_FILE = Path(os.getenv('HW10_METRICS_PATH', str(PROJECT_ROOT / 'reports' / 'hw10' / 'request_metrics.jsonl')))


def log_request(*, trace_id: str, status_code: int, latency_ms: float, is_cached: bool | None, error: str | None = None) -> None:
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'trace_id': trace_id,
        'endpoint': '/api/hw09/ask',
        'status_code': int(status_code),
        'status': 'error' if status_code >= 400 else 'success',
        'is_cached': is_cached,
        'latency_ms': round(float(latency_ms), 3),
        'error': error,
    }
    try:
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with METRICS_FILE.open('a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        LOGGER.exception('HW10 request metrics write failed')
