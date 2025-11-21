
# app.py
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from db import users_col, logs_col
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================
# ROOT (SERVE FRONTEND)
# ==========================
@app.route("/")
def home():
       return render_template("dashboard.html")

# ==========================
# API: ADD USER
# ==========================
@app.route("/add_user", methods=["POST"])
def add_user():
    data = request.json
    rfid = data.get("rfid")
    name = data.get("name")

    if not rfid or not name:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    # check if RFID already exists
    if users_col.find_one({"rfid": rfid}):
        return jsonify({"status": "error", "message": "RFID already registered"}), 409

    users_col.insert_one({
        "rfid": rfid,
        "name": name
    })

    return jsonify({"status": "success", "message": "User added!"})

# ==========================
# API: GET ALL USERS
# ==========================
@app.route("/users", methods=["GET"])
def get_users():
    users = list(users_col.find({}, {"_id": 0}))
    return jsonify(users)

# ==========================
# API: DELETE USER
# ==========================
@app.route("/delete_user", methods=["POST"])
def delete_user():
    data = request.json
    rfid = data.get("rfid")

    if not rfid:
        return jsonify({"status": "error", "message": "Missing RFID"}), 400

    users_col.delete_one({"rfid": rfid})
    return jsonify({"status": "success", "message": "User deleted!"})

# ==========================
# API: RFID SCAN ENDPOINT
# (ESP32 → SERVER)
# ==========================
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

    # notify frontend via websocket
    socketio.emit("scan_event", log_data)

    return jsonify({"status": "received"})

# ==========================
# API: GET LOG HISTORY
# ==========================
@app.route("/logs", methods=["GET"])
def get_logs():
    logs = list(logs_col.find({}, {"_id": 0}))
    return jsonify(logs)

# ==========================
# RUN SERVER
# ==========================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
