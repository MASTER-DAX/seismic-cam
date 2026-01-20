# admin_app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime
from db import (
    find_user_by_name_and_employee,
    register_user,
    find_user_by_uid,
    count_users_by_access_level,
    delete_user,
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

    if not uid or not reader_cottage:
        return jsonify({"error": "missing data"}), 400

    user = find_user_by_uid(uid)

    access_result = {"uid": uid, "access": "denied", "reason": ""}

    if not user:
        access_result["reason"] = "Card not registered"
    elif user.get("cottage") != reader_cottage:
        access_result["reason"] = "Wrong cottage"
    elif user.get("valid_until"):
        try:
            valid_date = datetime.strptime(user["valid_until"], "%Y-%m-%d").date()
            if valid_date < datetime.today().date():
                access_result["reason"] = "Card expired"
            else:
                access_result["access"] = "granted"
                access_result["reason"] = "Access granted"
        except:
            access_result["reason"] = "Invalid valid_until date"
    else:
        access_result["access"] = "granted"
        access_result["reason"] = "Access granted"

    socketio.emit("card_tapped", access_result)
    return jsonify({"access": access_result["access"]})

# -------------------------------------------------
# Admin → Register Card (NEW LOGIC)
# -------------------------------------------------
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
        return jsonify({"status": "failed", "message": "UID and Name required"}), 400

    user = find_user_by_uid(uid)

    # Prevent registration if already active
    if user:
        try:
            valid_date = datetime.strptime(user.get("valid_until",""), "%Y-%m-%d").date()
            if valid_date >= datetime.today().date():
                return jsonify({
                    "status": "failed",
                    "message": "Card already activated — cannot register"
                }), 400
        except:
            # If valid_until invalid or missing, allow overwrite
            pass

    doc = {
        "uid": uid,
        "name": name,
        "employee_id": employee_id,
        "access_level": access_level.lower() if access_level else "guest",
        "valid_until": valid_until,
        "cottage": cottage
    }

    register_user(doc)
    return jsonify({"status": "saved", "message": "Card registered successfully"})

# -------------------------------------------------
# Admin → Delete User
# -------------------------------------------------
@app.route("/api/delete_user/<uid>", methods=["DELETE"])
def delete_user_route(uid):
    delete_user(uid)
    return jsonify({"status": "deleted"})

# -------------------------------------------------
# Dashboard: Users by Cottage
# -------------------------------------------------
@app.route("/api/users_by_cottage/<cottage>")
def users_by_cottage_route(cottage):
    # Assuming you have a find_users_by_cottage function
    from db import find_users_by_cottage
    return jsonify(find_users_by_cottage(cottage))

# -------------------------------------------------
# Dashboard: User Counts by Access Level
# -------------------------------------------------
@app.route("/api/user_counts")
def user_counts():
    counts = count_users_by_access_level()
    return jsonify(counts)

# -------------------------------------------------
# Admin → Login User (for Mobile App)
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
# RFID Login (UID + Name)
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
