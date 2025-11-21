
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ------------------- CONFIG --------------------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["rfid_system"]
users = db["users"]

# Flask App
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# ------------------------------------------------


# ============ REGISTER USER (Name Only) =====================
@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.json
    name = data.get("name")

    if not name:
        return jsonify({"error": "Name required"}), 400

    # Create placeholder for card ID (assigned later via write mode)
    user_id = users.insert_one({
        "name": name,
        "card_id": None
    }).inserted_id

    return jsonify({"message": "User created", "user_id": str(user_id)}), 200


# ============ TRIGGER WRITE MODE FOR ESP32 ==================
@app.route("/api/write-command", methods=["POST"])
def write_command():
    data = request.json
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "UserID missing"}), 400

    # Inform ESP32 via WebSocket
    socketio.emit("write_mode", {"user_id": user_id})

    return jsonify({"message": "Write mode triggered"}), 200


# =============== ESP32 CONFIRMS RFID WRITE ==================
@app.route("/api/confirm-write", methods=["POST"])
def confirm_write():
    data = request.json
    user_id = data.get("user_id")
    card_id = data.get("card_id")

    if not user_id or not card_id:
        return jsonify({"error": "Missing data"}), 400

    users.update_one({"_id": user_id}, {"$set": {"card_id": card_id}})

    return jsonify({"message": "RFID saved to user"}), 200


# =============== VALIDATE RFID ON SCAN ======================
@app.route("/api/validate-rfid", methods=["POST"])
def validate_rfid():
    data = request.json
    card_id = data.get("card_id")

    user = users.find_one({"card_id": card_id})

    if user:
        return jsonify({"access": True, "name": user["name"]}), 200
    else:
        return jsonify({"access": False}), 200


# ------------------- RUN SERVER ---------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
