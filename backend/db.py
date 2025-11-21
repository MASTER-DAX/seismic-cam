# backend/db.py
import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set")

DB_NAME = os.getenv("DB_NAME", "smart_cottage")
# Use the existing collection named "users" by default
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_col = db[COLLECTION_NAME]

# Ensure index on uid for quick lookup and uniqueness
# If uid is already stored differently, you can adapt this field.
try:
    users_col.create_index([("uid", ASCENDING)], unique=True)
except Exception:
    # index creation can fail if existing conflicting documents exist
    pass


def find_user_by_uid(uid: str):
    """Return user document or None"""
    if not uid:
        return None
    return users_col.find_one({"uid": uid})


def register_user(user_doc: dict):
    """
    user_doc must contain 'uid' and at least 'name'.
    Returns (doc, created_flag)
    """
    uid = user_doc.get("uid")
    if not uid:
        raise ValueError("uid is required")

    doc = {
        "uid": uid,
        "name": user_doc.get("name"),
        "email": user_doc.get("email"),
        "meta": user_doc.get("meta", {}),
    }
    try:
        result = users_col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc, True
    except DuplicateKeyError:
        # If already exists, update and return updated doc
        users_col.update_one({"uid": uid}, {"$set": doc})
        updated = users_col.find_one({"uid": uid})
        return updated, False


def list_users(limit: int = 100):
    return list(users_col.find().limit(limit))


def trigger_buzzer_event(uid: str, details: dict = None):
    """
    Log buzzer events to an 'events' collection.
    """
    events_col = db.get_collection("events")
    ev = {
        "uid": uid,
        "type": "buzzer",
        "details": details or {},
    }
    events_col.insert_one(ev)
    return ev
