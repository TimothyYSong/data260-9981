import json
import math
import os
from urllib.request import Request, urlopen

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

EMBED_MODEL = "nomic-embed-text:latest"


def embed_text(text: str) -> list[float]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text cannot be empty")

    payload = json.dumps({
        "model": EMBED_MODEL,
        "input": text,
    }).encode("utf-8")

    request = Request(
        f"{OLLAMA_BASE_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        result = json.load(response)

    embeddings = result.get("embeddings")

    if not isinstance(embeddings, list) or not embeddings:
        raise ValueError("Ollama returned no embeddings")

    vector = embeddings[0]

    if (
        not isinstance(vector, list)
        or not vector
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vector
        )
    ):
        raise ValueError("Ollama returned an invalid embedding")

    return [float(value) for value in vector]
