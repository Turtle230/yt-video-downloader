import os
import re
import glob
import tempfile
import traceback
from flask import Flask, request, send_file, send_from_directory, jsonify
from flask_cors import CORS
import yt_dlp

# Resolve directory paths for hosting static frontend assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app, expose_headers=["Content-Disposition"])

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "yt_downloader_temp")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Frontend File Serving Routes ---

@app.route("/")
def index():
    """Serves the main Win95 interface."""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """Serves CSS, JS, and image assets from the frontend directory."""
    return send_from_directory(FRONTEND_DIR, filename)

# --- Downloader Helper Functions & API ---

def clean_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

def get_yt_opts(mode, output_template):
    opts = {
        'outtmpl': output_template,
        'quiet': True,
        'noprogress': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Safely load and validate PROXY_URL
    proxy_url = os.environ.get("PROXY_URL", "").strip()
    if proxy_url and not proxy_url.endswith(":port") and "your-proxy" not in proxy_url:
        opts['proxy'] = proxy_url

    if mode in ['mp3', 'ogg']:
        codec = 'mp3' if mode == 'mp3' else 'vorbis'
        opts.update({
            'format': 'ba/b',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '192',
            }]
        })
    else:
        opts.update({
            'format': 'bv*+ba/b/bv*/best',
            'merge_output_format': 'mp4',
        })
    return opts

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json() or {}
    url = data.get('url')
    mode = data.get('mode', 'mp4')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        unique_prefix = f"dl_{os.urandom(4).hex()}_"
        temp_template = os.path.join(DOWNLOAD_DIR, f"{unique_prefix}%(title)s.%(ext)s")
        opts = get_yt_opts(mode, temp_template)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        matching_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{unique_prefix}*"))
        if not matching_files:
            return jsonify({"error": "Downloaded file not found on server"}), 500

        actual_file_path = matching_files[0]
        safe_title = clean_filename(info.get('title', 'download'))
        ext = mode if mode in ['mp3', 'ogg'] else 'mp4'
        download_filename = f"{safe_title}.{ext}"

        response = send_file(
            actual_file_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/ogg' if mode == 'ogg' else 'application/octet-stream'
        )

        @response.call_on_close
        def remove_file():
            if os.path.exists(actual_file_path):
                try:
                    os.remove(actual_file_path)
                except Exception as cleanup_err:
                    print(f"Error removing temp file: {cleanup_err}")

        return response

    except Exception as e:
        print("Backend Download Exception:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)