import json
import time
from pathlib import Path

from kafka import KafkaConsumer, TopicPartition

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/hw10"
RAW = OUT / "raw"

source = RAW / "collection_run.json"
run = json.loads(source.read_text())

requests = {
    item["correlation_id"]: item
    for item in run["requests"]
}

topics = {
    "s9981_tasks": "planner",
    "s9981_drafts": "writer",
    "s9981_final": "reviewer",
}

consumer = KafkaConsumer(
    bootstrap_servers="127.0.0.1:9092",
    group_id=None,
    enable_auto_commit=False,
    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
)

partitions = [
    TopicPartition(topic, 0)
    for topic in topics
]

consumer.assign(partitions)
consumer.seek_to_beginning(*partitions)

end_offsets = consumer.end_offsets(partitions)

print("Reading existing Kafka topic history...")
for partition in partitions:
    print(
        partition.topic,
        "end offset:",
        end_offsets[partition],
    )

deadline = time.monotonic() + 60
matched = 0

while time.monotonic() < deadline:
    batches = consumer.poll(
        timeout_ms=1000,
        max_records=500,
    )

    for partition, messages in batches.items():
        stage = topics[partition.topic]

        for message in messages:
            data = message.value
            correlation_id = data.get("correlation_id")

            if correlation_id in requests:
                requests[correlation_id]["messages"][stage] = data
                matched += 1

    if all(
        consumer.position(p) >= end_offsets[p]
        for p in partitions
    ):
        break

consumer.close()

cases = []
missing = []

for item in sorted(
    requests.values(),
    key=lambda x: int(x["case_id"].split("_")[1]),
):
    messages = item["messages"]

    absent = [
        stage
        for stage in topics.values()
        if stage not in messages
    ]

    if absent:
        missing.append({
            "case_id": item["case_id"],
            "missing_stages": absent,
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

# Preserve original collection evidence.
recovered_run = {
    **run,
    "requests": list(requests.values()),
    "missing": missing,
    "recovered_from_kafka_history": True,
}

(RAW / "collection_run_recovered.json").write_text(
    json.dumps(recovered_run, indent=2)
)

print("Matched Kafka records:", matched)
print("Complete cases:", len(cases), "/20")
print("Missing cases:", len(missing))

if missing:
    print(json.dumps(missing, indent=2))
    print("Original eval_cases.json left unchanged.")
else:
    assert len(cases) == 20
    assert len({
        c["correlation_id"] for c in cases
    }) == 20
    assert all(
        isinstance(c["draft"], str)
        for c in cases
    )

    (OUT / "eval_cases.json").write_text(
        json.dumps(cases, indent=2, ensure_ascii=False)
    )

    print("PASS: All 20 genuine Writer drafts recovered.")
    print("Saved:", OUT / "eval_cases.json")
