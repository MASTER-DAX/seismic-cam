from pymongo import MongoClient
import os
from datetime import datetime

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfid_system"]

users = db["users"]
taps = db["taps"]

# ------------------------
# USER OPERATIONS
# ------------------------

def find_user_by_name_and_employee(name, employee_id):
    return users.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}, "employee_id": employee_id},
        {"_id": 0}
    )


def register_user(doc):
    doc["created_at"] = datetime.utcnow()
    users.replace_one({"uid": doc["uid"]}, doc, upsert=True)
    return True

def find_user_by_uid(uid):
    return users.find_one({"uid": uid}, {"_id": 0})

def trigger_buzzer_event(uid):
    taps.insert_one({"uid": uid, "ts": datetime.utcnow()})

# ------------------------
# DASHBOARD STATS
# ------------------------
def count_users_by_access_level():
    pipeline = [
        {"$group": {"_id": "$access_level", "count": {"$sum": 1}}}
    ]
    result = users.aggregate(pipeline)
    counts = {"guest": 0, "basic": 0, "premium": 0, "admin": 0}
    for doc in result:
        key = doc["_id"].lower()
        if key in counts:
            counts[key] = doc["count"]
    return counts
