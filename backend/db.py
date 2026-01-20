from pymongo import MongoClient
import os
from datetime import datetime

# -------------------------------------------------
# MONGO CONNECTION
# -------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

try:
    client.admin.command("ping")
    print("✅ MongoDB connected")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    raise

db = client["rfid_system"]

users = db["users"]
taps = db["taps"]

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def find_user_by_uid(uid):
    return users.find_one({"uid": uid}, {"_id": 0})


def find_user_by_name_and_employee(name, employee_id):
    return users.find_one(
        {
            "name": {"$regex": f"^{name}$", "$options": "i"},
            "employee_id": employee_id
        },
        {"_id": 0}
    )


def is_card_expired(user):
    """
    Returns True if expired
    """
    valid_until = user.get("valid_until")
    if not valid_until:
        return False  # permanent card

    try:
        expiry = datetime.fromisoformat(valid_until)
        return expiry < datetime.utcnow()
    except:
        return False


def can_register_uid(uid):
    user = users.find_one({"uid": uid})
    if not user:
        return True

    return is_card_expired(user)


def register_user(doc):
    doc["created_at"] = datetime.utcnow()
    users.replace_one({"uid": doc["uid"]}, doc, upsert=True)
    return True


def delete_user(uid):
    users.delete_one({"uid": uid})


def update_user(uid, data):
    users.update_one({"uid": uid}, {"$set": data})


def trigger_buzzer_event(uid):
    taps.insert_one({
        "uid": uid,
        "timestamp": datetime.utcnow()
    })


def get_users_by_cottage(cottage):
    result = []
    for u in users.find({"cottage": cottage}, {"_id": 0}):
        result.append(u)
    return result


def count_users_by_access_level():
    counts = {"guest": 0, "basic": 0, "premium": 0, "admin": 0}
    for user in users.find({}, {"access_level": 1}):
        level = user.get("access_level", "").lower()
        if level in counts:
            counts[level] += 1
    return counts
