import os

from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://127.0.0.1:27017/"
)

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

mongo_db = mongo_client["s9981_doc"]

inspections_collection = mongo_db["inspections"]