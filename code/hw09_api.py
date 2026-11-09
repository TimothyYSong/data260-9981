import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from semantic_cache import SemanticCache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI(title="DATA 260 HW9 Semantic Cache")

cache = SemanticCache()


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    data_version: str = "v1"


@app.post("/api/hw09/ask")
def ask_question(request: QuestionRequest):
    try:
        return cache.ask(
            question=request.question,
            threshold=request.threshold,
            data_version=request.data_version,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc