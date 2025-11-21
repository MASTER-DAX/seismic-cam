from flask_cors import CORS
import os
import time
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from db import users_col, logs_col

app = Flask(__name__)
CORS(app)  # <--- VERY IMPORTANT
socketio = SocketIO(app, cors_allowed_origins="*")


# ======================================
# HOME - SERVE FRONTEND
# ======================================
@app.route("/")
def home():
    return render_template("dashboard.html")


# ======================================
# ADD USER
# ======================================
@app.route("/add_user", methods=["POST"])
def add_user():
    data = request.json
    rfid = data.get("rfid")
    name = data.get("name")

    if not rfid or not name:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    # Prevent duplicates
    if users_col.find_one({"rfid": rfid}):
        return jsonify({"status": "error", "message": "RFID already exists"}), 409

    users_col.insert_one({
        "rfid": rfid,
        "name": name
    })

    return jsonify({"status": "success", "message": "User added"})


# ======================================
# GET ALL USERS
# ======================================
@app.route("/users", methods=["GET"])
def get_users():
    users = list(users_col.find({}, {"_id": 0}))
    return jsonify(users)


# ======================================
# DELETE USER
# ======================================
@app.route("/delete_user", methods=["POST"])
def delete_user():
    data = request.json
    rfid = data.get("rfid")

    if not rfid:
        return jsonify({"status": "error", "message": "Missing RFID"}), 400

    users_col.delete_one({"rfid": rfid})

    return jsonify({"status": "success", "message": "User deleted"})


# ======================================
# RFID SCAN ENDPOINT (ESP32 → SERVER)
# ======================================
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


# ======================================
# GET LOG HISTORY
# ======================================
@app.route("/logs", methods=["GET"])
def get_logs():
    logs = list(logs_col.find({}, {"_id": 0}))
    return jsonify(logs)


# ======================================
# RUN SERVER (RENDER COMPATIBLE)
# ======================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns PORT
    socketio.run(app, host="0.0.0.0", port=port)
