# db.py
import os
from pymongo import MongoClient

# Read MongoDB URI from Render environment variable
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["smart_cottage"]
users_col = db["users"]


def get_user(uid):
    return users_col.find_one({"uid": uid})


def register_user(uid, name, email):
    users_col.insert_one({
        "uid": uid,
        "name": name,
        "email": email
    })
