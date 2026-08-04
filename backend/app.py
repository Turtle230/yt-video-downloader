import os
import re
import requests
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

def normalize_youtube_url(url):
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
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

    # Modern Cobalt v10 Payload Structure
    cobalt_payload = {
        "url": target_url,
        "downloadMode": "audio" if is_audio else "auto",
        "audioFormat": mode if is_audio else "mp3",
        "videoQuality": "720",
        "youtubeVideoCodec": "h264"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://cobalt.tools/"
    }

    # Backup instances if main instance rejects the payload
    instances = [
        "https://api.cobalt.tools/",
        "https://co.wuk.sh/"
    ]

    for instance in instances:
        try:
            response = requests.post(
                instance,
                json=cobalt_payload,
                headers=headers,
                timeout=15
            )
            
            res_data = response.json()
            print(f"Instance [{instance}] Status: {response.status_code}, Body: {res_data}")

            if response.status_code == 200 and res_data.get("status") in ["tunnel", "redirect", "picker"]:
                return jsonify({
                    "download_url": res_data.get("url"),
                    "filename": res_data.get("filename", f"download.{mode}")
                })
            elif res_data.get("text"):
                error_detail = res_data.get("text")
                print(f"Cobalt Error Text: {error_detail}")

        except Exception as e:
            print(f"Failed contacting {instance}: {e}")

    return jsonify({"error": "Unable to extract stream from YouTube. Try again in a moment."}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)