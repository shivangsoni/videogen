"""
Flask Web Application for YouTube Shorts Video Generator
"""

import os
import uuid
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, url_for
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from script_parser import parse_script
from video_generator import VideoGenerator
from stock_video_fetcher import StockVideoFetcher

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'youtube-shorts-generator-secret-key')

# Configuration - Load from environment variables
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Store job status
jobs = {}


class VideoJob:
    def __init__(self, job_id):
        self.job_id = job_id
        self.status = "pending"
        self.progress = 0
        self.message = "Waiting to start..."
        self.output_file = None
        self.error = None
        self.stock_videos = []  # Track downloaded stock video info


def generate_video_async(job_id, script_text, stock_categories):
    """Generate video in background thread"""
    job = jobs[job_id]
    
    try:
        # Parse script
        job.status = "processing"
        job.progress = 5
        job.message = "Parsing script..."
        
        segments = parse_script(script_text)
        
        if not segments:
            raise ValueError("No valid content found in script")
        
        # Initialize generator
        job.progress = 10
        job.message = "Initializing video generator..."
        
        os.environ["PEXELS_API_KEY"] = PEXELS_API_KEY
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        
        # Parse stock categories if provided
        custom_keywords = None
        if stock_categories:
            categories = [c.strip() for c in stock_categories.split(",") if c.strip()]
            if categories:
                custom_keywords = categories[:3]  # Use up to 3 categories
        
        output_filename = f"short_{job_id}.mp4"
        
        # Step 1: Generate audio
        job.progress = 15
        job.message = "Generating voiceover audio..."
        
        # Step 2: Download videos (will happen inside generate_video)
        job.progress = 25
        job.message = "Downloading stock videos..."
        
        # Fetch stock video info for UI display
        stock_fetcher = StockVideoFetcher(PEXELS_API_KEY)
        
        # Parse stock categories if provided
        custom_keywords = None
        if stock_categories:
            categories = [c.strip() for c in stock_categories.split(",") if c.strip()]
            if categories:
                custom_keywords = categories[:3]
        
        # Fetch video metadata for display (before actual generation)
        stock_video_info = stock_fetcher.fetch_video_info(
            keywords=custom_keywords,
            count=3
        )
        job.stock_videos = stock_video_info
        
        # Step 3: Generate video - this is the long operation
        job.progress = 40
        job.message = "Building video (encoding in progress)..."
        
        output_path = generator.generate_video(
            segments,
            output_filename,
            use_stock_videos=True,
            stock_keywords=custom_keywords
        )
        
        job.progress = 95
        job.message = "Cleaning up temporary files..."
        
        generator.cleanup_temp_files()
        
        job.output_file = output_filename
        job.status = "completed"
        job.progress = 100
        job.message = "Video ready for download!"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job.status = "error"
        job.error = str(e)
        job.message = f"Error: {str(e)}"


@app.route('/')
def index():
    """Main page with form"""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """Start video generation"""
    script_text = request.form.get('script', '')
    stock_categories = request.form.get('stock_categories', '')
    
    if not script_text.strip():
        return jsonify({'error': 'Script text is required'}), 400
    
    # Create job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = VideoJob(job_id)
    
    # Start background thread
    thread = threading.Thread(
        target=generate_video_async,
        args=(job_id, script_text, stock_categories)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    """Check job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'output_file': job.output_file,
        'error': job.error,
        'stock_videos': job.stock_videos
    })


@app.route('/download/<job_id>')
def download(job_id):
    """Download generated video"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job.status != 'completed' or not job.output_file:
        return jsonify({'error': 'Video not ready'}), 400
    
    file_path = OUTPUT_DIR / job.output_file
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"youtube_short_{job_id}.mp4"
    )


if __name__ == '__main__':
    print("=" * 60)
    print("  YOUTUBE SHORTS VIDEO GENERATOR - WEB APP")
    print("=" * 60)
    print("\n  Open http://localhost:5000 in your browser\n")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
