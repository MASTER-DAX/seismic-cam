
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from db import find_user_by_uid, register_user, trigger_buzzer_event, list_all

# --------------------
# FLASK CONFIG
# --------------------
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# --------------------
# ROUTES
# --------------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/tap', methods=['POST'])
def tap_card():
    data = request.get_json() or {}
    uid = data.get('uid')
    if not uid:
        return jsonify({'error': 'no uid'}), 400

    # Log tap
    # trigger buzzer or store timestamp
    trigger_buzzer_event(uid)

    # Emit to frontend
    socketio.emit('card_tapped', {'uid': uid})

    # Return user info if registered
    user = find_user_by_uid(uid)
    if user:
        return jsonify({'status': 'ok', 'user': user})

    return jsonify({'status': 'ok'})

@app.route('/api/register_card', methods=['POST'])
def register_card():
    data = request.get_json() or {}
    uid = data.get('uid')
    name = data.get('name')
    employee_id = data.get('employee_id')
    access_level = data.get('access_level')
    valid_until = data.get('valid_until')
    write_to_card = data.get('write_to_card', False)
    write_payload = data.get('write_payload', {})

    if not uid or not name:
        return jsonify({'error': 'uid and name required'}), 400

    doc = {
        'uid': uid,
        'name': name,
        'employee_id': employee_id,
        'access_level': access_level,
        'valid_until': valid_until
    }

    register_user(doc)

    if write_to_card:
        # store write task in database
        pass

    return jsonify({'status': 'saved'})

@app.route('/api/pending_write', methods=['GET'])
def pending_write():
    # backend returns pending write tasks for ESP32
    return jsonify({})

# --------------------
# RUN
# --------------------
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
