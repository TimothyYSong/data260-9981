from uuid import uuid4
from time import perf_counter
from memory_metrics import log_chat_usage
from file_memory_commands import handle_memory_command

import os

from fastapi import APIRouter

from memory_schemas import ChatRequest
from memory_store import (
    save_message,
    load_short_term_window,
    load_latest_summaries,
)
from chat_prompt import compose_chat_prompt
from chat_model import generate_chat_reply
from memory_summaries import (
    maybe_update_session_summary,
    maybe_update_lifetime_summary,
)
from memory_store import (
    save_message,
    load_short_term_window,
    load_latest_summaries,
    load_top_episodes,
)
from memory_store import (
    messages_collection,
    summaries_collection,
    episodes_collection,
)
from memory_embeddings import embed_text
from memory_episodes import extract_and_store_episodes

router = APIRouter(prefix="/api", tags=["Memory Chat"])


@router.post("/chat")
def chat(request: ChatRequest):
    start_time = perf_counter()
    # Generate a session ID when omitted.
    session_id = request.session_id or str(uuid4())


    # Part 4.3: Handle file-memory commands directly.
    # Commands do not require Ollama inference.
    command_reply = handle_memory_command(
        request.message,
        request.user_id,
    )

    if command_reply is not None:
        return {
            "user_id": request.user_id,
            "session_id": session_id,
            "reply": command_reply,
            "memory_used": {
                "short_term": {
                    "count": 0,
                    "messages": [],
                },
                "long_term": {
                    "session_summary": None,
                    "lifetime_summary": None,
                },
                "episodic_facts": [],
                "file_memory_command": request.message.strip(),
            },
        }


    # 1. Save the incoming user message.
    save_message(
        request.user_id,
        session_id,
        "user",
        request.message,
    )

    # 2. Retrieve short-term conversation memory.
    window = load_short_term_window(
        request.user_id,
        session_id,
    )


    # Part 3.4: Optional assistant-message eviction policy.
    # Retain user messages and discard historical assistant
    # replies from the short-term prompt context.
    if os.getenv("HW6_MEMORY_POLICY") == "evict_assistant":
        window = [
            message
            for message in window
            if message.get("role") != "assistant"
        ]

 
    # 3. Retrieve long-term summaries.
    summaries = load_latest_summaries(
        request.user_id,
        session_id,
    )

    
    # 4. Retrieve relevant episodic facts from prior messages.
    query_embedding = embed_text(request.message)

    retrieved_episodes = load_top_episodes(
        user_id=request.user_id,
        query_embedding=query_embedding,
        k=3,
    )

    episodic_facts = [
        {
            "fact": episode["fact"],
            "importance": episode["importance"],
            "similarity": episode["similarity"],
            "session_id": episode["session_id"],
        }
        for episode in retrieved_episodes
    ]


    # 5. Compose the model prompt.
    prompt = compose_chat_prompt(
        lifetime_summary=summaries["lifetime_summary"],
        session_summary=summaries["session_summary"],
        short_term_messages=window,
        current_message=request.message,
        episodic_facts=episodic_facts,
    )

    # 6. Call Ollama and capture actual token usage.
    model_result = generate_chat_reply(
        prompt,
        return_usage=True,
    )

    reply = model_result["reply"]

    # 7. Save the assistant response.
    save_message(
        request.user_id,
        session_id,
        "assistant",
        reply,
    )


    # Extract and store new episodic facts for future turns.
    extract_and_store_episodes(
        user_id=request.user_id,
        session_id=session_id,
        message=request.message,
    )


    # 8. Update summaries at configured thresholds.
    updated_summary = maybe_update_session_summary(
        request.user_id,
        session_id,
    )

    if updated_summary is not None:
        maybe_update_lifetime_summary(request.user_id)

    # Exclude the current message from the history
    # list because it appears separately in the prompt.
    history = list(window)

    if (
        history
        and history[-1]["role"] == "user"
        and history[-1]["content"] == request.message
    ):
        history.pop()

    # Part 3: log token usage and total request latency.
    latency_ms = (perf_counter() - start_time) * 1000

    log_chat_usage(
        user_id=request.user_id,
        session_id=session_id,
        prompt=prompt,
        prompt_tokens=model_result["prompt_tokens"],
        completion_tokens=model_result["completion_tokens"],
        latency_ms=latency_ms,
    )

    return {
        "user_id": request.user_id,
        "session_id": session_id,
        "reply": reply,
        "memory_used": {
            "short_term": {
                "count": len(history),
                "messages": [
                    {
                        "role": m["role"],
                        "content": m["content"],
                    }
                    for m in history
                ],
            },
            "long_term": {
                "session_summary": (
                    summaries["session_summary"]["text"]
                    if summaries["session_summary"]
                    else None
                ),
                "lifetime_summary": (
                    summaries["lifetime_summary"]["text"]
                    if summaries["lifetime_summary"]
                    else None
                ),
            },
            "episodic_facts": episodic_facts,
        },
    }


@router.get("/memory/{user_id}")
def get_user_memory(user_id: str):

    # 1. Retrieve the latest 16 messages.
    messages = list(
        messages_collection.find(
            {"user_id": user_id},
            {"_id": 0},
        )
        .sort([("created_at", -1), ("_id", -1)])
        .limit(16)
    )

    # Return messages in chronological order.
    messages.reverse()

    # 2. Retrieve the latest session summary.
    session_summary = summaries_collection.find_one(
        {
            "user_id": user_id,
            "scope": "session",
        },
        {"_id": 0},
        sort=[("created_at", -1), ("_id", -1)],
    )

    # 3. Retrieve the latest lifetime summary.
    lifetime_summary = summaries_collection.find_one(
        {
            "user_id": user_id,
            "scope": "user",
            "session_id": None,
        },
        {"_id": 0},
        sort=[("created_at", -1), ("_id", -1)],
    )

    # 4. Retrieve the latest 20 episodic facts.
    episodes = list(
        episodes_collection.find(
            {"user_id": user_id},
            {"_id": 0, "embedding": 0},
        )
        .sort([("created_at", -1), ("_id", -1)])
        .limit(20)
    )

    # 5. Return the user's stored memory.
    return {
        "user_id": user_id,
        "messages": messages,
        "session_summary": session_summary,
        "lifetime_summary": lifetime_summary,
        "episodes": episodes,
    }


@router.get("/aggregate/{user_id}")
def get_user_aggregate(user_id: str):

    # 1. Count messages grouped by UTC date.
    pipeline = [
        {
            "$match": {
                "user_id": user_id
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                        "timezone": "UTC"
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "date": "$_id",
                "count": 1
            }
        },
        {
            "$sort": {"date": 1}
        }
    ]

    daily_counts = list(
        messages_collection.aggregate(pipeline)
    )

    # 2. Retrieve the five most recent summaries.
    recent_summaries = list(
        summaries_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        )
        .sort([("created_at", -1), ("_id", -1)])
        .limit(5)
    )

    # 3. Return the aggregation results.
    return {
        "user_id": user_id,
        "daily_message_counts": daily_counts,
        "recent_summaries": recent_summaries,
    }
