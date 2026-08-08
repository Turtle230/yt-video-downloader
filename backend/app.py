import os
import shutil
import subprocess
import tempfile
import imageio_ffmpeg
from flask import Flask, request, send_from_directory, jsonify, send_file
from flask_cors import CORS
import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

# Retrieve dynamically bundled FFmpeg executable path
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# YouTube JS runtime environment check
_DENO_BIN_CANDIDATES = [
    os.path.abspath(os.path.join(BASE_DIR, '..', '.deno', 'bin')),
    os.path.join(os.path.expanduser('~'), '.deno', 'bin'),
]
_deno_bin_dir = next((p for p in _DENO_BIN_CANDIDATES if os.path.isdir(p)), None)
if _deno_bin_dir:
    os.environ['PATH'] = _deno_bin_dir + os.pathsep + os.environ.get('PATH', '')

DENO_PATH = shutil.which('deno')
DENO_VERSION = None
if DENO_PATH:
    try:
        DENO_VERSION = subprocess.run(
            [DENO_PATH, '--version'], capture_output=True, text=True, timeout=10
        ).stdout.strip().splitlines()[0]
    except Exception as e:
        DENO_VERSION = f"found but failed to run: {e}"

print(f"[startup] HOME={os.path.expanduser('~')} ffmpeg={FFMPEG_PATH} "
      f"deno_path={DENO_PATH} deno_version={DENO_VERSION}")

# Cookie file detection
_COOKIE_CANDIDATES = [
    '/etc/secrets/cookies.txt',
    os.path.join(BASE_DIR, 'cookies.txt'),
]
_source_cookie_path = next((p for p in _COOKIE_CANDIDATES if os.path.exists(p)), None)

COOKIES_PATH = None
HAS_COOKIES = False

if _source_cookie_path:
    try:
        writable_cookie_dir = tempfile.mkdtemp(prefix='cookies_')
        COOKIES_PATH = os.path.join(writable_cookie_dir, 'cookies.txt')
        shutil.copyfile(_source_cookie_path, COOKIES_PATH)
        HAS_COOKIES = True
    except Exception as e:
        print(f"Failed to copy cookies.txt: {e}")

PLAYER_CLIENT_FALLBACKS = [
    None,
    ['web'],
    ['web_creator'],
    ['android', 'ios'],
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
        'format': 'bestaudio/best' if is_audio else 'bv*+ba/b',
        'merge_output_format': None if is_audio else 'mp4',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'restrictfilenames': True,
        'remote_components': ['ejs:github'],
        'ffmpeg_location': FFMPEG_PATH,  # Dynamic FFmpeg executable location
    }

    if player_client is not None:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': player_client}}

    if HAS_COOKIES:
        ydl_opts['cookiefile'] = COOKIES_PATH

    if is_audio:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': mode,  # Handles 'mp3' or 'ogg'
            'preferredquality': '192',
        }]

    return ydl_opts

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    mode = data.get('mode', 'mp4')

    if not url:
        return jsonify({"error": "Please enter a valid YouTube URL."}), 400

    is_audio = mode in ['mp3', 'ogg']
    last_error = None

    for player_client in PLAYER_CLIENT_FALLBACKS:
        temp_dir = tempfile.mkdtemp()
        ydl_opts = build_ydl_opts(temp_dir, is_audio, mode, player_client)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_path = ydl.prepare_filename(info)

                base, _ = os.path.splitext(downloaded_path)
                final_path = f"{base}.{mode}" if is_audio else f"{base}.mp4"

                if not os.path.exists(final_path):
                    # Fallback check for alternate generated file extensions
                    matched_files = [
                        os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                        if f.endswith(f".{mode}") or (not is_audio and f.endswith(".mp4"))
                    ]
                    if matched_files:
                        final_path = matched_files[0]
                    else:
                        raise FileNotFoundError(f"Processed output file standard missing: {final_path}")

                response = send_file(
                    final_path,
                    as_attachment=True,
                    download_name=os.path.basename(final_path)
                )

                @response.call_on_close
                def cleanup(target_dir=temp_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)

                return response

        except Exception as e:
            last_error = e
            print(f"yt-dlp error (client={player_client or 'default'}): {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            continue

    return jsonify({"error": f"Extraction failed: {str(last_error)}"}), 500

# Global exception fallback handler to prevent raw HTML responses
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    print(f"Unhandled Exception: {e}")
    return jsonify({"error": "An internal server error occurred while processing the request."}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)