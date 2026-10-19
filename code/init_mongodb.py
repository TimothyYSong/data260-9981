import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/")
DB_NAME = "s9981_doc"
COLLECTION_NAME = "inspections"

VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "restaurant_name",
            "status",
            "inspection_type",
            "inspection_date",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "restaurant_name": {
                "bsonType": "string",
                "minLength": 1,
                "maxLength": 100,
            },
            "description": {
                "bsonType": "string",
            },
            "status": {
                "bsonType": "string",
                "enum": ["pending", "passed", "failed"],
            },
            "inspection_type": {
                "bsonType": "string",
                "enum": ["routine", "follow_up", "complaint"],
            },
            "inspection_date": {"bsonType": "date"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}


def initialize_mongodb():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    try:
        client.admin.command("ping")
        db = client[DB_NAME]

        options = {
            "validator": VALIDATOR,
            "validationLevel": "strict",
            "validationAction": "error",
        }

        if COLLECTION_NAME not in db.list_collection_names():
            db.create_collection(COLLECTION_NAME, **options)
            print("Created inspections collection.")
        else:
            db.command({"collMod": COLLECTION_NAME, **options})
            print("Updated existing inspections schema.")

        print(f"Database: {DB_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print("PASS: MongoDB schema initialized.")

    finally:
        client.close()


if __name__ == "__main__":
    initialize_mongodb()