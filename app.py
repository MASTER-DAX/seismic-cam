from flask import Flask, request, render_template_string
import os
from datetime import datetime

app = Flask(__name__)

# Use absolute path (safe for Render)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

# ✅ Safe folder creation to avoid FileExistsError on Render
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
    except FileExistsError:
        pass
    except PermissionError:
        print("⚠️ Warning: Cannot create uploads folder (permission denied). It may already exist.")

@app.route('/upload', methods=['POST'])
def upload_image():
    filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
    path = os.path.join(UPLOAD_FOLDER, filename)
    with open(path, "wb") as f:
        f.write(request.data)
    print(f"✅ Uploaded: {filename}")
    return "OK"

@app.route('/')
def index():
    # Sort newest first
    files = sorted(os.listdir(UPLOAD_FOLDER), reverse=True)
    html = """
    <html>
    <head>
        <title>Seismic Camera Captures</title>
        <style>
            body { font-family: Arial; text-align: center; background: #111; color: #fff; }
            img { width: 340px; margin: 10px; border-radius: 10px; box-shadow: 0 0 10px #45dfda; }
            h2 { color: #45dfda; }
        </style>
    </head>
    <body>
        <h2>🌋 Seismic Camera Captures</h2>
    """
    for file in files:
        html += f"<div><img src='/static/uploads/{file}'></div>"
    html += "</body></html>"
    return render_template_string(html)

if __name__ == '__main__':
    # Use port 10000 on Render if needed
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
