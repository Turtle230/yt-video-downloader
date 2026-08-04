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

    # Bypasses bot verification checks on datacenter hosts
    ydl_opts = {
        'format': 'best' if is_audio else 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'cachedir': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android'],
                'player_skip': ['js', 'configs', 'webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            direct_url = None
            if 'formats' in info:
                # Grab the first available direct HTTP video/audio stream URL
                for f in info['formats']:
                    if f.get('url') and 'googlevideo.com' in f.get('url'):
                        direct_url = f['url']
                        break

            if not direct_url:
                direct_url = info.get('url')

            if direct_url:
                return jsonify({
                    "download_url": direct_url,
                    "title": info.get('title', 'download')
                })

            return jsonify({"error": "Unable to extract stream."}), 400

    except Exception as e:
        print(f"yt-dlp extraction error: {e}")
        return jsonify({"error": "YouTube blocked this IP request. Try again in a minute."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)