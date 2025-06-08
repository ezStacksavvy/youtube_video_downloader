import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

# --- Configuration ---
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Initialize Flask App ---
app = Flask(__name__)
# --- FIX IS HERE: Expose headers for the frontend to read ---
CORS(app, expose_headers=['Content-Length', 'Content-Disposition'])

# (The rest of the file is the same as the run.bat version)

def sanitize_filename(filename):
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)

@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': 'cookies.txt'}
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
                    audio_formats.append({'quality': f.get('format_note', 'Audio'), 'filesize_str': f.get('filesize_approx_str', 'N/A'), 'url': f.get('url'), 'ext': f.get('ext')})
            video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)
            return jsonify({'title': info.get('title', 'No title'), 'thumbnail': info.get('thumbnail', ''), 'video_formats': video_formats, 'audio_formats': audio_formats})
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
        ydl_opts = {'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]', 'outtmpl': output_path, 'quiet': True, 'no_warnings': True, 'cookiefile': 'cookies.txt'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to process download: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)