import os
import re
import random
import time
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- NEW: Robust Cookie Rotation System ---
# List of paths where Render will place our secret files
# We will try them in this order.
COOKIE_FILE_PATHS = [
    '/etc/secrets/cookies1.txt',
    '/etc/secrets/cookies2.txt',
    '/etc/secrets/cookies3.txt',
    # Add more paths here if you uploaded more cookie files
    # '/etc/secrets/cookies4.txt',
]

# A simple in-memory set to track cookies that have failed during the server's current life.
# This resets if the server restarts, giving failed cookies a chance to work again.
FAILED_COOKIES = set()

def get_next_valid_cookie():
    """Finds the next available cookie path that hasn't failed yet."""
    for path in COOKIE_FILE_PATHS:
        if path not in FAILED_COOKIES and os.path.exists(path):
            # Check if the file is not empty
            if os.path.getsize(path) > 0:
                return path
            else:
                logging.warning(f"Cookie file exists but is empty: {path}")
                FAILED_COOKIES.add(path) # Treat empty file as a failure
    return None # Return None if all cookies have failed

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app, expose_headers=['Content-Length', 'Content-Disposition'])

def sanitize_filename(filename):
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)

@app.route('/api/get-info', methods=['POST'])
def get_info():
    # Simple rate limiting to appear more human
    time.sleep(random.uniform(0.5, 2.0))

    data = request.get_json()
    url = data.get('url')
    if not url: return jsonify({"error": "URL is required"}), 400

    # --- NEW: Retry Logic ---
    # We will loop through our available cookies until one works or we run out.
    for _ in range(len(COOKIE_FILE_PATHS)):
        cookie_path = get_next_valid_cookie()

        if not cookie_path:
            logging.error("All available cookie files have failed.")
            return jsonify({"error": "Could not process this video. The server's authentication resources are temporarily exhausted. Please try again later."}), 500

        logging.info(f"Attempting to fetch info using cookie: {os.path.basename(cookie_path)}")
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': cookie_path}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # If we get here, the cookie worked! Return the success response.
                logging.info(f"Successfully fetched info with {os.path.basename(cookie_path)}")
                video_formats, audio_formats, unique_resolutions = [], [], set()
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' and f.get('resolution'):
                        resolution = f.get('resolution')
                        if resolution not in unique_resolutions:
                            unique_resolutions.add(resolution)
                            video_formats.append({'resolution': resolution})
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        audio_formats.append({'quality': f.get('format_note', 'Audio'), 'filesize_str': f.get('filesize_approx_str', 'N/A'), 'url': f.get('url'), 'ext': f.get('ext')})
                video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
                return jsonify({'title': info.get('title', 'No title'), 'thumbnail': info.get('thumbnail', ''), 'video_formats': video_formats, 'audio_formats': audio_formats})

        except Exception as e:
            # This cookie failed. Log it, add it to the failed set, and let the loop try the next one.
            logging.warning(f"Cookie {os.path.basename(cookie_path)} failed. Error: {e}")
            FAILED_COOKIES.add(cookie_path)
    
    # If the loop finishes without a single success, it means all cookies failed.
    return jsonify({"error": "Could not process this video after trying all available authentication methods. The video may be private or restricted."}), 500


@app.route('/api/process-download', methods=['POST'])
def process_download():
    # For downloads, we'll just use the first available good cookie.
    cookie_path = get_next_valid_cookie()
    if not cookie_path:
        return jsonify({"error": "Server configuration error: Missing authentication."}), 500

    data = request.get_json()
    url, quality, video_title = data.get('url'), data.get('quality'), data.get('title')
    if not all([url, quality, video_title]): return jsonify({"error": "Missing required parameters"}), 400
    try:
        height = quality.split('x')[1]
        safe_title = sanitize_filename(video_title)
        filename = f"{safe_title}_{height}p.mp4"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        ydl_opts = {'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]', 'outtmpl': output_path, 'quiet': True, 'no_warnings': True, 'cookiefile': cookie_path}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logging.error(f"yt-dlp failed to process download: {e}")
        return jsonify({"error": "An internal server error occurred while processing your download."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)