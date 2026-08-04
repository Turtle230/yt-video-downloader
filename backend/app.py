import os
import requests
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS

# Resolve directory paths for hosting static frontend assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

# --- Frontend File Serving Routes ---

@app.route("/")
def index():
    """Serves the main Win95 interface."""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """Serves CSS, JS, and image assets from the frontend directory."""
    return send_from_directory(FRONTEND_DIR, filename)

# --- Downloader API Route ---

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json() or {}
    url = data.get('url')
    mode = data.get('mode', 'mp4')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Determine format parameters for Cobalt
        is_audio = mode in ['mp3', 'ogg']
        
        cobalt_payload = {
            "url": url,
            "downloadMode": "audio" if is_audio else "auto",
            "audioFormat": mode if is_audio else "mp3",
            "videoQuality": "max"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Request stream resolution from Cobalt API
        response = requests.post(
            "https://api.cobalt.tools/", 
            json=cobalt_payload, 
            headers=headers,
            timeout=15
        )
        
        res_data = response.json()

        if response.status_code != 200 or res_data.get("status") == "error":
            error_msg = res_data.get("text", "Failed to resolve stream link")
            return jsonify({"error": error_msg}), 400

        # Return direct download URL for frontend redirection
        return jsonify({
            "download_url": res_data.get("url"),
            "filename": res_data.get("filename", f"download.{mode}")
        })

    except requests.exceptions.RequestException as e:
        print(f"Cobalt Request Failed: {e}")
        return jsonify({"error": "External stream resolver unreachable"}), 502
    except Exception as e:
        print(f"Backend Exception: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)