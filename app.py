# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_user, register_user

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"msg": "RFID Server Running"})

# Check if RFID card is registered
@app.route("/check_card", methods=["POST"])
def check_card():
    data = request.json
    uid = data.get("uid")

    user = get_user(uid)
    if user:
        return jsonify({"registered": True, "user": {
            "name": user["name"],
            "email": user["email"]
        }})
    else:
        return jsonify({"registered": False})

# Register new RFID card
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    uid = data.get("uid")
    name = data.get("name")
    email = data.get("email")

    register_user(uid, name, email)

    return jsonify({"ok": True, "msg": "User registered successfully!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
