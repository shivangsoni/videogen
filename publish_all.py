#!/usr/bin/env python3
"""
Publish All Languages Script
Generates and publishes YouTube Shorts in ALL languages, ONE AT A TIME.

This script:
1. Generates video for ONE language
2. Publishes it to YouTube
3. Waits for completion
4. Moves to next language

Usage:
    python publish_all.py "Early Dating Truth" ssoni
    python publish_all.py "Early Dating Truth" shison
    python publish_all.py "Early Dating Truth" ssoni "Hindi,Kannada,Spanish"
"""

import subprocess
import sys
import os
import time
import signal
from datetime import datetime
from pathlib import Path

# Ignore SIGINT during processing
signal.signal(signal.SIGINT, signal.SIG_IGN)

# All supported languages
ALL_LANGUAGES = [
    "English",
    "Hindi", 
    "Kannada",
    "Spanish",
    "French",
    "German",
    "Portuguese",
    "Italian",
    "Japanese",
    "Korean",
    "Chinese",
    "Arabic",
    "Russian",
    "Dutch",
    "Turkish",
    "Polish",
    "Vietnamese",
    "Thai",
    "Indonesian"
]


def get_video_path(folder: str, language: str) -> Path:
    """Get the expected video path for a language."""
    lang_codes = {
        "English": "en", "Hindi": "hi", "Kannada": "kn", "Spanish": "es",
        "French": "fr", "German": "de", "Portuguese": "pt", "Italian": "it",
        "Japanese": "ja", "Korean": "ko", "Chinese": "zh", "Arabic": "ar",
        "Russian": "ru", "Dutch": "nl", "Turkish": "tr", "Polish": "pl",
        "Vietnamese": "vi", "Thai": "th", "Indonesian": "id"
    }
    code = lang_codes.get(language, language.lower()[:2])
    script_dir = Path(__file__).parent
    return script_dir / "youtubeshorts" / folder / f"{folder}_{code}.mp4"


def process_single_language(folder: str, language: str, account: str) -> dict:
    """
    Process a single language - generate video and publish to YouTube.
    Returns dict with status and details.
    """
    result = {
        "language": language,
        "status": "unknown",
        "video_path": None,
        "youtube_url": None,
        "error": None
    }
    
    video_path = get_video_path(folder, language)
    result["video_path"] = str(video_path)
    
    cmd = [
        sys.executable,
        "batch_video_generator.py",
        "--folder", folder,
        "--languages", language,
        "--publish",
        "--account", account
    ]
    
    print(f"\n  Running: {' '.join(cmd[1:])}")
    
    try:
        # Run subprocess and capture output
        process = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output in real-time
        youtube_url = None
        for line in process.stdout:
            print(f"  {line.rstrip()}")
            # Capture YouTube URL from output
            if "youtube.com/shorts/" in line:
                import re
                match = re.search(r'https://youtube\.com/shorts/[\w-]+', line)
                if match:
                    youtube_url = match.group(0)
        
        process.wait(timeout=900)  # 15 minutes max
        
        if process.returncode == 0:
            result["status"] = "success"
            result["youtube_url"] = youtube_url
        else:
            result["status"] = "failed"
            result["error"] = f"Exit code {process.returncode}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        result["status"] = "timeout"
        result["error"] = "Exceeded 15 minutes"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: python publish_all.py <folder_name> <account> [languages]")
        print()
        print("Examples:")
        print('  python publish_all.py "Early Dating Truth" ssoni')
        print('  python publish_all.py "Early Dating Truth" ssoni "Hindi,Kannada"')
        print()
        print("Available languages:", ", ".join(ALL_LANGUAGES))
        sys.exit(1)
    
    folder = sys.argv[1]
    account = sys.argv[2]
    
    # Optional: specify languages as third argument (comma-separated)
    if len(sys.argv) > 3:
        languages = [lang.strip() for lang in sys.argv[3].split(",")]
    else:
        languages = ALL_LANGUAGES
    
    print("=" * 60)
    print("YOUTUBE SHORTS - PUBLISH ALL LANGUAGES")
    print("=" * 60)
    print(f"Folder:    {folder}")
    print(f"Account:   {account}")
    print(f"Languages: {len(languages)}")
    print(f"Mode:      ONE AT A TIME (sequential)")
    print("=" * 60)
    
    results = []
    start_time = datetime.now()
    
    for i, language in enumerate(languages, 1):
        print()
        print("=" * 60)
        print(f"[{i}/{len(languages)}] {language.upper()}")
        print("=" * 60)
        
        lang_start = datetime.now()
        result = process_single_language(folder, language, account)
        lang_duration = datetime.now() - lang_start
        
        result["duration"] = str(lang_duration).split('.')[0]
        results.append(result)
        
        # Print status
        if result["status"] == "success":
            print(f"\n  ✓ {language}: SUCCESS ({result['duration']})")
            if result["youtube_url"]:
                print(f"    URL: {result['youtube_url']}")
        else:
            print(f"\n  ✗ {language}: {result['status'].upper()}")
            if result["error"]:
                print(f"    Error: {result['error']}")
        
        # Small delay between languages to avoid rate limiting
        if i < len(languages):
            print("\n  Waiting 5 seconds before next language...")
            time.sleep(5)
    
    # Final Summary
    total_duration = datetime.now() - start_time
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]
    
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total Duration: {str(total_duration).split('.')[0]}")
    print(f"Success: {len(success)}/{len(results)}")
    print(f"Failed:  {len(failed)}/{len(results)}")
    print()
    
    if success:
        print("✓ Successfully Published:")
        for r in success:
            url = r.get("youtube_url", "N/A")
            print(f"    {r['language']}: {url}")
    
    if failed:
        print()
        print("✗ Failed:")
        for r in failed:
            print(f"    {r['language']}: {r.get('error', r['status'])}")
    
    print()
    print("Done!")


if __name__ == "__main__":
    main()
