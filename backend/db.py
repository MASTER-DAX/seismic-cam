from pymongo import MongoClient
import os
from datetime import datetime

client = MongoClient(os.getenv("MONGO_URI"))
db = client["rfid_system"]
users = db["users"]
taps = db["taps"]
pending_writes = db["pending_writes"]

def register_user(doc):
    doc['created_at'] = datetime.utcnow()
    users.replace_one({'uid': doc['uid']}, doc, upsert=True)
    return True

def find_user_by_uid(uid):
    return users.find_one({"uid": uid})

def list_all():
    return list(users.find({}))

def trigger_buzzer_event(uid):
    taps.insert_one({'uid': uid, 'ts': datetime.utcnow()})

def create_write_task(uid, payload):
    pending_writes.insert_one({'uid': uid, 'payload': payload, 'status': 'pending', 'created_at': datetime.utcnow()})

def get_and_mark_pending_write():
    task = pending_writes.find_one_and_update({'status': 'pending'}, {'$set': {'status': 'in_progress', 'picked_at': datetime.utcnow()}})
    return task
