import os
import shutil
import subprocess
import tempfile
from flask import Flask, request, send_from_directory, jsonify, send_file
from flask_cors import CORS
import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

# YouTube now requires solving JS challenges to get real format URLs, which
# needs an external JS runtime (Deno recommended). Render's build step and
# runtime step can have different $HOME values, so installing to ~/.deno
# isn't reliable - the Build Command instead installs Deno to a path tied
# to the repo checkout itself (see DENO_INSTALL in the Build Command),
# which stays consistent between build and runtime.
_DENO_BIN_CANDIDATES = [
    os.path.abspath(os.path.join(BASE_DIR, '..', '.deno', 'bin')),
    os.path.join(os.path.expanduser('~'), '.deno', 'bin'),  # fallback for local dev
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

print(f"[startup] HOME={os.path.expanduser('~')} checked_dirs={_DENO_BIN_CANDIDATES} "
      f"deno_bin_dir={_deno_bin_dir} deno_path={DENO_PATH} deno_version={DENO_VERSION}")

# Render always places secret files at /etc/secrets/<filename>, regardless
# of the service's Root Directory setting - check there first. Fall back to
# a local cookies.txt next to app.py for local development on your laptop.
_COOKIE_CANDIDATES = [
    '/etc/secrets/cookies.txt',
    os.path.join(BASE_DIR, 'cookies.txt'),
]
_source_cookie_path = next((p for p in _COOKIE_CANDIDATES if os.path.exists(p)), None)

COOKIES_PATH = None
HAS_COOKIES = False

if _source_cookie_path:
    # /etc/secrets is read-only, but yt-dlp needs to write updated cookie
    # values back to the file as it uses them - so copy it into a writable
    # location once at startup and use that copy instead.
    try:
        writable_cookie_dir = tempfile.mkdtemp(prefix='cookies_')
        COOKIES_PATH = os.path.join(writable_cookie_dir, 'cookies.txt')
        shutil.copyfile(_source_cookie_path, COOKIES_PATH)
        HAS_COOKIES = True
    except Exception as e:
        print(f"Failed to copy cookies.txt to a writable location: {e}")

# Player-client fallback order.
# None = let yt-dlp pick its own default client rotation, which is smarter
# than hardcoding one - it already knows to skip clients with known issues
# (e.g. tv client formats are currently DRM-protected, mweb requires a PO
# token we don't have). Only fall back to forcing a specific client if the
# default behavior somehow fails.
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
        'restrictfilenames': True,  # avoids unicode/emoji filename issues on Linux
        'remote_components': ['ejs:github'],  # allow fetching updated JS challenge solver if needed
    }

    if player_client is not None:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': player_client}}

    if HAS_COOKIES:
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
                    base, _ = os.path.splitext(downloaded_path)
                    final_path = f"{base}.mp4"

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
            print(f"yt-dlp failed with player_client={player_client or 'default'} (cookies={'yes' if HAS_COOKIES else 'no'}): {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            continue  # try the next player client

    if not HAS_COOKIES:
        hint = " No cookies.txt was found on the server - this is very likely why every client failed."
    else:
        deno_info = f"[deno_found={bool(DENO_PATH)} deno_path={DENO_PATH} deno_version={DENO_VERSION}]"
        hint = f" {deno_info}"
        # Every client failed even with cookies - find out what formats
        # yt-dlp can actually see for this video, to know if it's a real
        # format-selection bug or the video has no usable formats at all.
        try:
            debug_opts = {
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'cookiefile': COOKIES_PATH,
                'remote_components': ['ejs:github'],
                'extractor_args': {'youtube': {'player_client': ['web']}},
            }
            with yt_dlp.YoutubeDL(debug_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                summary = ", ".join(
                    f"{f.get('format_id')}:{f.get('ext')}:{f.get('vcodec')}/{f.get('acodec')}"
                    for f in formats[:15]
                )
                hint = f" {deno_info} Available formats seen ({len(formats)} total): {summary}"
        except Exception as debug_e:
            hint = f" {deno_info} Could not list formats either: {debug_e}"

    return jsonify({"error": f"Failed to process download: {str(last_error)}.{hint}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)