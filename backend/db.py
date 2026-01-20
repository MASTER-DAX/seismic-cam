from pymongo import MongoClient
import os
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
try:
    client.admin.command("ping")
    print("MongoDB connected")
except Exception as e:
    print("MongoDB connection failed:", e)
    raise

db = client["rfid_system"]
users = db["users"]
taps = db["taps"]

# ------------------------
# USER OPERATIONS
# ------------------------
def find_user_by_uid(uid):
    return users.find_one({"uid": uid}, {"_id": 0})

def find_user_by_name_and_employee(name, employee_id):
    return users.find_one({"name": {"$regex": f"^{name}$", "$options": "i"},
                           "employee_id": employee_id}, {"_id": 0})

def register_user(doc):
    users.update_one({"uid": doc["uid"]}, {"$set": doc}, upsert=True)

def delete_user(uid):
    users.delete_one({"uid": uid})

def find_users_by_cottage(cottage):
    return list(users.find({"cottage": cottage}, {"_id": 0}))

def count_users_by_access_level():
    pipeline = [
        {"$group": {"_id": "$access_level", "count": {"$sum": 1}}}
    ]
    result = list(users.aggregate(pipeline))
    counts = {r["_id"]: r["count"] for r in result}
    return counts

def trigger_buzzer_event(uid):
    # Placeholder: implement hardware buzzer trigger if needed
    print(f"Buzzer triggered for UID: {uid}")
