"""
Configuration settings for video generation
"""

# Video dimensions (Landscape 16:9 format for YouTube/desktop)
# Using 720p for faster encoding (can change to 1920x1080 for HD)
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720

# Video settings
FPS = 24  # Reduced from 30 for faster encoding
MIN_DURATION = 30  # seconds
MAX_DURATION = 60  # seconds

# Text styling (v2: reduced font sizes by 8px for better fit)\nFONT_SIZE_HOOK = 72   # Was 80\nFONT_SIZE_MAIN = 62   # Was 70\nFONT_SIZE_CTA = 57    # Was 65\nFONT_COLOR = "white"\nFONT_STROKE_COLOR = "black"\nFONT_STROKE_WIDTH = 3

# Background colors (gradient-like effect with solid colors)
BACKGROUND_COLORS = [
    "#1a1a2e",  # Dark blue
    "#16213e",  # Navy
    "#0f3460",  # Deep blue
    "#1a1a1a",  # Almost black
    "#2d132c",  # Dark purple
    "#190019",  # Very dark magenta
]

# Text animation settings
FADE_DURATION = 0.3
TEXT_DISPLAY_TIME = 2.5  # Base time each text segment is shown

# Audio settings
TTS_LANGUAGE = "en"
TTS_SLOW = False

# Output settings (use environment variables for cloud deployment)
import os
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
TEMP_DIR = os.environ.get("TEMP_DIR", "temp")
