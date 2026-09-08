"""MongoDB persistence helpers for the complaint classifier application."""

import json
import os
from datetime import datetime

import pandas as pd
from pymongo import ASCENDING, MongoClient, UpdateOne


COMPLAINTS_COLLECTION = "complaints"
ADMINS_COLLECTION = "admins"
ACTIVITIES_COLLECTION = "activities"
METADATA_COLLECTION = "metadata"
_client = None
_database = None


def _reset_connection():
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database():
    """Return MongoDB, reconnecting after transient outages."""
    global _client, _database
    uri = os.getenv("MONGODB_URI", "").strip()
    database_name = os.getenv("MONGODB_DATABASE", "complaint_classifier").strip()
    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not configured. Set MONGODB_URI and MONGODB_DATABASE "
            "before using MongoDB persistence."
        )

    try:
        if _client is None or _database is None:
            _client = MongoClient(
                uri,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500,
                socketTimeoutMS=3000,
                retryWrites=True,
            )
            _client.admin.command("ping")
            _database = _client[database_name]
            _database[COMPLAINTS_COLLECTION].create_index([("Reference No", ASCENDING)], unique=True)
            _database[ADMINS_COLLECTION].create_index([("admin_id", ASCENDING)], unique=True)
            _database[ACTIVITIES_COLLECTION].create_index([("ref_no", ASCENDING), ("at", ASCENDING)])
        else:
            _client.admin.command("ping")
        return _database
    except Exception as error:
        _reset_connection()
        raise RuntimeError(f"MongoDB is temporarily unavailable: {error}") from error


def mongo_enabled() -> bool:
    return bool(os.getenv("MONGODB_URI", "").strip())


def _clean_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return value.item() if hasattr(value, "item") else value


def dataframe_to_documents(dataframe: pd.DataFrame) -> list[dict]:
    return [
        {str(key): _clean_value(value) for key, value in row.items()}
        for row in dataframe.to_dict(orient="records")
    ]


def documents_to_dataframe(documents: list[dict], columns: list[str]) -> pd.DataFrame:
    rows = []
    for document in documents:
        rows.append({column: document.get(column, "") for column in columns})
    return pd.DataFrame(rows, columns=columns)


def replace_complaints(dataframe: pd.DataFrame, columns: list[str]) -> None:
    """Persist complaint changes without deleting existing records."""
    documents = dataframe_to_documents(dataframe.reindex(columns=columns))
    try:
        collection = get_database()[COMPLAINTS_COLLECTION]
        operations = []
        for document in documents:
            reference_no = str(document.get("Reference No", "")).strip()
            if not reference_no:
                continue
            operations.append(
                UpdateOne(
                    {"Reference No": reference_no},
                    {"$set": document},
                    upsert=True,
                )
            )
        if operations:
            collection.bulk_write(operations, ordered=False)
    except Exception as error:
        # Keep complaint history available during a temporary MongoDB outage.
        print(f"[WARN] MongoDB complaint write unavailable; using local fallback: {error}")
        dataframe.reindex(columns=columns).to_csv("complaints.csv", index=False, encoding="utf-8")


def load_complaints(columns: list[str], legacy_path: str = "complaints.csv") -> pd.DataFrame:
    """Load complaints from MongoDB and import the legacy CSV on first use."""
    try:
        database = get_database()
        collection = database[COMPLAINTS_COLLECTION]
        if collection.count_documents({}) == 0 and os.path.exists(legacy_path):
            legacy = pd.read_csv(legacy_path, on_bad_lines="skip")
            legacy = legacy.reindex(columns=columns, fill_value="")
            documents = dataframe_to_documents(legacy)
            operations = [
                UpdateOne(
                    {"Reference No": str(document.get("Reference No", "")).strip()},
                    {"$set": document},
                    upsert=True,
                )
                for document in documents
                if str(document.get("Reference No", "")).strip()
            ]
            if operations:
                collection.bulk_write(operations, ordered=False)

        documents = list(collection.find({}, {"_id": 0}).sort("_id", ASCENDING))
        return documents_to_dataframe(documents, columns)
    except Exception as error:
        if os.path.exists(legacy_path):
            print(f"[WARN] MongoDB complaint read unavailable; using local fallback: {error}")
            legacy = pd.read_csv(legacy_path, on_bad_lines="skip")
            return legacy.reindex(columns=columns, fill_value="")
        raise


def load_legacy_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
