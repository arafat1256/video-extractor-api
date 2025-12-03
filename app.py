from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import requests
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Social Download All In One API
RAPIDAPI_KEY = "8323c19993msh133999b087688ffp15533fjsn39a277015a81"
RAPIDAPI_HOST = "social-download-all-in-one.p.rapidapi.com"

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Video Extractor API is running',
        'version': '4.0.0 - Social Download All In One'
    })

def is_youtube_url(url):
    """Check if URL is from YouTube"""
    youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)

def extract_with_rapidapi(url):
    """Extract video using Social Download All In One API"""
    try:
        logger.info(f"Using Social Download API for: {url}")
        
        api_url = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST,
            "Content-Type": "application/json"
        }
        
        payload = {"url": url}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"API Status: {response.status_code}")
        logger.info(f"API Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if successful
            if data.get('status') == 'success':
                medias = data.get('medias', [])
                
                if medias and len(medias) > 0:
                    # Get best quality (first one is usually best)
                    best_media = medias[0]
                    
                    return {
                        'success': True,
                        'title': data.get('title', 'Video'),
                        'thumbnail': data.get('thumbnail'),
                        'downloadUrl': best_media.get('url'),
                        'quality': best_media.get('quality', 'HD'),
                        'extension': best_media.get('extension', 'mp4'),
                        'duration': data.get('duration', 0),
                        'filesize': best_media.get('size', 0),
                        'source': 'rapidapi'
                    }
                else:
                    logger.error("No media items found in response")
            else:
                logger.error(f"API returned error status: {data.get('status')}")
        else:
            logger.error(f"API request failed with status {response.status_code}")
        
        return None
        
    except Exception as e:
        logger.error(f"RapidAPI error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def extract_with_ytdlp(url):
    """Extract video using yt-dlp (fallback for non-YouTube platforms)"""
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
        
        # Try RapidAPI first for all platforms (YouTube, Instagram, TikTok, Facebook)
        result = extract_with_rapidapi(url)
        
        if result:
            logger.info(f"Success via RapidAPI: {result.get('title')}")
            return jsonify(result)
        
        # Fallback to yt-dlp for non-YouTube platforms if RapidAPI fails
        if not is_youtube_url(url):
            logger.info("RapidAPI failed, trying yt-dlp fallback...")
            result = extract_with_ytdlp(url)
            
            if result:
                logger.info(f"Success via yt-dlp: {result.get('title')}")
                return jsonify(result)
        
        # If everything fails
        return jsonify({
            'success': False,
            'error': 'Video extraction failed. Video may be private, age-restricted, or unavailable.'
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
