import os
import re
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

# --- Configuration ---
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- THE FINAL FIX: Robust Cookie Handling with Debugging ---
# This new function prepares the cookie file and will crash if it fails.
def prepare_cookie_file():
    render_cookie_path = '/etc/secrets/cookies.txt'
    local_cookie_path = 'cookies.txt'
    
    # Define a writable path for the final cookie file
    temp_cookie_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
    writable_cookie_path = temp_cookie_file.name
    
    source_path = None
    if os.path.exists(render_cookie_path):
        source_path = render_cookie_path
    elif os.path.exists(local_cookie_path):
        source_path = local_cookie_path

    if source_path:
        with open(source_path, 'r') as secret_file:
            cookie_content = secret_file.read()
            # If the cookie content is empty, raise an error immediately
            if not cookie_content.strip():
                raise RuntimeError("CRITICAL ERROR: The source cookie file is empty!")
            temp_cookie_file.write(cookie_content)
    else:
        # If no cookie file is found anywhere, this is a critical failure.
        raise FileNotFoundError("CRITICAL ERROR: No cookie file found at /etc/secrets/cookies.txt or locally.")
        
    temp_cookie_file.close()
    return writable_cookie_path

# Prepare the cookie file once when the app starts.
# If this fails, the app will crash and the Render logs will show the "CRITICAL ERROR" message.
WRITABLE_COOKIE_PATH = prepare_cookie_file()


# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app, expose_headers=['Content-Length', 'Content-Disposition'])

def sanitize_filename(filename):
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)

# --- All other code uses the prepared WRITABLE_COOKIE_PATH ---

@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        proxy_url = os.environ.get('PROXY_URL')
        ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': WRITABLE_COOKIE_PATH}
        if proxy_url: ydl_opts['proxy'] = proxy_url
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_formats, audio_formats, unique_resolutions = [], [], set()
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('resolution'):
                    resolution = f.get('resolution')
                    if resolution not in unique_resolutions:
                        unique_resolutions.add(resolution)
                        video_formats.append({'resolution': resolution})
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_formats.append({'quality': f.get('format_note', 'Audio'),'filesize_str': f.get('filesize_approx_str', 'N/A'),'url': f.get('url'), 'ext': f.get('ext')})
            video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)
            return jsonify({'title': info.get('title', 'No title'),'thumbnail': info.get('thumbnail', ''),'video_formats': video_formats,'audio_formats': audio_formats})
    except Exception as e:
        return jsonify({"error": f"An error occurred while fetching info: {str(e)}"}), 500

@app.route('/api/process-download', methods=['POST'])
def process_download():
    data = request.get_json()
    url, quality, video_title = data.get('url'), data.get('quality'), data.get('title')
    if not all([url, quality, video_title]):
        return jsonify({"error": "Missing required parameters for download."}), 400
    try:
        height = quality.split('x')[1]
        safe_title = sanitize_filename(video_title)
        filename = f"{safe_title}_{height}p.mp4"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        proxy_url = os.environ.get('PROXY_URL')
        ydl_opts = {'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]', 'outtmpl': output_path, 'quiet': True, 'no_warnings': True, 'cookiefile': WRITABLE_COOKIE_PATH}
        if proxy_url: ydl_opts['proxy'] = proxy_url
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to process download: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)