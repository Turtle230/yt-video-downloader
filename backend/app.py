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
        return jsonify({"error": "Please enter a valid URL."}), 400

    is_audio = mode in ['mp3', 'ogg']

    # Configuration tuned specifically to bypass datacenter IP blocks on Render
    ydl_opts = {
        'format': 'bestaudio/best' if is_audio else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cachedir': False,
        # Force mobile/TV clients to bypass YouTube datacenter IP restrictions
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'tv_embed'],
                'skip': ['dash', 'hls']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Retrieve direct media stream URL
            direct_url = info.get('url')
            if not direct_url and 'requested_formats' in info:
                direct_url = info['requested_formats'][0].get('url')

            if direct_url:
                return jsonify({
                    "download_url": direct_url,
                    "title": info.get('title', 'download')
                })
            
            return jsonify({"error": "Could not extract direct stream URL."}), 400

    except Exception as e:
        print(f"yt-dlp extraction error: {e}")
        return jsonify({"error": "Extraction failed. YouTube stream unreachable."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)