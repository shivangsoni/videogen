#!/usr/bin/env python3
"""
Publish All Languages Script
Generates and publishes YouTube Shorts in ALL languages, ONE AT A TIME.

This script:
1. Iterates over all folders in youtubeshorts/
2. Generates video for ONE language at a time
3. Publishes it to YouTube
4. Waits for completion
5. Moves to next language/folder

Usage:
    python publish_all.py ssoni                    # All folders, all languages
    python publish_all.py ssoni "Hindi,Kannada"   # All folders, specific languages
    python publish_all.py ssoni --folder "motivation"  # Specific folder only
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


def get_all_folders() -> list:
    """Get all valid folders in youtubeshorts directory."""
    script_dir = Path(__file__).parent
    youtubeshorts_dir = script_dir / "youtubeshorts"
    
    if not youtubeshorts_dir.exists():
        return []
    
    folders = []
    for item in youtubeshorts_dir.iterdir():
        if item.is_dir():
            # Check if it has required files
            has_script = (item / "script.txt").exists()
            has_metadata = (item / "metadata.txt").exists()
            has_youtube = (item / "youtube_publish.txt").exists()
            
            if has_script and has_metadata and has_youtube:
                folders.append(item.name)
    
    return sorted(folders)


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
    if len(sys.argv) < 2:
        print("Usage: python publish_all.py <account> [languages] [--folder <name>]")
        print()
        print("Examples:")
        print('  python publish_all.py ssoni                     # All folders, all languages')
        print('  python publish_all.py ssoni "Hindi,Kannada"    # All folders, specific languages')
        print('  python publish_all.py ssoni --folder motivation # Specific folder only')
        print()
        print("Available languages:", ", ".join(ALL_LANGUAGES))
        sys.exit(1)
    
    account = sys.argv[1]
    languages = ALL_LANGUAGES
    specific_folder = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--folder" and i + 1 < len(sys.argv):
            specific_folder = sys.argv[i + 1]
            i += 2
        elif not sys.argv[i].startswith("--"):
            languages = [lang.strip() for lang in sys.argv[i].split(",")]
            i += 1
        else:
            i += 1
    
    # Get folders to process
    if specific_folder:
        folders = [specific_folder]
    else:
        folders = get_all_folders()
    
    if not folders:
        print("No valid folders found in youtubeshorts/")
        print("Each folder needs: script.txt, metadata.txt, youtube_publish.txt")
        sys.exit(1)
    
    print("=" * 60)
    print("YOUTUBE SHORTS - PUBLISH ALL LANGUAGES")
    print("=" * 60)
    print(f"Account:   {account}")
    print(f"Folders:   {len(folders)}")
    for f in folders:
        print(f"           - {f}")
    print(f"Languages: {len(languages)}")
    print(f"Mode:      ONE AT A TIME (sequential)")
    print(f"Total:     {len(folders) * len(languages)} videos")
    print("=" * 60)
    
    all_results = {}
    start_time = datetime.now()
    total_videos = len(folders) * len(languages)
    current_video = 0
    
    for folder in folders:
        print()
        print("#" * 60)
        print(f"FOLDER: {folder}")
        print("#" * 60)
        
        all_results[folder] = []
        
        for language in languages:
            current_video += 1
            print()
            print("=" * 60)
            print(f"[{current_video}/{total_videos}] {folder} - {language.upper()}")
            print("=" * 60)
            
            lang_start = datetime.now()
            result = process_single_language(folder, language, account)
            lang_duration = datetime.now() - lang_start
            
            result["duration"] = str(lang_duration).split('.')[0]
            result["folder"] = folder
            all_results[folder].append(result)
            
            # Print status
            if result["status"] == "success":
                print(f"\n  [OK] {language}: SUCCESS ({result['duration']})")
                if result["youtube_url"]:
                    print(f"    URL: {result['youtube_url']}")
            else:
                print(f"\n  [FAIL] {language}: {result['status'].upper()}")
                if result["error"]:
                    print(f"    Error: {result['error']}")
            
            # Small delay between videos to avoid rate limiting
            if current_video < total_videos:
                print("\n  Waiting 5 seconds before next video...")
                time.sleep(5)
    
    # Final Summary
    total_duration = datetime.now() - start_time
    
    print()
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total Duration: {str(total_duration).split('.')[0]}")
    
    total_success = 0
    total_failed = 0
    
    for folder, results in all_results.items():
        success = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] != "success"]
        total_success += len(success)
        total_failed += len(failed)
        
        print(f"\n{folder}:")
        print(f"  Success: {len(success)}/{len(results)}")
        if success:
            for r in success:
                url = r.get("youtube_url", "N/A")
                print(f"    [OK] {r['language']}: {url}")
        if failed:
            for r in failed:
                print(f"    [FAIL] {r['language']}: {r.get('error', r['status'])}")    
    print()
    print(f"TOTAL: {total_success} success, {total_failed} failed")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
