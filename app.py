from flask_cors import CORS
import os
import time
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from db import users_col, logs_col

app = Flask(__name__)
CORS(app)  # allow ALL origins
socketio = SocketIO(app, cors_allowed_origins="*")

# ====================================================
# DEVICE STATE (ESP32 READS THIS)
# ====================================================
DEVICE_STATE = {
    "mode": "SCAN",      # SCAN or WRITE
    "target_user": None  # user_id during write mode
}


# ====================================================
# HOME (Optional)
# ====================================================
@app.route("/")
def home():
    return "<h2>RFID Backend Running</h2>"


# ====================================================
# CREATE PENDING USER (NO RFID YET)
# ====================================================
@app.route("/create_pending_user", methods=["POST"])
def create_pending_user():
    data = request.json
    name = data.get("name")

    if not name:
        return jsonify({"ok": False, "msg": "Name required"}), 400

    user = {
        "user_id": str(int(time.time() * 1000)),  # simple unique ID
        "name": name,
        "rfid": None,
        "pending": True
    }

    users_col.insert_one(user)

    return jsonify({"ok": True, "user_id": user["user_id"]})


# ====================================================
# REQUEST WRITE MODE
# ESP32 will switch Arduino to WRITE MODE
# ====================================================
@app.route("/request_write", methods=["POST"])
def request_write():
    data = request.json
    user_id = data.get("user_id")

    user = users_col.find_one({"user_id": user_id})
    if not user:
        return jsonify({"ok": False, "msg": "User not found"}), 404

    # tell ESP32 to switch Arduino into WRITE mode
    DEVICE_STATE["mode"] = "WRITE"
    DEVICE_STATE["target_user"] = user_id

    print("WRITE MODE REQUESTED for user:", user_id)

    return jsonify({"ok": True})


# ====================================================
# ESP32 POLLING ENDPOINT
# ESP32 calls this every 1 second
# ====================================================
@app.route("/device_mode", methods=["GET"])
def device_mode():
    return jsonify(DEVICE_STATE)


# ====================================================
# COMPLETE WRITE — ESP32 sends new RFID
# ====================================================
@app.route("/complete_write", methods=["POST"])
def complete_write():
    data = request.json
    user_id = data.get("user_id")
    rfid = data.get("rfid")

    if not user_id or not rfid:
        return jsonify({"ok": False, "msg": "Missing fields"}), 400

    user = users_col.find_one({"user_id": user_id})
    if not user:
        return jsonify({"ok": False, "msg": "User not found"}), 404

    # update user record
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"rfid": rfid, "pending": False}}
    )

    # reset device state
    DEVICE_STATE["mode"] = "SCAN"
    DEVICE_STATE["target_user"] = None

    print("WRITE COMPLETED:", user_id, rfid)

    return jsonify({"ok": True})


# ====================================================
# NORMAL SCAN MODE — ESP32 sends SCAN_UID:XXXX
# ====================================================
@app.route("/scan", methods=["POST"])
def scan():
    data = request.json
    rfid = data.get("rfid")

    user = users_col.find_one({"rfid": rfid})

    log_data = {
        "rfid": rfid,
        "name": user["name"] if user else "Unknown",
        "timestamp": time.time()
    }

    logs_col.insert_one(log_data)
    socketio.emit("scan_event", log_data)

    return jsonify({"status": "received"})


# ====================================================
# GET ALL USERS
# ====================================================
@app.route("/users", methods=["GET"])
def get_users():
    users = list(users_col.find({}, {"_id": 0}))
    return jsonify(users)


# ====================================================
# DELETE USER
# ====================================================
@app.route("/delete_user", methods=["POST"])
def delete_user():
    data = request.json
    rfid = data.get("rfid")

    if not rfid:
        return jsonify({"status": "error", "message": "Missing RFID"}), 400

    users_col.delete_one({"rfid": rfid})
    return jsonify({"status": "success"})


# ====================================================
# GET LOGS
# ====================================================
@app.route("/logs", methods=["GET"])
def get_logs():
    logs = list(logs_col.find({}, {"_id": 0}))
    return jsonify(logs)


# ====================================================
# RENDER SERVER RUNNER
# ====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)

