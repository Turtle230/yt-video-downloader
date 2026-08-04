import os
import re
import glob
import tempfile
import traceback
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app, expose_headers=["Content-Disposition"])

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "yt_downloader_temp")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

def get_yt_opts(mode, output_template):
    opts = {
        'outtmpl': output_template,
        'quiet': True,
        'noprogress': True,
        'nocheckcertificate': True,
        'remote_components': ['ejs:github'],
        'extractor_args': {
            'youtube': {
                'player_js_variant': ['tv'],
                'player_client': ['tv', 'mweb']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    
    if mode == 'mp3':
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    elif mode == 'ogg':
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'vorbis', # Uses standard OGG Vorbis encoding
                'preferredquality': '192',
            }]
        })
    else:
        opts.update({
            'format': 'best[ext=mp4]/best',
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
        # Unique prefix identifier for dynamic matching
        unique_prefix = f"dl_{os.urandom(4).hex()}_"
        temp_template = os.path.join(DOWNLOAD_DIR, f"{unique_prefix}%(title)s.%(ext)s")
        opts = get_yt_opts(mode, temp_template)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        
        # Locate the exact generated file dynamically (handles .ogg / .opus conversion edge cases)
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
    app.run(host='0.0.0.0', port=5000, debug=True)