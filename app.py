from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import logging
import re

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
        'version': '3.1.0 - Fixed YouTube API'
    })

def is_youtube_url(url):
    """Check if URL is from YouTube"""
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)

def extract_youtube_video_id(url):
    """Extract video ID from YouTube URL"""
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
    """Extract YouTube video using YouTube Media Downloader API"""
    try:
        logger.info(f"Using YouTube Media Downloader API for: {url}")
        
        # Extract video ID
        video_id = extract_youtube_video_id(url)
        if not video_id:
            logger.error("Could not extract video ID")
            return None
        
        logger.info(f"Video ID: {video_id}")
        
        # Get video info first
        info_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        
        params = {"videoId": video_id}
        
        info_response = requests.get(info_url, headers=headers, params=params, timeout=30)
        
        logger.info(f"Info API Status: {info_response.status_code}")
        
        if info_response.status_code != 200:
            logger.error(f"Info API failed: {info_response.text[:200]}")
            return None
        
        info_data = info_response.json()
        logger.info(f"Info Response: {str(info_data)[:300]}")
        
        # Check if video is available
        if info_data.get('errorId') != 'Success':
            logger.error(f"Video error: {info_data.get('errorId')}")
            return None
        
        title = info_data.get('title', 'YouTube Video')
        
        # Get download links
        download_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/download"
        
        download_response = requests.get(download_url, headers=headers, params=params, timeout=30)
        
        logger.info(f"Download API Status: {download_response.status_code}")
        
        if download_response.status_code != 200:
            logger.error(f"Download API failed: {download_response.text[:200]}")
            return None
        
        download_data = download_response.json()
        logger.info(f"Download Response: {str(download_data)[:500]}")
        
        # Extract download links
        links = download_data.get('links', [])
        
        if not links:
            logger.error("No download links found")
            return None
        
        # Find best quality with audio
        best_link = None
        
        # Priority: MP4 with highest quality
        for link in links:
            if link.get('format') == 'mp4':
                if not best_link or link.get('quality', 0) > best_link.get('quality', 0):
                    best_link = link
        
        # Fallback to any format
        if not best_link and links:
            best_link = links[0]
        
        if best_link:
            return {
                'success': True,
                'title': title,
                'thumbnail': info_data.get('thumbnail'),
                'downloadUrl': best_link.get('url'),
                'quality': f"{best_link.get('quality', 'HD')}",
                'extension': best_link.get('format', 'mp4'),
                'duration': info_data.get('duration', 0),
                'filesize': best_link.get('size', 0),
                'source': 'rapidapi-youtube'
            }
        
        return None
        
    except Exception as e:
        logger.error(f"YouTube API error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
            # Try YouTube Media Downloader API
            result = extract_with_rapidapi(url)
            
            if result:
                logger.info(f"Success via YouTube API: {result.get('title')}")
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'YouTube extraction failed. Video may be private, restricted, or unavailable.'
                }), 500
        else:
            # Use yt-dlp for other platforms
            result = extract_with_ytdlp(url)
            
            if result:
                logger.info(f"Success via yt-dlp: {result.get('title')}")
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Platform not supported or video unavailable'
                }), 500
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
