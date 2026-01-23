"""
Main entry point for YouTube Shorts video generation

Usage:
    python main.py <script_file> [output_name]
    
Example:
    python main.py scripts/example_script.txt my_video.mp4
    
For stock videos from Pexels (free):
    set PEXELS_API_KEY=your_api_key
    python main.py scripts/example_script.txt -o my_video.mp4
    
Get free API key at: https://www.pexels.com/api/
"""

import argparse
import os
import sys
from pathlib import Path

from script_parser import parse_script
from video_generator import VideoGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate faceless YouTube Shorts from a script file"
    )
    parser.add_argument(
        "script_file",
        type=str,
        help="Path to the script file"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output_short.mp4",
        help="Output video filename (default: output_short.mp4)"
    )
    parser.add_argument(
        "--pexels-key",
        type=str,
        default=None,
        help="Pexels API key for stock videos (or set PEXELS_API_KEY env var)"
    )
    parser.add_argument(
        "--no-stock",
        action="store_true",
        help="Don't use stock videos, use animated backgrounds only"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't delete temporary files after generation"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    script_path = Path(args.script_file)
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}")
        sys.exit(1)
    
    # Read script
    print(f"Reading script from: {script_path}")
    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()
    
    # Parse script
    print("Parsing script...")
    segments = parse_script(script_text)
    
    if not segments:
        print("Error: No valid content found in script")
        sys.exit(1)
    
    print(f"Found {len(segments)} segments:")
    for seg in segments:
        print(f"  - {seg.segment_type}: {len(seg.display_lines)} lines")
    
    # Get Pexels API key
    pexels_key = args.pexels_key or os.environ.get("PEXELS_API_KEY")
    
    if pexels_key:
        print("\n✓ Pexels API key found - will use stock videos")
    else:
        print("\n⚠ No Pexels API key - using animated backgrounds")
        print("  Get free API key at: https://www.pexels.com/api/")
    
    # Generate video
    print("\nStarting video generation...")
    generator = VideoGenerator(pexels_api_key=pexels_key)
    
    try:
        output_path = generator.generate_video(
            segments, 
            args.output,
            use_stock_videos=not args.no_stock
        )
        print(f"\n✅ Success! Video saved to: {output_path}")
    except Exception as e:
        print(f"\n❌ Error generating video: {e}")
        raise
    finally:
        if not args.no_cleanup:
            generator.cleanup_temp_files()


if __name__ == "__main__":
    main()
