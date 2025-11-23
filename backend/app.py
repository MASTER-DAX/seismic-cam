from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os


app = Flask(__name__)
CORS(app)


# ==========================
# MongoDB Connection
# ==========================
MONGO_URI = os.getenv("MONGO_URI") # put in Render Environment
client = MongoClient(MONGO_URI)
db = client["smart_cottage"]
users = db["users"]


# ==========================
# ROUTES
# ==========================
@app.route("/register", methods=["POST"])
def register():
data = request.json
name = data.get("name")
age = data.get("age")


if not name or not age:
return jsonify({"ok": False, "msg": "Missing fields"}), 400


users.insert_one({"name": name, "age": age})
return jsonify({"ok": True, "msg": "User registered successfully"})




@app.route("/login", methods=["POST"])
def login():
data = request.json
name = data.get("name")


user = users.find_one({"name": name})


if not user:
return jsonify({"ok": False, "msg": "User not found"}), 404


return jsonify({"ok": True, "msg": f"Welcome back, {name}!"})




@app.route("/")
def home():
return "Backend running..."




if __name__ == "__main__":
app.run(host="0.0.0.0", port=5000)
