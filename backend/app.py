import os
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import yt_dlp

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

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    mode = data.get('mode', 'mp4')

    if not url:
        return jsonify({"error": "Please supply a valid URL"}), 400

    is_audio = mode in ['mp3', 'ogg']

    ydl_opts = {
        'format': 'bestaudio/best' if is_audio else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract direct media URL stream
            direct_url = info.get('url')
            if not direct_url and 'requested_formats' in info:
                direct_url = info['requested_formats'][0].get('url')

            if direct_url:
                return jsonify({
                    "download_url": direct_url,
                    "title": info.get('title', 'download')
                })
            else:
                return jsonify({"error": "Unable to extract playable stream URL."}), 400

    except Exception as e:
        print(f"yt-dlp extraction error: {e}")
        return jsonify({"error": "Extraction failed. YouTube may be throttling server IPs."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)