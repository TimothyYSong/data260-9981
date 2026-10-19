from mongo_database import mongo_client, mongo_db

COLLECTIONS = [
    "messages",
    "summaries",
    "episodes",
]


def initialize_memory_collections():
    mongo_client.admin.command("ping")

    existing = set(mongo_db.list_collection_names())

    for name in COLLECTIONS:
        if name not in existing:
            mongo_db.create_collection(name)
            print(f"CREATED: {name}")
        else:
            print(f"EXISTS: {name}")

    current = set(mongo_db.list_collection_names())

    required = {
        "inspections",
        "messages",
        "summaries",
        "episodes",
    }

    assert required.issubset(current)

    print(f"Database: {mongo_db.name}")
    print("PASS: All memory collections initialized.")
    print("PASS: Part 1 inspections collection preserved.")


if __name__ == "__main__":
    try:
        initialize_memory_collections()
    finally:
        mongo_client.close()
