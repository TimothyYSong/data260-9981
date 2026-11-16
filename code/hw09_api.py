import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
    try:
        # STEP 5: Forward the question to our semantic cache.
        # semantic_cache.py handles:
        # - Converting the question into an embedding
        # - Searching Redis using cosine similarity
        # - Returning a cached answer on a HIT
        # - Running the HW8 agent and storing an answer on a MISS
        # - Measuring similarity and response latency
        return cache.ask(
            question=request.question,
            threshold=request.threshold,
            data_version=request.data_version,
        )

    # STEP 6: Handle invalid input or cache validation errors.
    # Return HTTP 400 (Bad Request).
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # STEP 7: Handle agent execution failures.
    # Return HTTP 502 (Bad Gateway).
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc