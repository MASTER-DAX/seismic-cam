# RFID System (Flask backend + Frontend + Arduino + ESP32 bridge)

## What’s included
- backend/ : Flask app (serves frontend + API)
- frontend/index.html : single-file UI
- Arduino + ESP32 example code (in README)
- Uses MongoDB (MONGO_URI environment variable)

## Quick setup (local)
1. Create MongoDB (Atlas) and get connection string.
2. In the backend folder create env variable: `MONGO_URI`
3. Create virtualenv, install:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   export MONGO_URI="your_mongo_uri"
   python backend/app.py
