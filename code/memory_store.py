from mongo_database import mongo_db
from memory_schemas import MessageDocument, SummaryDocument

import os
import math

SHORT_TERM_N = int(os.getenv("SHORT_TERM_N", "12"))

messages_collection = mongo_db["messages"]
summaries_collection = mongo_db["summaries"]
episodes_collection = mongo_db["episodes"]


def save_message(user_id, session_id, role, content):
    message = MessageDocument(
        user_id=user_id,
        session_id=session_id,
        role=role,
        content=content,
    )

    result = messages_collection.insert_one(
        message.model_dump()
    )

    return str(result.inserted_id)


def load_short_term_window(
    user_id: str,
    session_id: str,
    n: int | None = None
):
    limit = SHORT_TERM_N if n is None else n

    if limit < 1:
        raise ValueError("SHORT_TERM_N must be at least 1")

    documents = list(
        messages_collection.find(
            {
                "user_id": user_id,
                "session_id": session_id
            },
            {"_id": 0}
        )
        .sort([("created_at", -1), ("_id", -1)])
        .limit(limit)
    )

    documents.reverse()

    return documents


def load_latest_summaries(user_id: str, session_id: str):
    session_summary = summaries_collection.find_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "scope": "session",
        },
        {"_id": 0},
        sort=[("created_at", -1), ("_id", -1)],
    )

    lifetime_summary = summaries_collection.find_one(
        {
            "user_id": user_id,
            "session_id": None,
            "scope": "user",
        },
        {"_id": 0},
        sort=[("created_at", -1), ("_id", -1)],
    )

    return {
        "session_summary": session_summary,
        "lifetime_summary": lifetime_summary,
    }


def cosine_similarity(vector_a, vector_b):
    if not vector_a or len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def load_top_episodes(user_id, query_embedding, k=3):
    if k < 1:
        raise ValueError("k must be at least 1")

    if not query_embedding or not any(query_embedding):
        return []

    documents = episodes_collection.find(
        {"user_id": user_id},
        {"_id": 0}
    )

    scored_episodes = []

    for episode in documents:
        embedding = episode.get("embedding", [])

        if len(embedding) != len(query_embedding):
            continue

        if not any(embedding):
            continue

        similarity = cosine_similarity(
            query_embedding,
            embedding
        )

        scored_episodes.append(
            (similarity, episode)
        )

    scored_episodes.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        {
            **episode,
            "similarity": round(score, 4)
        }
        for score, episode in scored_episodes[:k]
    ]
