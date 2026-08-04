import os
import re
import requests
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

# Serve static frontend files
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

def normalize_youtube_url(url):
    """Convert short links (youtu.be/ID) to full standard YouTube watch URLs."""
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json() or {}
    raw_url = data.get('url', '').strip()
    mode = data.get('mode', 'mp4')

    if not raw_url:
        return jsonify({"error": "No URL provided"}), 400

    target_url = normalize_youtube_url(raw_url)
    is_audio = mode in ['mp3', 'ogg']

    cobalt_payload = {
        "url": target_url,
        "downloadMode": "audio" if is_audio else "auto",
        "audioFormat": mode if is_audio else "mp3",
        "videoQuality": "max"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(
            "https://api.cobalt.tools/",
            json=cobalt_payload,
            headers=headers,
            timeout=20
        )
        
        res_data = response.json()

        if response.status_code != 200 or res_data.get("status") == "error":
            error_msg = res_data.get("text", "Failed to resolve stream link")
            return jsonify({"error": error_msg}), 400

        return jsonify({
            "download_url": res_data.get("url"),
            "filename": res_data.get("filename", f"download.{mode}")
        })

    except requests.exceptions.RequestException as e:
        print(f"Cobalt Request Failed: {e}")
        return jsonify({"error": "External stream resolver unreachable"}), 502
    except Exception as e:
        print(f"Backend Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)