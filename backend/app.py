import os
import re
import tempfile
import logging
import random
import time
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

logging.basicConfig(level=logging.INFO)

# Global configuration
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

class CookieManager:
    def __init__(self):
        # Define multiple cookie file paths (both Render and local)
        self.cookie_files = [
            '/etc/secrets/cookies1.txt',
            '/etc/secrets/cookies2.txt', 
            '/etc/secrets/cookies3.txt',
            '/etc/secrets/cookies4.txt',
            '/etc/secrets/cookies5.txt',
            # Local fallbacks for development
            'cookies1.txt',
            'cookies2.txt',
            'cookies3.txt'
        ]
        self.last_used = {}
        self.failed_cookies = set()
        self.cooldown_period = timedelta(hours=1)  # 1 hour cooldown per cookie
        self.temp_cookie_files = {}
        self.lock = Lock()
    
    def prepare_cookie_file(self, source_path):
        """Convert a cookie file to a writable temporary file"""
        try:
            if not os.path.exists(source_path):
                return None
                
            temp_cookie_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=".txt", 
                mode='w', 
                encoding='utf-8'
            )
            
            with open(source_path, 'r', encoding='utf-8') as secret_file:
                cookie_content = secret_file.read()
                if not cookie_content.strip():
                    logging.warning(f"Cookie file {source_path} is empty")
                    temp_cookie_file.close()
                    os.unlink(temp_cookie_file.name)
                    return None
                temp_cookie_file.write(cookie_content)
            
            temp_cookie_file.close()
            self.temp_cookie_files[source_path] = temp_cookie_file.name
            logging.info(f"Prepared cookie file: {source_path} -> {temp_cookie_file.name}")
            return temp_cookie_file.name
            
        except Exception as e:
            logging.error(f"Failed to prepare cookie file {source_path}: {e}")
            return None
    
    def validate_cookie_file(self, cookie_path):
        """Test if a cookie file is still valid"""
        try:
            test_options = {
                'cookiefile': cookie_path,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'timeout': 30
            }
            
            with yt_dlp.YoutubeDL(test_options) as ydl:
                # Test with a simple, always-available video
                info = ydl.extract_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ', download=False)
                return info is not None
                
        except Exception as e:
            logging.warning(f"Cookie validation failed for {cookie_path}: {e}")
            return False
    
    def get_fresh_cookie_file(self):
        """Get a fresh, validated cookie file with rotation logic"""
        with self.lock:
            current_time = datetime.now()
            available_cookies = []
            
            # Check all cookie files
            for cookie_file in self.cookie_files:
                if not os.path.exists(cookie_file):
                    continue
                    
                # Skip failed cookies (but allow retry after extended cooldown)
                if cookie_file in self.failed_cookies:
                    last_failed = self.last_used.get(cookie_file + '_failed')
                    if last_failed and (current_time - last_failed) < timedelta(hours=6):
                        continue
                    else:
                        self.failed_cookies.discard(cookie_file)
                
                # Check cooldown period
                last_used = self.last_used.get(cookie_file)
                if not last_used or (current_time - last_used) > self.cooldown_period:
                    available_cookies.append(cookie_file)
            
            if not available_cookies:
                logging.warning("No available cookies found, trying least recently used")
                # If no cookies available, use the least recently used one
                if self.cookie_files:
                    sorted_cookies = sorted(
                        [f for f in self.cookie_files if os.path.exists(f)],
                        key=lambda x: self.last_used.get(x, datetime.min)
                    )
                    if sorted_cookies:
                        available_cookies = [sorted_cookies[0]]
            
            if not available_cookies:
                logging.error("No cookie files available at all")
                return None
            
            # Select random cookie from available ones
            chosen_cookie = random.choice(available_cookies)
            
            # Prepare the cookie file
            prepared_cookie = self.prepare_cookie_file(chosen_cookie)
            if not prepared_cookie:
                logging.error(f"Failed to prepare cookie file: {chosen_cookie}")
                return None
            
            # Validate the cookie
            if not self.validate_cookie_file(prepared_cookie):
                logging.warning(f"Cookie validation failed: {chosen_cookie}")
                self.failed_cookies.add(chosen_cookie)
                self.last_used[chosen_cookie + '_failed'] = current_time
                # Try another cookie
                return self.get_fresh_cookie_file() if len(available_cookies) > 1 else None
            
            # Mark as used
            self.last_used[chosen_cookie] = current_time
            logging.info(f"Using cookie file: {chosen_cookie}")
            return prepared_cookie
    
    def cleanup_temp_files(self):
        """Clean up temporary cookie files"""
        for temp_file in self.temp_cookie_files.values():
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        self.temp_cookie_files.clear()

class RequestThrottler:
    def __init__(self):
        self.request_times = defaultdict(list)
        self.lock = Lock()
        self.min_interval = 8  # Minimum 8 seconds between requests
        self.max_requests_per_hour = 25  # Conservative limit
        self.max_requests_per_day = 100
    
    def can_make_request(self, client_ip):
        with self.lock:
            now = time.time()
            hour_ago = now - 3600
            day_ago = now - 86400
            
            # Clean old requests
            self.request_times[client_ip] = [
                req_time for req_time in self.request_times[client_ip] 
                if req_time > day_ago
            ]
            
            recent_requests = self.request_times[client_ip]
            hourly_requests = [req for req in recent_requests if req > hour_ago]
            
            # Check daily limit
            if len(recent_requests) >= self.max_requests_per_day:
                return False, "Daily rate limit exceeded"
            
            # Check hourly limit
            if len(hourly_requests) >= self.max_requests_per_hour:
                return False, "Hourly rate limit exceeded"
            
            # Check minimum interval
            if recent_requests and (now - recent_requests[-1]) < self.min_interval:
                return False, f"Please wait {self.min_interval} seconds between requests"
            
            # Log this request
            self.request_times[client_ip].append(now)
            return True, "OK"
    
    def get_wait_time(self, client_ip):
        if not self.request_times[client_ip]:
            return 0
        return max(0, self.min_interval - (time.time() - self.request_times[client_ip][-1]))

# Initialize global managers
cookie_manager = CookieManager()
throttler = RequestThrottler()

app = Flask(__name__)
CORS(app, expose_headers=['Content-Length', 'Content-Disposition'])

def get_random_user_agent():
    """Return a random realistic user agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def get_ytdl_options(cookie_file=None):
    """Get enhanced yt-dlp options with better anti-detection"""
    options = {
        'quiet': True,
        'no_warnings': True,
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 5,
        'sleep_interval_subtitles': random.uniform(1, 2),
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'user_agent': get_random_user_agent(),
        'referer': 'https://www.youtube.com/',
        'headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        },
        'http_chunk_size': 10485760,  # 10MB chunks
        'timeout': 120,
    }
    
    if cookie_file:
        options['cookiefile'] = cookie_file
    
    return options

def sanitize_filename(filename):
    """Sanitize filename for safe file system usage"""
    return re.sub(r'[\/\?<>\\:\*\|"]', '_', filename)

def get_client_ip():
    """Get client IP address with proxy support"""
    return request.environ.get('HTTP_X_FORWARDED_FOR', 
                              request.environ.get('HTTP_X_REAL_IP', 
                                                request.remote_addr))

@app.route('/api/get-info', methods=['POST'])
def get_info():
    client_ip = get_client_ip()
    
    # Check rate limiting
    can_proceed, message = throttler.can_make_request(client_ip)
    if not can_proceed:
        return jsonify({"error": f"Rate limit exceeded: {message}"}), 429
    
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    # Add random delay to appear more human-like
    time.sleep(random.uniform(0.5, 2.0))
    
    cookie_file = cookie_manager.get_fresh_cookie_file()
    if not cookie_file:
        return jsonify({"error": "Server configuration error: No valid authentication available. Please try again later."}), 503
    
    try:
        ydl_opts = get_ytdl_options(cookie_file)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_formats = []
            audio_formats = []
            unique_resolutions = set()
            
            for f in info.get('formats', []):
                # Video formats
                if f.get('vcodec') != 'none' and f.get('resolution'):
                    resolution = f.get('resolution')
                    if resolution not in unique_resolutions:
                        unique_resolutions.add(resolution)
                        video_formats.append({'resolution': resolution})
                
                # Audio formats
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_formats.append({
                        'quality': f.get('format_note', 'Audio'),
                        'filesize_str': f.get('filesize_approx_str', 'N/A'),
                        'url': f.get('url'),
                        'ext': f.get('ext')
                    })
            
            # Sort formats
            video_formats.sort(key=lambda x: int(x['resolution'].split('x')[1]), reverse=True)
            audio_formats.sort(key=lambda x: x.get('abr') or 0, reverse=True)
            
            return jsonify({
                'title': info.get('title', 'No title'),
                'thumbnail': info.get('thumbnail', ''),
                'video_formats': video_formats,
                'audio_formats': audio_formats
            })
            
    except Exception as e:
        logging.error(f"yt-dlp failed to get info from {client_ip}: {e}")
        
        # More specific error messages
        error_msg = str(e).lower()
        if 'sign in' in error_msg or 'bot' in error_msg:
            return jsonify({"error": "Video requires additional verification. Please try a different video or try again later."}), 403
        elif 'private' in error_msg or 'unavailable' in error_msg:
            return jsonify({"error": "This video is private or unavailable for download."}), 404
        elif 'age' in error_msg:
            return jsonify({"error": "Age-restricted content cannot be processed."}), 403
        else:
            return jsonify({"error": "Could not process this video. Please try another video or try again later."}), 500

@app.route('/api/process-download', methods=['POST'])
def process_download():
    client_ip = get_client_ip()
    
    # Check rate limiting (stricter for downloads)
    can_proceed, message = throttler.can_make_request(client_ip)
    if not can_proceed:
        return jsonify({"error": f"Rate limit exceeded: {message}"}), 429
    
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality')
    video_title = data.get('title')
    
    if not all([url, quality, video_title]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Add random delay
    time.sleep(random.uniform(1.0, 3.0))
    
    cookie_file = cookie_manager.get_fresh_cookie_file()
    if not cookie_file:
        return jsonify({"error": "Server configuration error: No valid authentication available. Please try again later."}), 503
    
    try:
        height = quality.split('x')[1]
        safe_title = sanitize_filename(video_title)
        filename = f"{safe_title}_{height}p.mp4"
        output_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        ydl_opts = get_ytdl_options(cookie_file)
        ydl_opts.update({
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]',
            'outtmpl': output_path,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
        
    except Exception as e:
        logging.error(f"yt-dlp failed to process download from {client_ip}: {e}")
        
        error_msg = str(e).lower()
        if 'sign in' in error_msg or 'bot' in error_msg:
            return jsonify({"error": "Download requires additional verification. Please try again later."}), 403
        elif 'http error 429' in error_msg:
            return jsonify({"error": "Too many requests. Please wait before trying again."}), 429
        else:
            return jsonify({"error": "Download failed. Please try again later."}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    cookie_file = cookie_manager.get_fresh_cookie_file()
    return jsonify({
        "status": "healthy",
        "cookies_available": cookie_file is not None,
        "timestamp": datetime.now().isoformat()
    })

# Cleanup function
@app.teardown_appcontext
def cleanup(error):
    cookie_manager.cleanup_temp_files()

if __name__ == '__main__':
    app.run(debug=True, port=5000)