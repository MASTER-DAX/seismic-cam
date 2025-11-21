
# backend/app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from db import get_user, register_user, list_users
from pathlib import Path

app = Flask(__name__)
CORS(app)

# === robust path to frontend folder (works on Render) ===
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR / ".." / "frontend").resolve()  # ../frontend

# store the last received uid (simple in-memory; you can persist if needed)
last_uid = None

# === Serve frontend index ===
@app.route("/")
def serve_index():
    # serve index.html from frontend dir
    return send_from_directory(str(FRONTEND_DIR), "index.html")

# serve other static files in frontend folder at /frontend/<path>
@app.route("/frontend/<path:path>")
def serve_frontend_file(path):
    return send_from_directory(str(FRONTEND_DIR), path)

# === API ===
@app.route("/update_card", methods=["POST"])
def update_card():
    """Called by ESP32 after reading UID from Arduino. Stores last_uid in memory."""
    global last_uid
    data = request.json or {}
    uid = data.get("uid")
    last_uid = uid
    return jsonify({"ok": True, "uid": uid})

@app.route("/last_card", methods=["GET"])
def last_card():
    """Frontend polls this endpoint to get the latest tapped UID."""
    return jsonify({"uid": last_uid})

@app.route("/check_card", methods=["POST"])
def check_card():
    """Check if UID exists in DB. Returns registered true/false and user details when present."""
    data = request.json or {}
    uid = data.get("uid")
    user = get_user(uid)
    if user:
        # return only needed fields (avoid sending _id raw)
        return jsonify({"registered": True, "user": {"name": user.get("name"), "email": user.get("email")}})
    else:
        return jsonify({"registered": False})

@app.route("/register", methods=["POST"])
def register():
    """Register a new card => store uid, name, email"""
    data = request.json or {}
    uid = data.get("uid")
    name = data.get("name")
    email = data.get("email")
    if not uid or not name:
        return jsonify({"ok": False, "msg": "uid and name required"}), 400

    register_user(uid, name, email)
    return jsonify({"ok": True, "msg": "Registered", "uid": uid})

@app.route("/users", methods=["GET"])
def users():
    """Admin endpoint to list users. (Optional)"""
    results = list_users()
    out = [{"uid": r.get("uid"), "name": r.get("name"), "email": r.get("email")} for r in results]
    return jsonify(out)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
