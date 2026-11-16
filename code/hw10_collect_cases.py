import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer, TopicPartition

PREFIX = "s9981"
BOOTSTRAP = "127.0.0.1:9092"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "hw10"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    *[
        f"Retrieve inspection details for inspection {i}."
        for i in range(10016, 10026)
    ],
    "Retrieve inspection details for inspection 99991.",
    "Retrieve inspection details for inspection 99992.",
    "Provide a restaurant food safety inspection checklist.",
    "What should a restaurant sanitation checklist include?",
    "Give a checklist for checking restaurant food storage.",
    "What belongs on a basic restaurant hygiene checklist?",
    "Find inspections for Restaurant 14.",
    "Search restaurant inspection records for Restaurant 15.",
    "Summarize inspections for restaurant ID 14.",
    "Compare inspection outcomes for Restaurants 14 and 15.",
]

TOPICS = {
    f"{PREFIX}_tasks": "planner",
    f"{PREFIX}_drafts": "writer",
    f"{PREFIX}_final": "reviewer",
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def main():
    assert len(QUESTIONS) == 20

    consumer = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        group_id=None,
        enable_auto_commit=False,
        auto_offset_reset="latest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    partitions = [TopicPartition(topic, 0) for topic in TOPICS]
    consumer.assign(partitions)
    consumer.seek_to_end(*partitions)

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda obj: json.dumps(obj).encode("utf-8"),
    )

    requests = {}
    for index, question in enumerate(QUESTIONS, 1):
        correlation_id = str(uuid4())
        requests[correlation_id] = {
            "case_id": f"case_{index:02d}",
            "correlation_id": correlation_id,
            "question": question,
            "submitted_at": utc_now(),
            "messages": {},
        }

    print("Submitting 20 genuine Kafka requests...", flush=True)

    for correlation_id, item in requests.items():
        producer.send(
            f"{PREFIX}_inbox",
            value={
                "correlation_id": correlation_id,
                "question": item["question"],
            },
        ).get(timeout=15)

    producer.flush()

    deadline = time.monotonic() + 180

    while time.monotonic() < deadline:
        batches = consumer.poll(timeout_ms=1000, max_records=100)

        for partition, messages in batches.items():
            stage = TOPICS[partition.topic]

            for message in messages:
                data = message.value
                correlation_id = data.get("correlation_id")

                if correlation_id in requests:
                    requests[correlation_id]["messages"][stage] = data

        completed = sum(
            all(stage in item["messages"] for stage in TOPICS.values())
            for item in requests.values()
        )

        print(f"\rComplete pipeline records: {completed}/20",
              end="", flush=True)

        if completed == 20:
            break

    print()

    producer.close()
    consumer.close()

    cases = []
    missing = []

    for item in requests.values():
        messages = item["messages"]

        if not all(stage in messages for stage in TOPICS.values()):
            missing.append({
                "case_id": item["case_id"],
                "missing_stages": [
                    stage for stage in TOPICS.values()
                    if stage not in messages
                ],
            })
            continue

        planner = messages["planner"]
        writer = messages["writer"]
        reviewer = messages["reviewer"]

        cases.append({
            "case_id": item["case_id"],
            "correlation_id": item["correlation_id"],
            "question": item["question"],
            "plan": planner.get("steps"),
            "draft": writer.get("draft"),
            "final_answer": reviewer.get("answer"),
            "reviewer_status": reviewer.get("status"),
            "review_reason": reviewer.get("review_reason"),
            "source": "actual Kafka Planner/Writer/Reviewer messages",
        })

    with (RAW / "collection_run.json").open("w") as file:
        json.dump({
            "collected_at": utc_now(),
            "requests": list(requests.values()),
            "missing": missing,
        }, file, indent=2)

    with (OUT / "eval_cases.json").open("w") as file:
        json.dump(cases, file, indent=2, ensure_ascii=False)

    print(f"Cases saved: {len(cases)}/20")
    print(f"Missing: {len(missing)}")
    print(f"Dataset: {OUT / 'eval_cases.json'}")

    if missing:
        print("Missing stages:", json.dumps(missing, indent=2))
        raise SystemExit(1)

    assert len(cases) == 20
    assert len(set(c["correlation_id"] for c in cases)) == 20
    assert all(isinstance(c["draft"], str) for c in cases)
    print("PASS: 20 distinct genuine Writer drafts collected.")

if __name__ == "__main__":
    main()
