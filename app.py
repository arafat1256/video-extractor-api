from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RapidAPI credentials for YouTube fallback
RAPIDAPI_KEY = "01895d9745msha194600cb99baebp130d5djsn2bae2cf551d8"
RAPIDAPI_HOST = "social-download-all-in-one.p.rapidapi.com"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Video Extractor API is running',
        'version': '2.0.0 - Hybrid'
    })

def is_youtube_url(url):
    """Check if URL is from YouTube"""
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)

def extract_with_rapidapi(url):
    """Extract YouTube video using RapidAPI"""
    try:
        logger.info(f"Using RapidAPI for YouTube: {url}")
        
        api_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST,
            "Content-Type": "application/json"
        }
        
        payload = {"url": url}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                medias = data.get('medias', [])
                
                if medias:
                    # Get best quality
                    best_media = medias[0]
                    
                    return {
                        'success': True,
                        'title': data.get('title', 'YouTube Video'),
                        'thumbnail': data.get('thumbnail'),
                        'downloadUrl': best_media.get('url'),
                        'quality': best_media.get('quality', 'HD'),
                        'extension': best_media.get('extension', 'mp4'),
                        'duration': 0,
                        'filesize': best_media.get('size', 0),
                        'source': 'rapidapi'
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"RapidAPI error: {str(e)}")
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
            # Try RapidAPI for YouTube
            result = extract_with_rapidapi(url)
            
            if result:
                logger.info("Success via RapidAPI")
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'YouTube extraction failed. Video may be unavailable.'
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
