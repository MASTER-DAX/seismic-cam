# db.py
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# ==========================
# MONGODB CONNECTION STRING
# ==========================
# Read from Render's environment variable
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI environment variable is not set!")

# ==========================
# CONNECT TO MONGO ATLAS
# ==========================
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas!")
except Exception as e:
    print("❌ MongoDB Connection Error:", e)

# ==========================
# DATABASE + COLLECTIONS
# ==========================
db = client["smart_cottage"]     # database name
users_col = db["users"]          # store users
logs_col = db["sensors"]         # store scan logs
