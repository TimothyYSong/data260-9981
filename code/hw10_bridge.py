"""HW10 cache-to-Kafka request bridge."""

import json
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic, perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from pydantic import BaseModel, Field

from hw10_tracing import trace_stage

PREFIX = "s9981"
BOOTSTRAP = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"
)

router = APIRouter()


class HW10Question(BaseModel):
    question: str = Field(min_length=1)
    threshold: float = Field(default=0.95, ge=0, le=1)
    data_version: str = "hw10_v1"
    evaluate: bool = True


def kafka_request(question, trace_id, timeout=90):
    """Publish with trace_id and wait for the matching final message."""

    partition = TopicPartition(f"{PREFIX}_final", 0)

    consumer = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        group_id=None,
        enable_auto_commit=False,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    producer = None

    try:
        consumer.assign([partition])
        consumer.seek_to_end(partition)

        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        with trace_stage(trace_id, "inbox_publish"):
            producer.send(
                f"{PREFIX}_inbox",
                value={
                    "correlation_id": trace_id,
                    "trace_id": trace_id,
                    "question": question,
                },
            ).get(timeout=15)

        deadline = monotonic() + timeout

        with trace_stage(trace_id, "final_response_wait"):
            while monotonic() < deadline:
                records = consumer.poll(timeout_ms=500)

                for messages in records.values():
                    for message in messages:
                        final = message.value

                        if final.get("correlation_id") == trace_id:
                            return final

            raise TimeoutError(
                f"No final Kafka response for trace_id={trace_id}"
            )
    finally:
        consumer.close()
        if producer is not None:
            producer.close()


def register_routes(cache):
    @router.post("/api/hw10/ask")
    def ask_hw10(request: HW10Question):
        trace_id = str(uuid4())
        started = perf_counter()

        try:
            with trace_stage(
                trace_id,
                "cache_lookup",
                threshold=request.threshold,
                data_version=request.data_version,
            ) as span:
                embedding = cache.embed(request.question)
                match = cache.search(
                    embedding,
                    request.data_version,
                    request.question,
                )

                hit = (
                    match is not None
                    and match["similarity"] >= request.threshold
                )

                span["cache_result"] = "hit" if hit else "miss"
                span["similarity"] = (
                    match["similarity"] if match else None
                )

            if hit:
                return {
                    "trace_id": trace_id,
                    "question": request.question,
                    "answer": match["answer"],
                    "is_cached": True,
                    "similarity": match["similarity"],
                    "latency_ms": round(
                        (perf_counter() - started) * 1000, 2
                    ),
                }

            try:
                with trace_stage(trace_id, "kafka_round_trip"):
                    final = kafka_request(request.question, trace_id)
            except ValueError as exc:
                raise RuntimeError(
                    f"Kafka transport failure: {exc}"
                ) from exc

            if final.get("status") != "approved":
                raise RuntimeError(
                    "Reviewer did not approve the response: "
                    + str(final.get("review_reason"))
                )

            answer = final.get("answer")

            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("Empty final Kafka answer")


            if request.evaluate:
                # Evaluate the actual correlation-linked Kafka messages.
                evaluation_case = {
                    "case_id": trace_id,
                    "correlation_id": trace_id,
                    "question": request.question,
                    "plan": final.get("plan", []),
                    "draft": final.get("draft", ""),
                    "final_answer": answer,
                    "reviewer_status": final["status"],
                }

                with trace_stage(trace_id, "evaluation"):
                    evaluation_run = subprocess.run(
                        [
                            sys.executable,
                            str(
                                Path(__file__).resolve().parent
                                / "hw10_trace_evaluator.py"
                            ),
                        ],
                        input=json.dumps(evaluation_case),
                        text=True,
                        capture_output=True,
                        timeout=120,
                    )

                    if evaluation_run.returncode != 0:
                        raise RuntimeError(
                            "Evaluator failed: "
                            + evaluation_run.stderr[-1500:]
                        )

                    evaluation = json.loads(evaluation_run.stdout)

                    if evaluation.get("trace_id") != trace_id:
                        raise RuntimeError(
                            "Evaluator returned mismatched trace_id"
                        )

                    result_dir = (
                        Path(__file__).resolve().parents[1]
                        / "reports"
                        / "hw10"
                        / "live_evaluations"
                    )
                    result_dir.mkdir(parents=True, exist_ok=True)

                    result_path = result_dir / f"{trace_id}.json"
                    result_path.write_text(
                        json.dumps(
                            evaluation,
                            indent=2,
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )

            with trace_stage(trace_id, "cache_store"):
                cache.store(
                    request.question,
                    embedding,
                    answer,
                    request.data_version,
                )

            return {
                "trace_id": trace_id,
                "question": request.question,
                "answer": answer,
                "is_cached": False,
                "similarity": (
                    match["similarity"] if match else None
                ),
                "latency_ms": round(
                    (perf_counter() - started) * 1000, 2
                ),
                "reviewer_status": final["status"],
            }

        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail={"trace_id": trace_id, "error": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"trace_id": trace_id, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "trace_id": trace_id,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            ) from exc

    return router
