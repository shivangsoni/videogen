#!/usr/bin/env python3
"""
Single Script Multi-Variant Video Generator

Creates 1 engaging script and generates multiple video variants using:
- Different video sources: Pexels, Giphy, Pixabay, Animation
- Different voices: Male and Female
- Ensures unique stock media throughout each video (no repeats)

Usage:
    python generate_single_video_variants.py
    python generate_single_video_variants.py --topic "Your custom topic"
    python generate_single_video_variants.py --script-only  # Just generate the script
"""

import os
import sys
import argparse
import shutil
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Fix Windows console encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

def safe_print(msg: str):
    """Print safely on Windows"""
    try:
        print(msg)
    except UnicodeEncodeError:
        safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
        print(safe_msg)

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from script_parser import parse_script
from video_generator import VideoGenerator
from audio_generator import AudioGenerator

# ============================================================================
# CONFIGURATION
# ============================================================================

YOUTUBESHORTS_DIR = Path(__file__).parent / "youtubeshorts"
OUTPUT_DIR = Path(__file__).parent / "output"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# Video variants to generate
VIDEO_VARIANTS = [
    {"name": "pexels_male", "source": "pexels", "voice": "Male"},
    {"name": "pexels_female", "source": "pexels", "voice": "Female"},
    {"name": "pixabay_male", "source": "pixabay", "voice": "Male"},
    {"name": "pixabay_female", "source": "pixabay", "voice": "Female"},
    {"name": "giphy_male", "source": "giphy", "voice": "Male"},
    {"name": "giphy_female", "source": "giphy", "voice": "Female"},
    {"name": "animation_male", "source": "animation", "voice": "Male"},
    {"name": "animation_female", "source": "animation", "voice": "Female"},
]

# Voice configurations
VOICES = {
    "Male": {
        "voice_id": "en-US-ChristopherNeural",
        "voice_name": "English - Male"
    },
    "Female": {
        "voice_id": "en-US-JennyNeural", 
        "voice_name": "English - Female"
    }
}

# ============================================================================
# SCRIPT GENERATION
# ============================================================================

def generate_script_with_groq(topic: str = None) -> Dict:
    """Generate a viral script using Groq API"""
    import requests
    
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        safe_print("=" * 50)
        safe_print("GROQ API KEY NOT FOUND")
        safe_print("=" * 50)
        safe_print("\nGet a FREE API key at: https://console.groq.com")
        safe_print("\nThen add to your .env file:")
        safe_print('GROQ_API_KEY=your_key_here')
        return None
    
    # Default topic if none provided
    if not topic:
        topics = [
            "The surprising psychology trick that makes you instantly more likable - mirror their energy",
            "Why the 2-minute rule changes everything. If it takes less than 2 minutes, do it NOW",
            "The reason you're always tired: you're not lazy, you're overstimulated",
            "How one simple morning habit changed my life forever - drink water before coffee",
            "The uncomfortable truth about success that nobody wants to hear",
            "Why smart people fail: analysis paralysis is real",
            "The power of strategic quitting - knowing when to walk away is a superpower",
        ]
        topic = random.choice(topics)
    
    safe_print(f"\nGenerating script for: {topic}")
    
    prompt = f"""Create a viral YouTube Shorts script about: {topic}

IMPORTANT: Create engaging content that hooks viewers instantly and delivers real value.

Follow this EXACT format:

Hook (0-2s):
[One powerful opening line that stops scrolling - must create curiosity or shock]

Core:
[Line 1 - make a bold claim or statement]
[Line 2 - explain WHY this matters]
[Line 3 - give a specific example or fact]
[Line 4 - address a common mistake people make]
[Line 5 - provide a simple solution or insight]
[Line 6 - reinforce with a powerful truth]

End (CTA):
[Call to action - save this, follow for more, share with someone]

KEYWORDS:
[List 6-8 relevant keywords for finding stock videos, comma-separated, include visual concepts like: abstract, city, nature, dark, light, motion, people, success]

TITLE:
[Catchy YouTube title under 50 chars with emotional words like: shocking, secret, truth, why, how]

DESCRIPTION:
[3 lines with emojis, restate the hook, add hashtags]

Example of good Hook: "This one habit made me $100K richer"
Example of good Core line: "Most people waste 2 hours daily on this"

Return ONLY the content in this exact format, no explanations."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are a viral YouTube Shorts script writer. Create punchy, engaging content. Use short sentences. Be direct. Every line must deliver value."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.85,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        return parse_generated_content(content, topic)
        
    except Exception as e:
        safe_print(f"Error generating script: {e}")
        return None


def parse_generated_content(content: str, topic: str) -> Dict:
    """Parse the generated content into structured format"""
    result = {
        "script": "",
        "keywords": [],
        "title": "",
        "description": "",
        "topic": topic
    }
    
    lines = content.strip().split("\n")
    current_section = None
    script_lines = []
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if line_lower.startswith("hook"):
            current_section = "script"
            script_lines.append(line)
        elif line_lower.startswith("core"):
            script_lines.append(line)
        elif line_lower.startswith("end"):
            script_lines.append(line)
        elif line_lower.startswith("keywords:"):
            current_section = "keywords"
            kw_part = line.split(":", 1)[1].strip() if ":" in line else ""
            if kw_part:
                result["keywords"] = [k.strip() for k in kw_part.split(",") if k.strip()]
        elif line_lower.startswith("title:"):
            current_section = "title"
            result["title"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line_lower.startswith("description:"):
            current_section = "description"
            desc_part = line.split(":", 1)[1].strip() if ":" in line else ""
            if desc_part:
                result["description"] = desc_part
        elif current_section == "script":
            script_lines.append(line)
        elif current_section == "keywords" and line.strip() and not line_lower.startswith("title"):
            result["keywords"].extend([k.strip() for k in line.split(",") if k.strip()])
        elif current_section == "description" and line.strip():
            result["description"] += "\n" + line.strip()
    
    result["script"] = "\n".join(script_lines).strip()
    result["description"] = result["description"].strip()
    
    # Ensure we have keywords
    if not result["keywords"]:
        result["keywords"] = ["motivation", "success", "mindset", "growth", "inspiration"]
    
    return result


def create_folder_for_video(content: Dict, folder_name: str) -> Path:
    """Create folder structure with script files"""
    folder_path = YOUTUBESHORTS_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # script.txt
    script_path = folder_path / "script.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content["script"])
    safe_print(f"  Created: {script_path}")
    
    # metadata.txt
    metadata_path = folder_path / "metadata.txt"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(f"keywords: {', '.join(content['keywords'])}")
    safe_print(f"  Created: {metadata_path}")
    
    # youtube_publish.txt
    publish_path = folder_path / "youtube_publish.txt"
    with open(publish_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {content['title']}\n")
        f.write(f"Description:\n")
        f.write(f"    {content['description'].replace(chr(10), chr(10) + '    ')}")
    safe_print(f"  Created: {publish_path}")
    
    return folder_path


# ============================================================================
# VIDEO GENERATION
# ============================================================================

def generate_video_variant(
    script_text: str,
    keywords: List[str],
    variant: Dict,
    output_path: Path,
    used_media_tracker: set
) -> Optional[Path]:
    """Generate a single video variant"""
    
    source = variant["source"]
    voice_type = variant["voice"]
    voice_config = VOICES[voice_type]
    
    safe_print(f"\n  [{variant['name']}] Generating video...")
    safe_print(f"    Source: {source}")
    safe_print(f"    Voice: {voice_type} ({voice_config['voice_id']})")
    safe_print(f"    Keywords: {', '.join(keywords[:3])}")
    
    try:
        segments = parse_script(script_text)
        if not segments:
            safe_print(f"    [ERROR] Could not parse script")
            return None
        
        # Create video generator with unique media tracking
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        
        # Set voice
        generator.audio_generator.voice = voice_config['voice_name']
        generator.audio_generator.voice_id = voice_config['voice_id']
        
        # Determine source flags
        use_anime = False
        use_giphy = source == "giphy"
        use_pixabay = source == "pixabay"
        use_pexels = source == "pexels"
        use_animation = source == "animation"
        
        def progress_callback(pct, msg):
            safe_print(f"    [{pct:.0%}] {msg}")
        
        # Modify keywords to get variety
        varied_keywords = get_varied_keywords(keywords, used_media_tracker, source)
        
        output_filename = output_path.name
        
        if use_animation:
            # For animation, don't use any stock videos
            result_path = generator.generate_video(
                segments=segments,
                output_filename=output_filename,
                stock_keywords=varied_keywords,
                target_language=voice_config['voice_name'],
                progress_callback=progress_callback,
                use_anime_clips=False,
                use_giphy_clips=False,
                use_pixabay_clips=False,
                use_stock_videos=False  # Force animation background
            )
        else:
            result_path = generator.generate_video(
                segments=segments,
                output_filename=output_filename,
                stock_keywords=varied_keywords,
                target_language=voice_config['voice_name'],
                progress_callback=progress_callback,
                use_anime_clips=use_anime,
                use_giphy_clips=use_giphy,
                use_pixabay_clips=use_pixabay,
            )
        
        # Track used keywords to avoid repetition
        for kw in varied_keywords:
            used_media_tracker.add(f"{source}:{kw}")
        
        if result_path and Path(result_path).exists():
            shutil.move(result_path, output_path)
            safe_print(f"    [OK] Saved: {output_path.name}")
            
            try:
                generator.cleanup_temp_files()
            except Exception as e:
                pass
            
            return output_path
        
        return None
        
    except Exception as e:
        safe_print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


def get_varied_keywords(keywords: List[str], used_tracker: set, source: str) -> List[str]:
    """Get varied keywords to ensure different stock media is used"""
    
    # Supplementary keywords by category
    supplementary = {
        "motivation": ["determination", "achievement", "hustle", "grind", "focus"],
        "success": ["winning", "victory", "champion", "goal", "milestone"],
        "mindset": ["thinking", "brain", "psychology", "mental", "attitude"],
        "growth": ["progress", "development", "evolution", "improve", "advance"],
        "inspiration": ["dream", "vision", "aspiration", "hope", "believe"],
        "default": [
            "abstract dark", "neon lights", "city night", "sunrise", "ocean waves",
            "mountains", "forest", "rain", "fire", "smoke", "particles", "stars",
            "urban", "modern", "minimal", "dramatic", "cinematic"
        ]
    }
    
    varied = []
    
    # First, try original keywords that haven't been used with this source
    for kw in keywords:
        key = f"{source}:{kw}"
        if key not in used_tracker and len(varied) < 5:
            varied.append(kw)
    
    # Then add supplementary keywords
    for kw in keywords:
        kw_lower = kw.lower()
        for category, supplements in supplementary.items():
            if category in kw_lower or kw_lower in category:
                for sup in supplements:
                    key = f"{source}:{sup}"
                    if key not in used_tracker and len(varied) < 5:
                        varied.append(sup)
                        break
    
    # Fill remaining with default keywords
    if len(varied) < 3:
        random.shuffle(supplementary["default"])
        for kw in supplementary["default"]:
            key = f"{source}:{kw}"
            if key not in used_tracker and len(varied) < 5:
                varied.append(kw)
    
    return varied[:5] if varied else keywords[:5]


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate single script with multiple video variants"
    )
    parser.add_argument(
        "--topic", "-t",
        help="Custom topic for the video (random if not provided)"
    )
    parser.add_argument(
        "--script-only", "-s",
        action="store_true",
        help="Only generate the script, don't create videos"
    )
    parser.add_argument(
        "--variants", "-v",
        help="Comma-separated list of variants to generate (e.g., 'pexels_male,pixabay_female')",
        default=None
    )
    parser.add_argument(
        "--folder", "-f",
        help="Folder name for the generated content",
        default=None
    )
    
    args = parser.parse_args()
    
    safe_print("\n" + "=" * 60)
    safe_print("SINGLE SCRIPT MULTI-VARIANT VIDEO GENERATOR")
    safe_print("=" * 60)
    
    # Generate or use existing script
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    folder_name = args.folder or f"video_{timestamp}"
    
    safe_print(f"\n[1/3] GENERATING SCRIPT")
    safe_print("-" * 40)
    
    content = generate_script_with_groq(args.topic)
    
    if not content:
        safe_print("[ERROR] Failed to generate script")
        return
    
    safe_print(f"\nTitle: {content['title']}")
    safe_print(f"Keywords: {', '.join(content['keywords'])}")
    safe_print(f"\nScript:")
    safe_print("-" * 30)
    safe_print(content['script'])
    safe_print("-" * 30)
    
    # Create folder structure
    safe_print(f"\n[2/3] CREATING FOLDER STRUCTURE")
    safe_print("-" * 40)
    
    folder_path = create_folder_for_video(content, folder_name)
    
    if args.script_only:
        safe_print(f"\n[OK] Script created in: {folder_path}")
        safe_print("\nTo generate videos, run:")
        safe_print(f"  python generate_single_video_variants.py --folder {folder_name}")
        return
    
    # Generate video variants
    safe_print(f"\n[3/3] GENERATING VIDEO VARIANTS")
    safe_print("-" * 40)
    
    # Filter variants if specified
    variants_to_generate = VIDEO_VARIANTS
    if args.variants:
        variant_names = [v.strip() for v in args.variants.split(",")]
        variants_to_generate = [v for v in VIDEO_VARIANTS if v["name"] in variant_names]
        if not variants_to_generate:
            safe_print(f"[ERROR] No valid variants found. Available: {[v['name'] for v in VIDEO_VARIANTS]}")
            return
    
    safe_print(f"Generating {len(variants_to_generate)} variants...")
    
    # Track used media to ensure variety
    used_media_tracker = set()
    results = []
    
    for i, variant in enumerate(variants_to_generate, 1):
        safe_print(f"\n[{i}/{len(variants_to_generate)}] {variant['name']}")
        safe_print("=" * 40)
        
        output_path = folder_path / f"{folder_name}_{variant['name']}.mp4"
        
        # Skip if already exists
        if output_path.exists():
            safe_print(f"  [SKIP] Already exists: {output_path.name}")
            results.append({"variant": variant["name"], "status": "exists", "path": str(output_path)})
            continue
        
        video_path = generate_video_variant(
            script_text=content["script"],
            keywords=content["keywords"],
            variant=variant,
            output_path=output_path,
            used_media_tracker=used_media_tracker
        )
        
        if video_path:
            results.append({"variant": variant["name"], "status": "generated", "path": str(video_path)})
        else:
            results.append({"variant": variant["name"], "status": "failed", "path": None})
    
    # Summary
    safe_print(f"\n{'=' * 60}")
    safe_print("SUMMARY")
    safe_print(f"{'=' * 60}")
    safe_print(f"\nFolder: {folder_path}")
    safe_print(f"\nVariants generated:")
    
    success_count = 0
    for r in results:
        icon = "[OK]" if r["status"] in ("generated", "exists") else "[FAIL]"
        if r["status"] in ("generated", "exists"):
            success_count += 1
        safe_print(f"  {icon} {r['variant']}: {r['status']}")
    
    safe_print(f"\nTotal: {success_count}/{len(results)} successful")
    
    if success_count > 0:
        safe_print(f"\nVideos saved in: {folder_path}")
        safe_print("\nReview the videos and choose the best one to publish!")
        safe_print("\nTo publish, use:")
        safe_print(f"  python batch_video_generator.py --folder {folder_name} --publish --account YOUR_ACCOUNT")


if __name__ == "__main__":
    main()
