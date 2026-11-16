import logging
from time import perf_counter
from uuid import uuid4

from hw10_metrics import log_request

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from hw10_bridge import register_routes
from semantic_cache import SemanticCache

# STEP 1: Configure logging.
# Logs help track cache activity, errors, and performance.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# STEP 2: Create the FastAPI application.
# This exposes our semantic cache through an HTTP API.
app = FastAPI(title="DATA 260 HW9 Semantic Cache")

# Initialize the semantic cache from semantic_cache.py.
# It connects to Redis and loads the embedding model.
cache = SemanticCache()

app.include_router(register_routes(cache))


# STEP 3: Define the API request format.
# Each request contains a question, similarity threshold,
# and data-version marker.
class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)

    # Minimum cosine similarity required for a cache hit.
    # Default 0.95, selected through Part 3 testing.
    threshold: float = Field(default=0.95, ge=0.0, le=1.0)

    # Identifies the version of the underlying domain data.
    data_version: str = "v1"


# STEP 4: Create the POST endpoint for incoming questions.
# Example endpoint: POST /api/hw09/ask
@app.post("/api/hw09/ask")
def ask_question(request: QuestionRequest):
    """Serve HW9 requests while recording HW10 Part 1.1 telemetry."""
    trace_id = str(uuid4())  # Reuse as correlation_id when linking Kafka in Part 4.
    started = perf_counter()
    status_code = 200
    error = None
    is_cached = None

    try:
        result = cache.ask(
            question=request.question,
            threshold=request.threshold,
            data_version=request.data_version,
            trace_id=trace_id,
        )
        is_cached = result["is_cached"]
        return {**result, "trace_id": trace_id}
    except ValueError as exc:
        status_code = 400
        error = str(exc)
        raise HTTPException(status_code=400, detail=error) from exc
    except RuntimeError as exc:
        status_code = 502
        error = str(exc)
        raise HTTPException(status_code=502, detail=error) from exc
    except Exception as exc:
        status_code = 500
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        log_request(
            trace_id=trace_id,
            status_code=status_code,
            latency_ms=(perf_counter() - started) * 1000,
            is_cached=is_cached,
            error=error,
        )
