import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

# --- Configuration ---
# The folder where downloaded videos will be temporarily stored.
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Securely Handle Cookies at Startup ---
# This code runs once when the Flask application starts.
# 1. It checks for an environment variable named 'YT_COOKIES'.
# 2. If it exists, it writes its content to a 'cookies.txt' file in the same directory.
#    This file is used by yt-dlp but is NOT part of your GitHub repository.
# 3. If the environment variable is not found, it creates an empty file so the app doesn't crash.
YT_COOKIE_DATA = os.environ.get('YT_COOKIES')
COOKIE_FILE_PATH = 'cookies.txt'

if YT_COOKIE_DATA:
    with open(COOKIE_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(YT_COOKIE_DATA)
else:
    # Create an empty file if the environment variable is not set.
    # This allows the app to run locally without cookies, though it may be blocked by YouTube.
    open(COOKIE_FILE_PATH, 'a').close()
    print("WARNING: YT_COOKIES environment variable not found. App will run without authentication.")


# --- Initialize Flask App ---
app = Flask(__name__)
# --- Configure CORS to allow multiple frontends ---
# --- Configure CORS to allow multiple frontends ---
origins = [
    "http://localhost:3000", # For local development
    "https://ytv-downloader.netlify.app", # First live site (NO SLASH)
    "https://youtube-video-downloader-74eht97c2.vercel.app"  # Second live site (NO SLASH)
]

CORS(app, resources={r"/api/*": {"origins": origins}})

# --- Helper Function ---
def sanitize_filename(filename):
    """Removes characters that are invalid for Windows/Linux filenames."""
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)


# --- API Endpoint to Get Video Info ---
@app.route('/api/get-info', methods=['POST'])
def get_info():
    """
    Fetches video metadata and available format qualities without downloading.
    """
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # Use the dynamically created cookie file for authentication.
        ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': COOKIE_FILE_PATH}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_formats, audio_formats, unique_resolutions = [], [], set()

            for f in info.get('formats', []):
                # Filter for video formats
                if f.get('vcodec') != 'none' and f.get('resolution'):
                    resolution = f.get('resolution')
                    if resolution not in unique_resolutions:
                        unique_resolutions.add(resolution)
                        video_formats.append({'resolution': resolution})
                
                # Filter for audio-only streams
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_formats.append({
                        'quality': f.get('format_note', 'Audio'),
                        'filesize_str': f.get('filesize_approx_str', 'N/A'),
                        'url': f.get('url'),
                        'ext': f.get('ext')
                    })
            
            # Sort formats for a better user experience on the frontend
            video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)

            return jsonify({
                'title': info.get('title', 'No title'),
                'thumbnail': info.get('thumbnail', ''),
                'video_formats': video_formats,
                'audio_formats': audio_formats,
            })
    except Exception as e:
        return jsonify({"error": f"An error occurred while fetching info: {str(e)}"}), 500


# --- API Endpoint to Process and Download Video ---
@app.route('/api/process-download', methods=['POST'])
def process_download():
    """
    Downloads and merges the selected video quality with the best audio on the server,
    then sends the final file to the user. Requires FFmpeg.
    """
    data = request.get_json()
    url, quality, video_title = data.get('url'), data.get('quality'), data.get('title')

    if not all([url, quality, video_title]):
        return jsonify({"error": "Missing required parameters for download."}), 400
    
    try:
        height = quality.split('x')[1]
        safe_title = sanitize_filename(video_title)
        filename = f"{safe_title}_{height}p.mp4"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)

        # Use the cookie file here as well for the download process.
        ydl_opts = {
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True, 
            'cookiefile': COOKIE_FILE_PATH
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to process download: {str(e)}"}), 500


# --- Run the App ---
if __name__ == '__main__':
    # This block runs when you execute `python app.py`.
    # For production, a proper WSGI server like Gunicorn is used (configured on Render).
    app.run(debug=True, port=5000)