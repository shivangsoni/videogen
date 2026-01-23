"""
Video Generator with stock videos/animations and full-screen captions
"""

import os
import random
import textwrap
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Fix PIL.Image.ANTIALIAS deprecation for newer Pillow versions
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS,
    FADE_DURATION, OUTPUT_DIR, TEMP_DIR,
)
from script_parser import ScriptSegment, get_full_narration_text
from animated_background import AnimatedBackgroundGenerator
from stock_video_fetcher import StockVideoFetcher
from audio_generator import AudioGenerator


class VideoGenerator:
    def __init__(self, pexels_api_key: Optional[str] = None):
        self.temp_dir = Path(TEMP_DIR)
        self.output_dir = Path(OUTPUT_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        self.stock_fetcher = StockVideoFetcher(pexels_api_key)
        self.bg_generator = AnimatedBackgroundGenerator()
        self.audio_generator = AudioGenerator()
        self.font_path = self._get_font_path()
    
    def _get_font_path(self) -> str:
        """Get a suitable bold font path"""
        font_candidates = [
            # Linux fonts (HF Spaces)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            # Windows fonts
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        for font in font_candidates:
            if os.path.exists(font):
                return font
        return None
    
    def resize_video_to_fullscreen(self, clip: VideoFileClip) -> VideoFileClip:
        """Resize and crop video to fill full screen (9:16 portrait)"""
        target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT  # 9:16
        clip_ratio = clip.w / clip.h
        
        if clip_ratio > target_ratio:
            # Video is wider - crop sides
            new_width = int(clip.h * target_ratio)
            x_center = clip.w // 2
            clip = clip.crop(
                x1=x_center - new_width // 2,
                x2=x_center + new_width // 2
            )
        else:
            # Video is taller - crop top/bottom
            new_height = int(clip.w / target_ratio)
            y_center = clip.h // 2
            clip = clip.crop(
                y1=y_center - new_height // 2,
                y2=y_center + new_height // 2
            )
        
        # Resize to exact dimensions
        clip = clip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        
        return clip
    
    def create_subtitle_caption(
        self,
        text: str,
        font_size: int = 24,  # Reduced by 8px for v2
    ) -> np.ndarray:
        """
        Create subtitle-style caption at the bottom of screen (smaller font).
        Text is wrapped to ensure it stays within the video frame.
        """
        img = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font = ImageFont.truetype(self.font_path, font_size) if self.font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Convert to uppercase for impact
        text = text.upper()
        
        # Calculate max width for text (90% of video width with padding)
        max_text_width = int(VIDEO_WIDTH * 0.85)
        
        # Wrap text to fit within frame - calculate based on actual font metrics
        # More conservative wrapping to prevent text from being cut off
        avg_char_width = font_size * 0.55  # Approximate character width
        max_chars = max(15, int(max_text_width / avg_char_width))
        wrapped_lines = textwrap.wrap(text, width=max_chars)
        
        if not wrapped_lines:
            return np.array(img)
        
        # Calculate text dimensions
        line_height = font_size * 1.3
        total_height = len(wrapped_lines) * line_height
        
        # Padding and positioning - ensure text stays within frame
        padding = 25
        box_height = total_height + padding * 2
        
        # Position at bottom with safe margin (ensure box stays within frame)
        bottom_margin = 80  # Safe distance from bottom edge
        start_y = VIDEO_HEIGHT - box_height - bottom_margin
        
        # Ensure start_y doesn't go above a minimum threshold
        min_start_y = int(VIDEO_HEIGHT * 0.5)  # Don't go above middle of screen
        start_y = max(start_y, min_start_y)
        
        # Draw semi-transparent background box
        max_line_width = 0
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            max_line_width = max(max_line_width, bbox[2] - bbox[0])
        
        # Ensure box width doesn't exceed frame width
        box_width = min(max_line_width + padding * 2, VIDEO_WIDTH - 40)
        box_x = (VIDEO_WIDTH - box_width) // 2
        
        # Ensure box_x is within frame bounds
        box_x = max(20, box_x)
        
        # Draw rounded background
        self._draw_rounded_rect(
            draw,
            (box_x, start_y, box_x + box_width, start_y + box_height),
            radius=15,
            fill=(0, 0, 0, 180)
        )
        
        y = start_y + padding
        
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (VIDEO_WIDTH - text_width) / 2
            
            # Draw outline for readability
            outline_color = (0, 0, 0, 255)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, font=font, fill=outline_color)
            
            # Draw main text in white
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
            
            y += line_height
        
        return np.array(img)
    
    def _draw_rounded_rect(self, draw, coords, radius, fill):
        """Draw a rounded rectangle"""
        x1, y1, x2, y2 = coords
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    def create_caption_clip(
        self,
        text: str,
        start_time: float,
        duration: float,
        font_size: int = 32,
    ) -> ImageClip:
        """Create a subtitle caption clip with fade animation"""
        caption_img = self.create_subtitle_caption(text, font_size)
        
        clip = (
            ImageClip(caption_img)
            .set_duration(duration)
            .set_start(start_time)
            .crossfadein(min(0.2, duration * 0.15))
            .crossfadeout(min(0.2, duration * 0.15))
        )
        
        return clip
    
    def generate_video(
        self,
        segments: List[ScriptSegment],
        output_filename: str = "output_short.mp4",
        use_stock_videos: bool = True,
        stock_keywords: List[str] = None,
    ) -> str:
        """
        Generate video with stock videos/animations and full-screen captions.
        
        Args:
            segments: Parsed script segments
            output_filename: Output filename
            use_stock_videos: Whether to fetch stock videos
            stock_keywords: Optional custom keywords for stock video search
        """
        print("=" * 50)
        print("YOUTUBE SHORTS VIDEO GENERATOR")
        print("=" * 50)
        
        # Step 1: Generate audio
        print("\n[1/4] Generating voiceover audio...")
        full_text = get_full_narration_text(segments)
        audio_path = str(self.temp_dir / "narration.mp3")
        _, audio_duration = self.audio_generator.generate_audio(
            full_text, 
            audio_path,
            rate="-5%"
        )
        print(f"      Audio duration: {audio_duration:.2f}s")
        
        # Step 2: Process script
        print("\n[2/4] Processing script segments...")
        all_lines = []
        for segment in segments:
            for line in segment.display_lines:
                all_lines.append((line, segment.segment_type))
        
        print(f"      Total caption lines: {len(all_lines)}")
        line_timings = self._calculate_line_timings(all_lines, audio_duration)
        
        # Step 3: Get background videos/animations
        print("\n[3/4] Getting background videos...")
        background_clips = []
        
        # Try to fetch stock videos first
        if use_stock_videos and self.stock_fetcher.api_key:
            print("      Fetching stock videos from Pexels...")
            # Use custom keywords if provided, otherwise extract from script
            if stock_keywords:
                keywords = stock_keywords[:3]  # Limit to 3 keywords
                print(f"      Using custom categories: {keywords}")
            else:
                keywords = self.stock_fetcher.get_keywords_from_script(segments)
            video_paths = self.stock_fetcher.fetch_videos(keywords=keywords, count=3)
            
            if video_paths:
                print(f"      Downloaded {len(video_paths)} stock videos")
                for vpath in video_paths:
                    try:
                        clip = VideoFileClip(vpath)
                        clip = self.resize_video_to_fullscreen(clip)
                        # Darken video for better text readability
                        clip = clip.fx(vfx.colorx, 0.5)
                        background_clips.append(clip)
                    except Exception as e:
                        print(f"      Error loading video: {e}")
        
        # Fallback to animated backgrounds if no stock videos
        if not background_clips:
            print("      Using animated backgrounds...")
            styles = ['gradient_flow', 'particles', 'aurora', 'geometric_float']
            chosen_style = random.choice(styles)
            print(f"      Animation style: {chosen_style}")
            
            animated_bg = self.bg_generator.generate_animated_background(
                duration=audio_duration,
                style=chosen_style
            )
            background_clips.append(animated_bg)
        
        # Step 4: Build final video
        print("\n[4/4] Building video...")
        print(f"      Using {len(background_clips)} background clips")
        
        # Distribute all stock videos evenly across the duration
        if len(background_clips) == 1:
            bg = background_clips[0].set_duration(audio_duration)
        else:
            # Calculate duration for each clip
            time_per_clip = audio_duration / len(background_clips)
            print(f"      Each clip duration: {time_per_clip:.2f}s")
            
            adjusted_clips = []
            for i, clip in enumerate(background_clips):
                # Set each clip to play for equal duration
                if clip.duration >= time_per_clip:
                    # Trim if longer
                    adjusted = clip.subclip(0, time_per_clip)
                else:
                    # Loop if shorter
                    loops = int(time_per_clip / clip.duration) + 1
                    looped = concatenate_videoclips([clip] * loops)
                    adjusted = looped.subclip(0, time_per_clip)
                
                # Add crossfade transition
                if i > 0:
                    adjusted = adjusted.crossfadein(0.5)
                
                adjusted_clips.append(adjusted)
            
            # Concatenate all clips
            bg = concatenate_videoclips(adjusted_clips, method="compose")
            
            # Trim to exact duration
            if bg.duration > audio_duration:
                bg = bg.subclip(0, audio_duration)
        
        bg = bg.set_position((0, 0))
        
        # Create caption clips - SUBTITLE STYLE AT BOTTOM (v2: reduced font sizes by 8px)
        caption_clips = []
        for text, seg_type, start_time, end_time in line_timings:
            duration = end_time - start_time
            
            # Font sizes - reduced by 8px for v2, ensures text fits within frame
            if seg_type == 'hook':
                font_size = 44  # Slightly bigger for hook (was 52)
            elif seg_type == 'cta':
                font_size = 42  # CTA size (was 50)
            else:
                font_size = 40  # Main content size (was 48)
            
            caption_clip = self.create_caption_clip(
                text, start_time, duration, font_size
            )
            caption_clips.append(caption_clip)
        
        # Composite all layers
        print("      Compositing layers...")
        final_video = CompositeVideoClip(
            [bg] + caption_clips,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT)
        )
        
        # Add audio
        audio = AudioFileClip(audio_path)
        final_video = final_video.set_audio(audio)
        final_video = final_video.set_duration(audio_duration)
        
        # Export
        output_path = str(self.output_dir / output_filename)
        print(f"      Exporting to: {output_path}")
        
        final_video.write_videofile(
            output_path,
            fps=FPS,
            codec='libx264',
            audio_codec='aac',
            bitrate='4000k',  # Reduced for faster encoding
            audio_bitrate='128k',
            threads=4,
            preset='ultrafast',  # Much faster encoding
            verbose=False,
            logger=None
        )
        
        # Cleanup
        final_video.close()
        audio.close()
        for clip in background_clips:
            try:
                clip.close()
            except:
                pass
        
        print("\n" + "=" * 50)
        print("SUCCESS! Video generated!")
        print(f"   Output: {output_path}")
        print(f"   Duration: {audio_duration:.2f}s")
        print("=" * 50)
        
        return output_path
    
    def _calculate_line_timings(
        self,
        lines: List[Tuple[str, str]],
        total_duration: float
    ) -> List[Tuple[str, str, float, float]]:
        """Calculate timing for each caption line"""
        total_words = sum(len(line[0].split()) for line in lines)
        
        if total_words == 0:
            return []
        
        timings = []
        current_time = 0.0
        
        for text, seg_type in lines:
            word_count = max(len(text.split()), 1)
            line_duration = max(1.5, (word_count / total_words) * total_duration)
            
            if current_time + line_duration > total_duration:
                line_duration = total_duration - current_time
            
            if line_duration > 0:
                timings.append((text, seg_type, current_time, current_time + line_duration))
            
            current_time += line_duration
        
        # Scale to fit
        if timings and current_time != total_duration:
            scale = total_duration / current_time
            timings = [
                (text, st, start * scale, end * scale)
                for text, st, start, end in timings
            ]
        
        return timings
    
    def cleanup_temp_files(self):
        """Remove temporary files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


if __name__ == "__main__":
    from script_parser import parse_script
    
    test_script = """Hook (0–2s):
Here's how to handle your life—no motivation required.

Core:
Fix your sleep.
Fix your diet.
Fix your room.

You don't need a new mindset.
You need basic discipline.

Chaos outside creates chaos inside.

End (CTA):
Follow for more raw truth."""

    segments = parse_script(test_script)
    generator = VideoGenerator()
    generator.generate_video(segments, "fullscreen_short.mp4")
