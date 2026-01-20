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
    find_users_by_cottage,
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

    if not uid or not reader_cottage:
        return jsonify({"error": "missing data"}), 400

    # Trigger buzzer
    trigger_buzzer_event(uid)

    # Find user in DB
    user = find_user_by_uid(uid)

    # Prepare default response
    access_result = {"uid": uid, "access": "denied", "reason": "", "user": None}

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
                access_result["user"] = user
        except:
            access_result["reason"] = "Invalid valid_until date"
    else:
        access_result["access"] = "granted"
        access_result["reason"] = "Access granted"
        access_result["user"] = user

    # Emit to dashboard via Socket.IO
    socketio.emit("card_tapped", access_result)

    return jsonify(access_result)

# -------------------------------------------------
# ESP32 → Check Access (Optional, keeps old functionality)
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
        socketio.emit("card_tapped", {"uid": uid, "access": "denied", "reason": "Card not registered"})
        return jsonify({"access": "denied"})

    if user.get("cottage") != reader_cottage:
        socketio.emit("card_tapped", {"uid": uid, "access": "denied", "reason": "Wrong cottage"})
        return jsonify({"access": "denied"})

    socketio.emit("card_tapped", {"uid": uid, "access": "granted", "reason": "Access granted"})
    return jsonify({"access": "granted"})

# -------------------------------------------------
# Admin → Register Card
# -------------------------------------------------
@app.route("/api/register_card", methods=["POST"])
def register_card_route():
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
        "access_level": access_level.lower() if access_level else "guest",
        "valid_until": valid_until,
        "cottage": cottage
    }
    register_user(doc)
    return jsonify({"status": "saved"})

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
    return jsonify(find_users_by_cottage(cottage))

# -------------------------------------------------
# Dashboard: User Counts by Access Level
# -------------------------------------------------
@app.route("/api/user_counts")
def user_counts():
    return jsonify(count_users_by_access_level())

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
