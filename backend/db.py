from pymongo import MongoClient
from datetime import datetime
import os

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfid_system"]

users = db["users"]
taps = db["taps"]

# ---------------- USERS ----------------
def get_users(cottage=None, search=None, skip=0, limit=10):
    q = {}
    if cottage:
        q["cottage"] = cottage
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"employee_id": {"$regex": search, "$options": "i"}},
            {"uid": {"$regex": search, "$options": "i"}}
        ]

    data = list(
        users.find(q, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    total = users.count_documents(q)
    return data, total


def register_user(doc):
    doc["created_at"] = datetime.utcnow()
    users.replace_one({"uid": doc["uid"]}, doc, upsert=True)


def update_user(uid, data):
    users.update_one({"uid": uid}, {"$set": data})


def delete_user(uid):
    users.delete_one({"uid": uid})


def find_user(uid):
    return users.find_one({"uid": uid}, {"_id": 0})

# ---------------- TAPS / AUDIT ----------------
def log_tap(uid, cottage, result, reason):
    taps.insert_one({
        "uid": uid,
        "cottage": cottage,
        "result": result,
        "reason": reason,
        "timestamp": datetime.utcnow()
    })


def get_taps(skip=0, limit=20):
    data = list(
        taps.find({}, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    total = taps.count_documents({})
    return data, total
