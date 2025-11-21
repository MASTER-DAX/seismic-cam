# backend/app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from db import find_user_by_uid, register_user, trigger_buzzer_event, list_users

# --------------------
# FLASK CONFIG
# --------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# IMPORTANT FIX: Render + Gunicorn DO NOT support eventlet/gevent
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# --------------------
# ESP32 -> Backend
# --------------------
@app.route("/esp/read", methods=["POST"])
def esp_read():
    """
    ESP32 sends JSON: {"uid": "AB12CD34"}
    Response: {"buzzer": true/false, "message": "..."}
    """
    data = request.get_json(force=True, silent=True) or {}
    uid = (data.get("uid") or "").strip()

    if not uid:
        return jsonify({"error": "missing uid"}), 400

    user = find_user_by_uid(uid)

    if user:
        # notify frontend
        payload = {
            "uid": uid,
            "status": "registered",
            "user": {
                "name": user.get("name"),
                "email": user.get("email"),
            },
        }
        socketio.emit("card_scanned", payload)

        # log event
        trigger_buzzer_event(uid, {"reason": "registered_card_scanned"})

        return jsonify({
            "buzzer": True,
            "message": f"Welcome {user.get('name') or 'user'}"
        }), 200

    else:
        payload = {"uid": uid, "status": "unregistered"}
        socketio.emit("card_scanned", payload)

        return jsonify({
            "buzzer": False,
            "message": "Invalid / not registered card"
        }), 200


# --------------------
# FRONTEND REST API
# --------------------
@app.route("/api/check/<uid>", methods=["GET"])
def api_check(uid):
    uid = uid.strip()
    user = find_user_by_uid(uid)

    if user:
        return jsonify({
            "found": True,
            "user": {
                "uid": user["uid"],
                "name": user.get("name"),
                "email": user.get("email")
            }
        })
    return jsonify({"found": False})


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    uid = (data.get("uid") or "").strip()
    name = data.get("name")
    email = data.get("email")

    if not uid or not name:
        return jsonify({"error": "uid and name required"}), 400

    try:
        doc, created = register_user({
            "uid": uid,
            "name": name,
            "email": email,
            "meta": data.get("meta", {})
        })

        socketio.emit("user_registered", {
            "uid": uid,
            "name": name,
            "email": email,
            "created": created
        })

        return jsonify({
            "ok": True,
            "created": created,
            "user": {
                "uid": doc["uid"],
                "name": doc.get("name"),
                "email": doc.get("email")
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users", methods=["GET"])
def api_users():
    users = list_users()
    sanitized = [
        {"uid": u.get("uid"), "name": u.get("name"), "email": u.get("email")}
        for u in users
    ]
    return jsonify({"users": sanitized})


@app.route("/api/trigger_buzzer", methods=["POST"])
def api_trigger_buzzer():
    data = request.get_json(force=True, silent=True) or {}
    uid = (data.get("uid") or "").strip()

    if not uid:
        return jsonify({"error": "uid required"}), 400

    details = {"duration_ms": data.get("duration_ms", 200)}
    trigger_buzzer_event(uid, details)

    socketio.emit("buzzer", {"uid": uid, "details": details})

    return jsonify({"ok": True})


# --------------------
# SOCKET EVENTS
# --------------------
@socketio.on("connect")
def on_connect():
    print("Client connected")


@socketio.on("disconnect")
def on_disconnect():
    print("Client disconnected")


# --------------------
# ENTRY POINT
# --------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting app on 0.0.0.0:{port}")
    socketio.run(app, host="0.0.0.0", port=port)
