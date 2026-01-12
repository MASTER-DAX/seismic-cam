import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from db import (
    find_user_by_uid,
    register_user,
    trigger_buzzer_event,
    count_users_by_access_level
)

# -------------------------------------------------
# FLASK CONFIG
# -------------------------------------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.route("/health")
def health():
    return "OK", 200

# -------------------------------------------------
# SERVE FRONTEND
# -------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# -------------------------------------------------
# ESP32 → Server: Tap Card
# -------------------------------------------------
@app.route("/api/tap", methods=["POST"])
def tap_card():
    data = request.get_json() or {}
    
    uid = data.get("uid")
    reader_cottage = data.get("reader_cottage")
    
    if not uid:
        return jsonify({"error": "missing uid"}), 400
    if not reader_cottage:
        return jsonify({"error": "missing reader_cottage"}), 400

    trigger_buzzer_event(uid)
    socketio.emit("card_tapped", {"uid": uid})
    user = find_user_by_uid(uid)

    return jsonify({
        "status": "ok",
        "registered": bool(user),
        "user": user
    })

# -------------------------------------------------
# ESP32 CHECK ACCESS
# -------------------------------------------------
@app.route("/api/check_access", methods=["POST"])
def check_access():
    data = request.get_json() or {}

    uid = data.get("uid")
    reader_cottage = data.get("reader_cottage")

    if not uid:
        return jsonify({"error": "missing uid"}), 400
    if not reader_cottage:
        return jsonify({"error": "missing reader_cottage"}), 400

    user = find_user_by_uid(uid)

    if not user:
        return jsonify({
            "access": "denied",
            "reason": "Card not registered"
        })

    if user.get("cottage") != reader_cottage:
        return jsonify({
            "access": "denied",
            "reason": "Card assigned to different cottage"
        })

    return jsonify({
        "access": "granted",
        "reason": "Valid card & correct cottage",
        "user": {
            "name": user.get("name"),
            "employee_id": user.get("employee_id"),
            "access_level": user.get("access_level")
        }
    })

# -------------------------------------------------
# Admin → Register Card
# -------------------------------------------------

@app.route("/api/login_user", methods=["POST"])
def login_user():
    data = request.get_json() or {}
    name = data.get("name")
    employee_id = data.get("employee_id")

    if not name or not employee_id:
        return jsonify({"success": False, "message": "name and employee_id required"}), 400

    # Case-insensitive search for name + exact employee_id
    user = users.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}, "employee_id": employee_id},
        {"_id": 0}
    )

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 401

    return jsonify({
        "success": True,
        "user": {
            "name": user.get("name"),
            "employee_id": user.get("employee_id"),
            "access_level": user.get("access_level"),
            "cottage": user.get("cottage")
        }
    })
@app.route("/api/register_card", methods=["POST"])
def register_card():
    data = request.get_json() or {}

    uid = data.get("uid")
    name = data.get("name")
    employee_id = data.get("employee_id")
    access_level = data.get("access_level")
    valid_until = data.get("valid_until")
    cottage = data.get("cottage")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    doc = {
        "uid": uid,
        "name": name,
        "employee_id": employee_id,
        "access_level": access_level,
        "valid_until": valid_until,
        "cottage": cottage
    }

    register_user(doc)

    return jsonify({"status": "saved"})

# -------------------------------------------------
# DASHBOARD: Get counts by access level
# -------------------------------------------------
@app.route("/api/user_counts")
def user_counts():
    counts = count_users_by_access_level()
    return jsonify(counts)

# -------------------------------------------------
# USER LOGIN (UID + NAME)
# -------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    uid = data.get("uid")
    name = data.get("name")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    user = find_user_by_uid(uid)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 401

    # Case-insensitive name check
    if user.get("name", "").lower() != name.lower():
        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401

    return jsonify({
        "success": True,
        "user": {
            "uid": user.get("uid"),
            "name": user.get("name"),
            "access_level": user.get("access_level"),
            "cottage": user.get("cottage")
        }
    })

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)





db.py
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
