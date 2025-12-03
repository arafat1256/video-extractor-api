from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NEW RapidAPI credentials - YouTube Media Downloader
RAPIDAPI_KEY = "8323c19993msh133999b087688ffp15533fjsn39a277015a81"
RAPIDAPI_HOST = "youtube-media-downloader.p.rapidapi.com"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Video Extractor API is running',
        'version': '3.0.0 - New YouTube API'
    })

def is_youtube_url(url):
    """Check if URL is from YouTube"""
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)

def extract_youtube_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_with_rapidapi(url):
    """Extract YouTube video using NEW RapidAPI - YouTube Media Downloader"""
    try:
        logger.info(f"Using NEW RapidAPI for YouTube: {url}")
        
        # Extract video ID
        video_id = extract_youtube_video_id(url)
        if not video_id:
            logger.error("Could not extract video ID")
            return None
        
        logger.info(f"Video ID: {video_id}")
        
        # NEW API endpoint
        api_url = f"https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        
        params = {
            "videoId": video_id
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        
        logger.info(f"RapidAPI Status: {response.status_code}")
        logger.info(f"RapidAPI Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse response
            title = data.get('title', 'YouTube Video')
            thumbnail = data.get('thumbnail', {}).get('url')
            
            # Get video formats
            formats = data.get('formats', [])
            
            if formats:
                # Find best quality with audio
                best_format = None
                
                for fmt in formats:
                    if fmt.get('hasAudio') and fmt.get('hasVideo'):
                        if not best_format or fmt.get('quality', 0) > best_format.get('quality', 0):
                            best_format = fmt
                
                # If no combined format, try video-only
                if not best_format:
                    for fmt in formats:
                        if fmt.get('hasVideo'):
                            best_format = fmt
                            break
                
                if best_format:
                    return {
                        'success': True,
                        'title': title,
                        'thumbnail': thumbnail,
                        'downloadUrl': best_format.get('url'),
                        'quality': best_format.get('qualityLabel', 'HD'),
                        'extension': best_format.get('mimeType', 'mp4').split('/')[-1].split(';')[0],
                        'duration': data.get('lengthSeconds', 0),
                        'filesize': best_format.get('contentLength', 0),
                        'source': 'rapidapi-new'
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"NEW RapidAPI error: {str(e)}")
        return None

def extract_with_ytdlp(url):
    """Extract video using yt-dlp (Instagram, Facebook, TikTok)"""
    try:
        logger.info(f"Using yt-dlp for: {url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'geo_bypass': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'success': True,
                'title': info.get('title', 'video'),
                'thumbnail': info.get('thumbnail'),
                'downloadUrl': info.get('url'),
                'quality': info.get('format', 'Best Quality (HD + Audio)'),
                'extension': info.get('ext', 'mp4'),
                'duration': info.get('duration', 0),
                'filesize': info.get('filesize', 0),
                'source': 'ytdlp'
            }
            
    except Exception as e:
        logger.error(f"yt-dlp error: {str(e)}")
        return None

@app.route('/api/extract', methods=['POST'])
def extract_video():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        logger.info(f"Processing URL: {url}")
        
        # Route based on platform
        if is_youtube_url(url):
            # Try NEW RapidAPI for YouTube
            result = extract_with_rapidapi(url)
            
            if result:
                logger.info("Success via NEW RapidAPI")
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'YouTube extraction failed. Video may be private or unavailable.'
                }), 500
        else:
            # Use yt-dlp for other platforms
            result = extract_with_ytdlp(url)
            
            if result:
                logger.info("Success via yt-dlp")
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Platform not supported or video unavailable'
                }), 500
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
