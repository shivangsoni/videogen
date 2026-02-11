"""
Test Google Gemini Vision API with image-to-text extraction
"""

import os
import base64
import requests
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

# Load API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not set")
    exit(1)

# Create a test image with the script text
def create_test_image():
    """Create a simple test image with script text"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    text = """Hook (0-2s):
Here's how to fix your life - no motivation required.

Core:
Fix your sleep.
Fix your diet.
Fix your room.

You don't need a new mindset.
You need basic discipline.

Chaos outside
creates chaos inside.

End (CTA):
Fix the basics first.
Follow for more raw truth."""
    
    # Use default font to avoid Unicode issues
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw text on image
    y = 50
    for line in text.split('\n'):
        draw.text((50, y), line, fill='black', font=font)
        y += 30
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64}"

# Encode the image
if len(sys.argv) > 1:
    # Use provided image file
    with open(sys.argv[1], "rb") as f:
        image_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
else:
    # Create test image
    print("Creating test image with script text...")
    image_b64 = create_test_image()

# Remove data URL prefix
if "," in image_b64:
    image_b64_clean = image_b64.split(",", 1)[1]
else:
    image_b64_clean = image_b64

# Prepare Gemini request
prompt = """Create a YouTube Shorts script based on the image.
Follow this EXACT format:

SCRIPT:
Hook (0-2s):
[One powerful opening line that stops scrolling]

Core:
[4-7 short punchy lines, each on its own line]
[Use line breaks between thoughts]
[Keep each line under 10 words]

End (CTA):
[Call to action - save/follow/share]

TITLE:
[Catchy YouTube title under 60 chars, use emotion words]

DESCRIPTION:
[3-4 lines with emojis, include the hook and CTA]

KEYWORDS:
[Comma-separated keywords derived from the image]

Return ONLY the content in this format, no explanations."""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

headers = {
    "Content-Type": "application/json"
}

data = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": image_b64_clean
                }
            }
        ]
    }],
    "generationConfig": {
        "temperature": 0.8,
        "maxOutputTokens": 1000
    }
}

print("Sending request to Google Gemini Vision API...")
print(f"Image size: {len(image_b64)} bytes")

try:
    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=60
    )
    response.raise_for_status()
    
    result = response.json()
    content = result["candidates"][0]["content"]["parts"][0]["text"]
    
    print("\n" + "="*80)
    print("GOOGLE GEMINI VISION API RESPONSE:")
    print("="*80)
    print(content)
    print("="*80)
    print("\nSUCCESS! Google Gemini Vision API can read the image and extract script content.")
    
except Exception as e:
    print(f"\nERROR: {e}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
