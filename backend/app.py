import os
import shutil
import tempfile
from flask import Flask, request, send_from_directory, jsonify, send_file
from flask_cors import CORS
import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))
COOKIES_PATH = os.path.join(BASE_DIR, 'cookies.txt')

# Try these YouTube "player clients" in order until one works.
# YouTube patches which ones bypass bot-detection fairly often, so this
# list may need updating over time - if downloads start failing again,
# that's the first thing to revisit.
PLAYER_CLIENT_FALLBACKS = [
    ['tv_embedded'],
    ['web_creator'],
    ['android', 'ios'],
    ['web_safari'],
    ['mweb'],
]

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


def build_ydl_opts(temp_dir, is_audio, mode, player_client):
    ydl_opts = {
        'format': 'bestaudio/best' if is_audio else 'best[ext=mp4]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'restrictfilenames': True,  # avoids unicode/emoji filename issues on Linux
        'extractor_args': {'youtube': {'player_client': player_client}},
    }

    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH

    if is_audio:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': mode,  # 'mp3' or 'ogg'
            'preferredquality': '192',
        }]

    return ydl_opts


@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    mode = data.get('mode', 'mp4')

    if not url:
        return jsonify({"error": "Please enter a valid URL."}), 400

    is_audio = mode in ['mp3', 'ogg']

    last_error = None

    for player_client in PLAYER_CLIENT_FALLBACKS:
        temp_dir = tempfile.mkdtemp()
        ydl_opts = build_ydl_opts(temp_dir, is_audio, mode, player_client)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_path = ydl.prepare_filename(info)

                if is_audio:
                    base, _ = os.path.splitext(downloaded_path)
                    final_path = f"{base}.{mode}"
                else:
                    final_path = downloaded_path

                if not os.path.exists(final_path):
                    raise FileNotFoundError(f"Expected output file not found: {final_path}")

                response = send_file(
                    final_path,
                    as_attachment=True,
                    download_name=os.path.basename(final_path)
                )

                @response.call_on_close
                def cleanup(temp_dir=temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

                return response

        except Exception as e:
            last_error = e
            print(f"yt-dlp failed with player_client={player_client}: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            continue  # try the next player client

    # every client in the fallback list failed
    return jsonify({"error": f"Failed to process download: {str(last_error)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)