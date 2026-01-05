import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from db import (
    find_user_by_uid,
    register_user,
    trigger_buzzer_event
)

# -------------------------------------------------
# FLASK CONFIG
# -------------------------------------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -------------------------------------------------
# HEALTH CHECK (for uptime pings)
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
# Sends UID + reader's cottage ID
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

    # notify frontend
    socketio.emit("card_tapped", {"uid": uid})

    # lookup user
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
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # stable port for Render
    socketio.run(app, host="0.0.0.0", port=port)
