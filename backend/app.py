# app.py (FULL VERSION — NOTHING REMOVED)

import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

from db import (
    find_user_by_uid,
    find_user_by_name_and_employee,
    can_register_uid,
    register_user,
    delete_user,
    update_user,
    trigger_buzzer_event,
    get_users_by_cottage,
    count_users_by_access_level
)

# -------------------------------------------------
# FLASK CONFIG
# -------------------------------------------------
app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path=""
)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.route("/health")
def health():
    return "OK", 200

# -------------------------------------------------
# SERVE FRONTEND FILES
# -------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/accounts.html")
def accounts():
    return send_from_directory(app.static_folder, "accounts.html")

# -------------------------------------------------
# ESP32 → TAP CARD (LOG + REALTIME)
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

    # 🔔 log tap
    trigger_buzzer_event(uid)

    user = find_user_by_uid(uid)

    socketio.emit("card_tapped", {
        "uid": uid,
        "registered": bool(user),
        "user": user
    })

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

    # ❌ NOT REGISTERED
    if not user:
        socketio.emit("card_tapped", {
            "uid": uid,
            "access": "denied",
            "reason": "Card not registered"
        })
        return jsonify({"access": "denied"})

    # ❌ WRONG COTTAGE
    if user.get("cottage") != reader_cottage:
        socketio.emit("card_tapped", {
            "uid": uid,
            "access": "denied",
            "reason": "Wrong cottage"
        })
        return jsonify({"access": "denied"})

    # ❌ EXPIRED
    valid_until = user.get("valid_until")
    if valid_until:
        try:
            if datetime.fromisoformat(valid_until) < datetime.utcnow():
                socketio.emit("card_tapped", {
                    "uid": uid,
                    "access": "denied",
                    "reason": "Card expired"
                })
                return jsonify({"access": "denied"})
        except:
            pass

    # ✅ GRANTED
    socketio.emit("card_tapped", {
        "uid": uid,
        "access": "granted",
        "user": user
    })

    return jsonify({"access": "granted"})

# -------------------------------------------------
# ADMIN → REGISTER / UPDATE CARD
# -------------------------------------------------
@app.route("/api/register_card", methods=["POST"])
def register_card():
    data = request.get_json() or {}

    uid = data.get("uid")
    name = data.get("name")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    # 🔒 block if still valid
    if not can_register_uid(uid):
        return jsonify({
            "error": "Card already registered and still valid"
        }), 403

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
# DASHBOARD → USERS TABLE
# -------------------------------------------------
@app.route("/api/users_by_cottage/<cottage>")
def users_by_cottage(cottage):
    return jsonify(get_users_by_cottage(cottage))

# -------------------------------------------------
# DASHBOARD → DELETE USER
# -------------------------------------------------
@app.route("/api/user/<uid>", methods=["DELETE"])
def remove_user(uid):
    delete_user(uid)
    return jsonify({"status": "deleted"})

# -------------------------------------------------
# DASHBOARD → UPDATE USER
# -------------------------------------------------
@app.route("/api/user/<uid>", methods=["PUT"])
def edit_user(uid):
    data = request.get_json() or {}
    update_user(uid, data)
    return jsonify({"status": "updated"})

# -------------------------------------------------
# MOBILE APP LOGIN
# -------------------------------------------------
@app.route("/api/login_user", methods=["POST"])
def login_user():
    data = request.get_json() or {}

    name = data.get("name")
    employee_id = data.get("employee_id")

    if not name or not employee_id:
        return jsonify({"success": False}), 400

    user = find_user_by_name_and_employee(name, employee_id)

    if not user:
        return jsonify({"success": False}), 401

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
# DASHBOARD → USER COUNTS
# -------------------------------------------------
@app.route("/api/user_counts")
def user_counts():
    return jsonify(count_users_by_access_level())

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
