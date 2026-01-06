from pymongo import MongoClient
import os
from datetime import datetime

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfid_system"]

users = db["users"]
taps = db["taps"]

def register_user(doc):
    doc["created_at"] = datetime.utcnow()
    users.replace_one({"uid": doc["uid"]}, doc, upsert=True)
    return True

def find_user_by_uid(uid):
    return users.find_one({"uid": uid}, {"_id": 0})

def trigger_buzzer_event(uid):
    taps.insert_one({"uid": uid, "ts": datetime.utcnow()})

def get_user_counts():
    pipeline = [
        {"$group": {"_id": "$access_level", "count": {"$sum": 1}}}
    ]
    result = users.aggregate(pipeline)
    counts = {"guest":0, "basic":0, "premium":0, "admin":0}
    for r in result:
        key = r["_id"].lower()
        counts[key] = r["count"]
    return counts
