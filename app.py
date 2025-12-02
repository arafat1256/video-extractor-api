from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Video Extractor API is running',
        'version': '1.0.0'
    })

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
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_details = {
                'success': True,
                'title': info.get('title', 'video'),
                'thumbnail': info.get('thumbnail'),
                'downloadUrl': info.get('url'),
                'quality': info.get('format', 'Best Quality (HD + Audio)'),
                'extension': info.get('ext', 'mp4'),
                'duration': info.get('duration', 0),
                'filesize': info.get('filesize', 0)
            }
            
            logger.info(f"Success: {info.get('title')}")
            return jsonify(video_details)
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
