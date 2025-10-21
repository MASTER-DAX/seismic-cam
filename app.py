from flask import Flask, render_template, request
import os
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    files = sorted([f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))], reverse=True)
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # ESP32-CAM sends raw jpeg data, so save it manually
        image_data = request.data
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(image_data)
        print(f"✅ Image saved: {filename}")
        return "Image received", 200
    except Exception as e:
        print("❌ Upload error:", e)
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
