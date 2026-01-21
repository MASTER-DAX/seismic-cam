# admin_app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime

from db import (
    users,
    find_user_by_name_and_employee,
    register_user,
    find_user_by_uid,
    count_users_by_access_level,
    trigger_buzzer_event
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
# ESP32 → TAP CARD
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

    socketio.emit("card_tapped", {
        "uid": uid
    })

    user = find_user_by_uid(uid)

    return jsonify({
        "status": "ok",
        "registered": bool(user),
        "user": user
    })

# -------------------------------------------------
# ESP32 → CHECK ACCESS
# -------------------------------------------------
@app.route("/api/check_access", methods=["POST"])
def check_access():
    data = request.get_json() or {}

    uid = data.get("uid")
    reader_cottage = data.get("reader_cottage")

    if not uid or not reader_cottage:
        return jsonify({"error": "missing data"}), 400

    user = find_user_by_uid(uid)

    if not user:
        socketio.emit("card_tapped", {
            "uid": uid,
            "access": "denied",
            "reason": "Card not registered"
        })
        return jsonify({"access": "denied"})

    if user.get("cottage") != reader_cottage:
        socketio.emit("card_tapped", {
            "uid": uid,
            "access": "denied",
            "reason": "Wrong cottage"
        })
        return jsonify({"access": "denied"})

    socketio.emit("card_tapped", {
        "uid": uid,
        "access": "granted",
        "reason": "Access granted"
    })

    return jsonify({"access": "granted"})

# -------------------------------------------------
# MOBILE APP → LOGIN (NAME + EMPLOYEE ID)
# -------------------------------------------------
@app.route("/api/login_user", methods=["POST"])
def login_user():
    data = request.get_json() or {}

    name = data.get("name")
    employee_id = data.get("employee_id")

    if not name or not employee_id:
        return jsonify({"success": False, "message": "name and employee_id required"}), 400

    user = find_user_by_name_and_employee(name, employee_id)

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

# -------------------------------------------------
# ADMIN → REGISTER CARD
# -------------------------------------------------
@app.route("/api/register_card", methods=["POST"])
def register_card():
    data = request.get_json() or {}

    uid = data.get("uid")
    name = data.get("name")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    doc = {
        "uid": uid,
        "name": name,
        "employee_id": data.get("employee_id"),
        "access_level": data.get("access_level", "guest").lower(),
        "valid_until": data.get("valid_until"),
        "cottage": data.get("cottage"),
        "created_at": datetime.utcnow()
    }

    register_user(doc)

    return jsonify({"status": "saved"})

# -------------------------------------------------
# DASHBOARD → GET ALL USERS (WITH COTTAGE FILTER)
# -------------------------------------------------
@app.route("/api/users", methods=["GET"])
def get_users():
    cottage = request.args.get("cottage")

    query = {}
    if cottage:
        query["cottage"] = cottage

    users_list = list(
        users.find(query, {
            "_id": 0,
            "uid": 1,
            "name": 1,
            "employee_id": 1,
            "access_level": 1,
            "valid_until": 1,
            "cottage": 1,
            "created_at": 1
        })
    )

    return jsonify(users_list)

# -------------------------------------------------
# DASHBOARD → DELETE USER
# -------------------------------------------------
@app.route("/api/users/<uid>", methods=["DELETE"])
def delete_user(uid):
    users.delete_one({"uid": uid})
    return jsonify({"status": "deleted"})

# -------------------------------------------------
# DASHBOARD → UPDATE USER (EDIT)
# -------------------------------------------------
@app.route("/api/users/<uid>", methods=["PUT"])
def update_user(uid):
    data = request.get_json() or {}

    users.update_one(
        {"uid": uid},
        {"$set": {
            "name": data.get("name"),
            "employee_id": data.get("employee_id"),
            "access_level": data.get("access_level"),
            "valid_until": data.get("valid_until"),
            "cottage": data.get("cottage")
        }}
    )

    return jsonify({"status": "updated"})

# -------------------------------------------------
# DASHBOARD → USER COUNTS (GRAPH)
# -------------------------------------------------
@app.route("/api/user_counts")
def user_counts():
    counts = count_users_by_access_level()
    return jsonify(counts)

# -------------------------------------------------
# RFID LOGIN (UID + NAME)
# -------------------------------------------------
@app.route("/api/rfid/login", methods=["POST"])
def login_rfid():
    data = request.get_json() or {}

    uid = data.get("uid")
    name = data.get("name")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    user = find_user_by_uid(uid)

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 401

    if user.get("name", "").lower() != name.lower():
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

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
