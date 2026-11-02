
import argparse
import csv
import json
import random
from pathlib import Path

from kafka import KafkaProducer

PREFIX = "s9981"
TOPIC = f"{PREFIX}_tasks"
BOOTSTRAP_SERVERS = "kafka:19092"

VERIFY_SEED = 269981
ENTITY_ID = "restaurant-9981"
OUTPUT_DIR = Path("/results")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["before", "after"],
        required=True,
    )
    args = parser.parse_args()

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        key_serializer=lambda key: key.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )

    # Before: distribute related messages across two partitions.
    partitions = [0, 1] * 10
    random.Random(VERIFY_SEED).shuffle(partitions)

    rows = []

    for sequence in range(1, 21):
        task = {
            "correlation_id": (
                f"ordering-{args.mode}-{VERIFY_SEED}-{sequence:02d}"
            ),
            "entity_id": ENTITY_ID,
            "sequence": sequence,
            "question": f"Restaurant inspection task {sequence}",
            "steps": [
                "Inspect food storage.",
                "Check employee hygiene.",
                "Record inspection findings.",
            ],
        }

        if args.mode == "before":
            # Explicitly split messages across two partitions.
            metadata = producer.send(
                TOPIC,
                partition=partitions[sequence - 1],
                value=task,
            ).get(timeout=15)
        else:
            # After: same restaurant ID becomes the partition key.
            metadata = producer.send(
                TOPIC,
                key=ENTITY_ID,
                value=task,
            ).get(timeout=15)

        rows.append({
            "sequence": sequence,
            "entity_id": ENTITY_ID,
            "partition": metadata.partition,
            "offset": metadata.offset,
        })

        print(
            f"{args.mode.upper()} sequence={sequence:02d} "
            f"partition={metadata.partition} "
            f"offset={metadata.offset}"
        )

    producer.close()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"part3_ordering_{args.mode}.csv"

    with output_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} messages sent; results saved to {output_file}")


if __name__ == "__main__":
    main()
