# backend/db.py
import os
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URI = os.getenv("MONGO_URI")  # set this in Render / environment
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI)
db = client["smart_cottage"]
users_col = db["users"]

def get_user(uid):
    """Return user document or None"""
    if uid is None:
        return None
    return users_col.find_one({"uid": uid})

def register_user(uid, name, email):
    """Insert new user. No uniqueness enforcement here – adjust if needed."""
    doc = {"uid": uid, "name": name, "email": email}
    users_col.insert_one(doc)
    return doc

def list_users(limit=100):
    return list(users_col.find().limit(limit))
