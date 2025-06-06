import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app = Flask(__name__)
CORS(app)

COOKIE_FILE_PATH = 'cookies.txt'
if not os.path.exists(COOKIE_FILE_PATH):
    # This print statement is useful for local debugging
    print("WARNING: cookies.txt not found. This will likely fail on a live server.")

def sanitize_filename(filename):
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)

@app.route('/api/get-info', methods=['POST'])
def get_info():
    # This function remains unchanged
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': COOKIE_FILE_PATH}
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
                    audio_formats.append({'quality': f.get('format_note', 'Audio'),'filesize_str': f.get('filesize_approx_str', 'N/A'),'url': f.get('url'),'ext': f.get('ext')})
            video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)
            return jsonify({'title': info.get('title', 'No title'),'thumbnail': info.get('thumbnail', ''),'video_id': info.get('id'),'video_formats': video_formats,'audio_formats': audio_formats})
    except Exception as e:
        if "confirm you're not a bot" in str(e):
             return jsonify({"error": "Request blocked by YouTube (bot detection). The provided cookies may be invalid or expired."}), 500
        return jsonify({"error": f"An error occurred while fetching info: {str(e)}"}), 500

@app.route('/api/process-download', methods=['POST'])
def process_download():
    data = request.get_json()
    video_id, quality = data.get('video_id'), data.get('quality')
    if not all([video_id, quality]):
        return jsonify({"error": "Missing video_id or quality parameter."}), 400
    
    # Define output_path outside the try block so it's accessible in 'finally'
    output_path = None
    
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        info_opts = {'quiet': True, 'no_warnings': True, 'cookiefile': COOKIE_FILE_PATH}
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')

        height = quality.split('x')[1]
        safe_title = sanitize_filename(video_title)
        filename = f"{safe_title}_{height}p.mp4"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
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
    
    # --- THE FIX IS HERE: Automatic Cleanup ---
    finally:
        # This block will execute after the 'return' statement has sent the file.
        # It cleans up the downloaded file from the server's disk.
        if output_path and os.path.exists(output_path):
            print(f"Cleaning up file: {output_path}")
            os.remove(output_path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)