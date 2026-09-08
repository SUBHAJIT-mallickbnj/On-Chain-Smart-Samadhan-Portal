# -*- coding: utf-8 -*-
"""
Admin Manager - Handles Super Admin authentication and operations.
Admins are stored in MongoDB with hashed passwords.
"""

import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from mongo_store import get_database, load_legacy_json, ADMINS_COLLECTION


def _load_db():
    try:
        collection = get_database()[ADMINS_COLLECTION]
        if collection.count_documents({}) == 0:
            legacy = load_legacy_json("admin_db.json", {"admins": []})
            for admin in legacy.get("admins", []):
                collection.update_one(
                    {"admin_id": admin.get("admin_id")},
                    {"$set": admin},
                    upsert=True,
                )
        return {"admins": list(collection.find({}, {"_id": 0}))}
    except Exception as error:
        print(f"[WARN] MongoDB admin read unavailable; using local fallback: {error}")
        return load_legacy_json("admin_db.json", {"admins": []})


def _save_db(db):
    try:
        collection = get_database()[ADMINS_COLLECTION]
        for admin in db.get("admins", []):
            collection.update_one(
                {"admin_id": admin.get("admin_id")},
                {"$set": admin},
                upsert=True,
            )
    except Exception as error:
        print(f"[WARN] MongoDB admin write unavailable; using local fallback: {error}")
        temporary_path = "admin_db.json.tmp"
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(db, file, ensure_ascii=False, indent=2)
        os.replace(temporary_path, "admin_db.json")


def init_default_admin():
    """Create default super admin if no admins exist yet."""
    db = _load_db()
    if not db["admins"]:
        db["admins"].append({
            "admin_id": "superadmin",
            "display_name": "Super Administrator",
            "password_hash": generate_password_hash("Admin@123"),
            "department": "All",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": "system"
        })
        _save_db(db)
        print("\u2705 Default super admin created: ID=superadmin, Password=Admin@123, Dept=All")
    else:
        # Migrate existing admins that lack display_name
        changed = False
        for admin in db["admins"]:
            if not admin.get("display_name"):
                admin["display_name"] = admin["admin_id"]
                changed = True
        if changed:
            _save_db(db)


def authenticate_admin(admin_id: str, password: str):
    """Return admin dict if credentials valid, else None."""
    db = _load_db()
    for admin in db["admins"]:
        if admin["admin_id"].lower() == admin_id.lower():
            if check_password_hash(admin["password_hash"], password):
                return {
                    "admin_id": admin["admin_id"],
                    "display_name": admin.get("display_name", admin["admin_id"]),
                    "department": admin["department"],
                }
    return None


def create_admin(admin_id: str, password: str, department: str, created_by: str,
                 display_name: str = ""):
    """
    Create a new admin account.
    Returns (True, message) or (False, error_message).
    """
    if not admin_id or not password or not department:
        return False, "Admin ID, password, and department are required."

    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    db = _load_db()
    existing_ids = [a["admin_id"].lower() for a in db["admins"]]
    if admin_id.lower() in existing_ids:
        return False, f"Admin ID '{admin_id}' already exists."

    db["admins"].append({
        "admin_id": admin_id,
        "display_name": display_name.strip() if display_name.strip() else admin_id,
        "password_hash": generate_password_hash(password),
        "department": department,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_by": created_by
    })
    _save_db(db)
    return True, f"Admin '{admin_id}' ({display_name or admin_id}) created for department '{department}'."


def update_display_name(admin_id: str, new_display_name: str):
    """Update display name for an admin. Returns (True, msg) or (False, err)."""
    if not new_display_name.strip():
        return False, "Display name cannot be empty."
    db = _load_db()
    for admin in db["admins"]:
        if admin["admin_id"].lower() == admin_id.lower():
            admin["display_name"] = new_display_name.strip()
            _save_db(db)
            return True, "Display name updated successfully."
    return False, "Admin not found."


def get_admin_display_name(admin_id: str) -> str:
    """Return display name for a given admin_id, falling back to admin_id."""
    db = _load_db()
    for admin in db["admins"]:
        if admin["admin_id"].lower() == admin_id.lower():
            return admin.get("display_name", admin_id)
    return admin_id


def get_all_admins():
    """Return list of admins (without password hashes)."""
    db = _load_db()
    return [
        {
            "admin_id": a["admin_id"],
            "display_name": a.get("display_name", a["admin_id"]),
            "department": a["department"],
            "created_at": a.get("created_at", ""),
            "created_by": a.get("created_by", "")
        }
        for a in db["admins"]
    ]
