"""
Activity Log - Tracks the full history of actions on each complaint.
Stored in MongoDB as one activity document per complaint event.
"""

import json
import os
from datetime import datetime
from mongo_store import get_database, load_legacy_json, ACTIVITIES_COLLECTION


def _load() -> dict:
    try:
        collection = get_database()[ACTIVITIES_COLLECTION]
        if collection.count_documents({}) == 0:
            legacy = load_legacy_json("complaint_activity.json", {})
            documents = [
                {"ref_no": ref_no, **event}
                for ref_no, events in legacy.items()
                for event in events
            ]
            if documents:
                collection.insert_many(documents, ordered=False)
        result = {}
        for event in collection.find({}, {"_id": 0}).sort("at", 1):
            result.setdefault(event["ref_no"], []).append({
                key: value for key, value in event.items() if key != "ref_no"
            })
        _save_local(result)
        return result
    except Exception as error:
        print(f"[WARN] MongoDB activity read unavailable; using local fallback: {error}")
        return load_legacy_json("complaint_activity.json", {})


def _save_local(data: dict):
    temporary_path = "complaint_activity.json.tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temporary_path, "complaint_activity.json")


def append(ref_no: str, action: str, by: str, note: str = ""):
    """
    Append an activity entry for a complaint.

    action  - human-readable event label, e.g. "Submitted", "Discarded by Authority",
              "Dispute Raised & Reopened", "Marked as Solved by Authority",
              "Permanently Closed"
    by      - display name of actor (admin display name + dept, or 'Citizen', 'System')
    note    - optional reason / note attached to the action
    """
    data = _load()
    data.setdefault(ref_no, []).append({
        "action": action,
        "by": by,
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": note,
    })
    _save_local(data)
    try:
        get_database()[ACTIVITIES_COLLECTION].insert_one({"ref_no": ref_no, **data[ref_no][-1]})
    except Exception as error:
        print(f"[WARN] MongoDB activity write unavailable; using local fallback: {error}")


def get(ref_no: str) -> list:
    """Return list of activity entries for a complaint, oldest first."""
    data = _load()
    return data.get(ref_no, [])
