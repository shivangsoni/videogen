"""
Quick run script for YouTube Shorts Video Generator
Just run this script to generate a video!
"""

import os
import sys
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from script_parser import parse_script
from video_generator import VideoGenerator


def main():
    print("=" * 60)
    print("  YOUTUBE SHORTS VIDEO GENERATOR")
    print("=" * 60)
    
    # Configuration
    PEXELS_API_KEY = "iHd7xRYSd17iBTtVYecT4519k88ZMCYPmLWRrM6Sg2dy22EMdkoVQk0i"
    SCRIPT_FILE = "scripts/example_script.txt"
    OUTPUT_FILE = "output/my_short.mp4"
    
    # Check for custom script file
    if len(sys.argv) > 1:
        SCRIPT_FILE = sys.argv[1]
    
    if len(sys.argv) > 2:
        OUTPUT_FILE = sys.argv[2]
    
    script_path = project_dir / SCRIPT_FILE
    
    # Check if script exists
    if not script_path.exists():
        print(f"\n❌ Script file not found: {script_path}")
        print("\nCreate a script file with this format:")
        print("-" * 40)
        print("""Hook (0–2s):
Your attention-grabbing opening line.

Core:
Main point 1.
Main point 2.
Main point 3.

End (CTA):
Your call to action.
Follow for more!""")
        print("-" * 40)
        input("\nPress Enter to exit...")
        return
    
    # Read and parse script
    print(f"\n📄 Script: {SCRIPT_FILE}")
    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()
    
    segments = parse_script(script_text)
    
    if not segments:
        print("❌ No valid content found in script")
        input("\nPress Enter to exit...")
        return
    
    print(f"   Found {len(segments)} segments:")
    for seg in segments:
        print(f"   • {seg.segment_type}: {len(seg.display_lines)} lines")
    
    # Set API key
    os.environ["PEXELS_API_KEY"] = PEXELS_API_KEY
    print(f"\n🎬 Using Pexels stock videos")
    
    # Generate video
    print(f"\n🎥 Output: {OUTPUT_FILE}")
    print("\n" + "-" * 60)
    
    generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
    
    try:
        output_path = generator.generate_video(
            segments,
            Path(OUTPUT_FILE).name,
            use_stock_videos=True
        )
        
        print("\n" + "=" * 60)
        print(f"  ✅ VIDEO CREATED SUCCESSFULLY!")
        print(f"  📁 Saved to: {output_path}")
        print("=" * 60)
        
        # Open output folder
        output_dir = project_dir / "output"
        print(f"\n📂 Opening output folder...")
        os.startfile(str(output_dir))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        generator.cleanup_temp_files()
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
