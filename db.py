# db.py
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# ==========================
# MONGODB CONNECTION STRING
# ==========================
MONGO_URI = "mongodb+srv://daxdeniega16:13541ASAka@cluster0.u2nctpk.mongodb.net/?appName=Cluster0"

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
users_col = db["users"]        # store users
logs_col = db["sensors"]          # store scan logs
