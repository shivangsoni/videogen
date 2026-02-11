"""
Video Generator with stock videos/animations and full-screen captions
"""

import os
import sys
import random
import signal
import textwrap
from pathlib import Path
from typing import List, Tuple, Optional

# Fix Windows console encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Safe print function for Windows console (handles non-ASCII characters)
def safe_print(msg: str):
    """Print safely on Windows by encoding non-ASCII characters"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Replace non-ASCII characters with ? for console display
        safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
        print(safe_msg)

# Ignore SIGINT during video processing
signal.signal(signal.SIGINT, signal.SIG_IGN)

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Fix PIL.Image.ANTIALIAS deprecation for newer Pillow versions
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.audio.fx.all import audio_loop

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS,
    FADE_DURATION, OUTPUT_DIR, TEMP_DIR,
)
from script_parser import ScriptSegment, get_full_narration_text
from animated_background import AnimatedBackgroundGenerator
from stock_video_fetcher import StockVideoFetcher
from audio_generator import AudioGenerator
from translator import Translator
from anime_video_fetcher import AnimeVideoFetcher
from multi_source_fetcher import MultiSourceFetcher


class VideoGenerator:
    def __init__(self, pexels_api_key: Optional[str] = None):
        self.temp_dir = Path(TEMP_DIR)
        self.output_dir = Path(OUTPUT_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        self.stock_fetcher = StockVideoFetcher(pexels_api_key)
        self.anime_fetcher = AnimeVideoFetcher()
        self.multi_fetcher = MultiSourceFetcher()
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
        """Resize and crop video to fill full screen (9:16 portrait) - no black bars"""
        target_w = VIDEO_WIDTH   # 720
        target_h = VIDEO_HEIGHT  # 1280
        target_ratio = target_w / target_h  # 0.5625
        
        clip_w = clip.w
        clip_h = clip.h
        clip_ratio = clip_w / clip_h
        
        print(f"      Original: {clip_w}x{clip_h}, ratio: {clip_ratio:.3f}, target: {target_ratio:.3f}")
        
        # Calculate scale factor to FILL the target (not fit)
        # We want the smaller dimension to match, so we scale up
        scale_w = target_w / clip_w
        scale_h = target_h / clip_h
        scale = max(scale_w, scale_h)  # Use larger scale to ensure full coverage
        
        new_w = int(clip_w * scale)
        new_h = int(clip_h * scale)
        
        print(f"      Scaling by {scale:.3f} to: {new_w}x{new_h}")
        clip = clip.resize(newsize=(new_w, new_h))
        
        # Now crop to exact target size (centered)
        if new_w > target_w:
            x1 = (new_w - target_w) // 2
            clip = clip.crop(x1=x1, x2=x1 + target_w)
            print(f"      Cropped width to {target_w}")
        
        if new_h > target_h:
            y1 = (new_h - target_h) // 2
            clip = clip.crop(y1=y1, y2=y1 + target_h)
            print(f"      Cropped height to {target_h}")
        
        # Final safety resize to ensure exact dimensions
        if clip.w != target_w or clip.h != target_h:
            print(f"      Final resize from {clip.w}x{clip.h} to {target_w}x{target_h}")
            clip = clip.resize(newsize=(target_w, target_h))
        
        print(f"      Final size: {clip.w}x{clip.h}")
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
        )
        
        return clip
    
    def generate_video(
        self,
        segments: List[ScriptSegment],
        output_filename: str = "output_short.mp4",
        use_stock_videos: bool = True,
        stock_keywords: List[str] = None,
        target_language: str = "en",
        progress_callback=None,
        use_anime_clips: bool = False,
        use_giphy_clips: bool = False,
        use_pixabay_clips: bool = False,
        custom_gif_paths: Optional[List[str]] = None,
        custom_soundtrack_path: Optional[str] = None,
        soundtrack_volume: float = 0.2,
    ) -> str:
        """
        Generate video with stock videos/animations and full-screen captions.
        
        Args:
            segments: Parsed script segments
            output_filename: Output filename
            use_stock_videos: Whether to fetch stock videos
            stock_keywords: Optional custom keywords for stock video search
            target_language: Language code for audio (captions stay in English)
            progress_callback: Optional callback function(progress, message) for progress updates
            use_anime_clips: Whether to use anime clips from Trace Moe instead of Pexels
            use_giphy_clips: Whether to use GIPHY animated GIFs
            use_pixabay_clips: Whether to use Pixabay stock videos
            custom_gif_paths: List of custom GIF/video file paths (will be split equally across duration)
            custom_soundtrack_path: Path to custom soundtrack audio file
            soundtrack_volume: Volume for custom soundtrack (0.0 to 1.0)
            use_giphy_clips: Whether to use animated GIFs from GIPHY
            use_pixabay_clips: Whether to use free videos from Pixabay
        """
        def report_progress(pct, msg):
            """Report progress if callback is provided"""
            print(f"      [{pct:.0%}] {msg}")
            if progress_callback:
                progress_callback(pct, msg)
        
        print("=" * 50)
        print("YOUTUBE SHORTS VIDEO GENERATOR")
        print("=" * 50)
        
        # Step 1: Translate text (0% -> 10%)
        report_progress(0.02, "Translating script...")
        full_text = get_full_narration_text(segments)
        
        translator = Translator(target_language)
        translated_text = translator.translate(full_text)
        if target_language != "en" and not target_language.startswith("en"):
            report_progress(0.08, f"Translated to {target_language}")
        else:
            report_progress(0.08, "Using English audio")
        
        # Step 2: Generate audio (10% -> 25%)
        report_progress(0.10, "Generating voiceover audio...")
        # Use unique filename to prevent reusing old audio when voice changes
        import uuid
        audio_path = str(self.temp_dir / f"narration_{uuid.uuid4().hex[:8]}.mp3")
        print(f"      [VideoGenerator] Generating audio to: {audio_path}")
        print(f"      [VideoGenerator] Using voice_id: {self.audio_generator.voice_id}")
        _, audio_duration = self.audio_generator.generate_audio(
            translated_text,
            audio_path,
            rate="-5%"
        )
        report_progress(0.25, f"Audio ready ({audio_duration:.1f}s)")
        
        # Step 3: Process script segments (25% -> 30%)
        report_progress(0.27, "Processing captions...")
        all_lines = []
        for segment in segments:
            for line in segment.display_lines:
                all_lines.append((line, segment.segment_type))
        
        line_timings = self._calculate_line_timings(all_lines, audio_duration)
        report_progress(0.30, f"Prepared {len(all_lines)} caption lines")
        
        # Step 4: Get background videos/animations (30% -> 55%)
        report_progress(0.32, "Fetching background videos...")
        background_clips = []

        # Use custom GIF/video if provided (split duration equally)
        if custom_gif_paths and len(custom_gif_paths) > 0:
            try:
                valid_gifs = [path for path in custom_gif_paths if os.path.exists(path)]
                if valid_gifs:
                    num_gifs = len(valid_gifs)
                    duration_per_gif = audio_duration / num_gifs
                    
                    report_progress(0.35, f"Using {num_gifs} custom GIF/video backgrounds...")
                    
                    for i, gif_path in enumerate(valid_gifs):
                        try:
                            clip = VideoFileClip(gif_path)
                            clip = self.resize_video_to_fullscreen(clip)
                            
                            # Loop to match allocated duration
                            if clip.duration < duration_per_gif:
                                loops_needed = int(duration_per_gif / clip.duration) + 1
                                clip = clip.fx(vfx.loop, n=loops_needed)
                            
                            # Trim to exact allocated duration
                            clip = clip.subclip(0, min(clip.duration, duration_per_gif))
                            background_clips.append(clip)
                        except Exception as e:
                            print(f"      Error loading custom GIF {i+1}: {e}")
                    
                    if background_clips:
                        report_progress(0.45, f"{len(background_clips)} custom backgrounds ready")
            except Exception as e:
                print(f"      Error processing custom GIFs: {e}")
        
        # Try anime clips if requested
        if not background_clips and use_anime_clips:
            # Use stock_keywords for anime search if provided
            anime_keywords = stock_keywords[:3] if stock_keywords else None
            if anime_keywords:
                report_progress(0.35, f"Fetching anime clips for: {', '.join(anime_keywords)}...")
            else:
                report_progress(0.35, "Fetching random anime clips from Trace Moe...")
            video_paths = self.anime_fetcher.fetch_anime_clips(count=3, keywords=anime_keywords)
            
            if video_paths:
                report_progress(0.45, f"Processing {len(video_paths)} anime clips...")
                for i, vpath in enumerate(video_paths):
                    try:
                        clip = VideoFileClip(vpath)
                        clip = self.resize_video_to_fullscreen(clip)
                        clip = clip.fx(vfx.colorx, 0.6)  # Slightly less dim for anime
                        background_clips.append(clip)
                        report_progress(0.45 + (i+1)*0.03, f"Processed anime clip {i+1}/{len(video_paths)}")
                    except Exception as e:
                        print(f"      Error loading anime clip: {e}")
        
        # Try GIPHY animated GIFs
        elif not background_clips and use_giphy_clips:
            giphy_keywords = stock_keywords[:3] if stock_keywords else None
            if giphy_keywords:
                report_progress(0.35, f"Fetching GIPHY GIFs for: {', '.join(giphy_keywords)}...")
            else:
                report_progress(0.35, "Fetching animated GIFs from GIPHY...")
            
            video_paths = self.multi_fetcher.fetch_hand_drawn_gifs(
                query=giphy_keywords[0] if giphy_keywords else None,
                count=3
            )
            
            if video_paths:
                report_progress(0.45, f"Processing {len(video_paths)} GIPHY clips...")
                for i, vpath in enumerate(video_paths):
                    try:
                        clip = VideoFileClip(vpath)
                        clip = self.resize_video_to_fullscreen(clip)
                        clip = clip.fx(vfx.colorx, 0.7)  # Keep GIFs brighter
                        background_clips.append(clip)
                        report_progress(0.45 + (i+1)*0.03, f"Processed GIPHY clip {i+1}/{len(video_paths)}")
                    except Exception as e:
                        print(f"      Error loading GIPHY clip: {e}")
        
        # Try Pixabay free videos
        elif not background_clips and use_pixabay_clips:
            pixabay_keywords = stock_keywords[:3] if stock_keywords else None
            if pixabay_keywords:
                report_progress(0.35, f"Fetching Pixabay videos for: {', '.join(pixabay_keywords)}...")
            else:
                report_progress(0.35, "Fetching free videos from Pixabay...")
            
            video_paths = self.multi_fetcher.fetch_from_pixabay(
                query=pixabay_keywords[0] if pixabay_keywords else "motivation",
                media_type="video",
                count=3
            )
            
            if video_paths:
                report_progress(0.45, f"Processing {len(video_paths)} Pixabay clips...")
                for i, vpath in enumerate(video_paths):
                    try:
                        clip = VideoFileClip(vpath)
                        clip = self.resize_video_to_fullscreen(clip)
                        clip = clip.fx(vfx.colorx, 0.65)  # Slightly dim
                        background_clips.append(clip)
                        report_progress(0.45 + (i+1)*0.03, f"Processed Pixabay clip {i+1}/{len(video_paths)}")
                    except Exception as e:
                        print(f"      Error loading Pixabay clip: {e}")
        
        # Try to fetch stock videos if not using anime/sketch or they failed
        elif not background_clips and use_stock_videos and self.stock_fetcher.api_key:
            report_progress(0.35, "Searching Pexels for stock videos...")
            # Use custom keywords if provided, otherwise extract from script
            if stock_keywords:
                keywords = stock_keywords[:3]  # Limit to 3 keywords
            else:
                keywords = self.stock_fetcher.get_keywords_from_script(segments)
            
            report_progress(0.38, f"Downloading videos for: {', '.join(keywords[:2])}...")
            video_paths = self.stock_fetcher.fetch_videos(keywords=keywords, count=3)
            
            if video_paths:
                report_progress(0.45, f"Processing {len(video_paths)} stock videos...")
                for i, vpath in enumerate(video_paths):
                    try:
                        clip = VideoFileClip(vpath)
                        clip = self.resize_video_to_fullscreen(clip)
                        clip = clip.fx(vfx.colorx, 0.5)
                        background_clips.append(clip)
                        report_progress(0.45 + (i+1)*0.03, f"Processed video {i+1}/{len(video_paths)}")
                    except Exception as e:
                        print(f"      Error loading video: {e}")
        
        # Fallback to animated backgrounds if no stock videos
        if not background_clips:
            report_progress(0.50, "Generating animated background...")
            styles = ['gradient_flow', 'particles', 'aurora', 'geometric_float']
            chosen_style = random.choice(styles)
            
            animated_bg = self.bg_generator.generate_animated_background(
                duration=audio_duration,
                style=chosen_style
            )
            background_clips.append(animated_bg)
        
        report_progress(0.55, f"Background ready ({len(background_clips)} clips)")
        
        # Step 5: Build final video (55% -> 75%)
        report_progress(0.57, "Arranging video clips...")
        
        # Distribute all stock videos evenly across the duration
        if len(background_clips) == 1:
            bg = background_clips[0].set_duration(audio_duration)
        else:
            # Calculate duration for each clip
            time_per_clip = audio_duration / len(background_clips)
            
            adjusted_clips = []
            for i, clip in enumerate(background_clips):
                if clip.duration >= time_per_clip:
                    adjusted = clip.subclip(0, time_per_clip)
                else:
                    loops = int(time_per_clip / clip.duration) + 1
                    looped = concatenate_videoclips([clip] * loops)
                    adjusted = looped.subclip(0, time_per_clip)
                
                if i > 0:
                    adjusted = adjusted.crossfadein(0.5)
                
                adjusted_clips.append(adjusted)
            
            bg = concatenate_videoclips(adjusted_clips, method="compose")
            
            if bg.duration > audio_duration:
                bg = bg.subclip(0, audio_duration)
        
        bg = bg.set_position((0, 0))
        report_progress(0.62, "Video clips arranged")
        
        # Step 6: Create captions (62% -> 70%)
        report_progress(0.64, "Creating captions...")
        caption_clips = []
        total_captions = len(line_timings)
        for idx, (text, seg_type, start_time, end_time) in enumerate(line_timings):
            duration = end_time - start_time
            
            if seg_type == 'hook':
                font_size = 32
            elif seg_type == 'cta':
                font_size = 30
            else:
                font_size = 28
            
            caption_clip = self.create_caption_clip(
                text, start_time, duration, font_size
            )
            caption_clips.append(caption_clip)
            
            if (idx + 1) % 3 == 0 or idx == total_captions - 1:
                report_progress(0.64 + (idx/total_captions)*0.06, f"Caption {idx+1}/{total_captions}")
        
        report_progress(0.70, "Captions created")
        
        # Step 7: Composite layers (70% -> 75%)
        report_progress(0.72, "Compositing video layers...")
        
        # Ensure background is properly sized and positioned
        bg = bg.set_position(('center', 'center'))
        
        # Pre-composite captions in time-order groups to reduce layer count
        # Each frame only has 1 caption visible, so grouping doesn't affect visuals
        final_video = CompositeVideoClip(
            [bg] + caption_clips,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT)
        )
        
        # Add audio
        audio = AudioFileClip(audio_path)
        final_audio = audio

        # Optional custom soundtrack
        bg_audio = None
        if custom_soundtrack_path and os.path.exists(custom_soundtrack_path):
            try:
                bg_audio = AudioFileClip(custom_soundtrack_path)
                if bg_audio.duration < audio_duration:
                    bg_audio = audio_loop(bg_audio, duration=audio_duration)
                else:
                    bg_audio = bg_audio.subclip(0, audio_duration)
                # Clamp volume to [0, 1]
                volume = max(0.0, min(soundtrack_volume, 1.0))
                bg_audio = bg_audio.volumex(volume)
                final_audio = CompositeAudioClip([audio, bg_audio])
            except Exception as e:
                print(f"      Error loading custom soundtrack: {e}")

        final_video = final_video.set_audio(final_audio)
        final_video = final_video.set_duration(audio_duration)
        report_progress(0.75, "Video composed with audio")
        
        # Step 8: Export video (75% -> 98%)
        output_path = str(self.output_dir / output_filename)
        
        total_frames = int(audio_duration * FPS)
        report_progress(0.78, f"Encoding video ({total_frames} frames, ~{audio_duration:.0f}s)...")
        
        # Custom logger that tracks ffmpeg encoding progress in real-time
        from proglog import ProgressBarLogger
        
        class EncodingProgressLogger(ProgressBarLogger):
            """MoviePy-compatible logger that shows encoding progress.
            
            MoviePy does multiple passes (audio, then video). We track
            all passes and show cumulative progress that never goes backward.
            Pass layout: audio prep (78-80%), video render (80-92%).
            """
            def __init__(self, total_frames, progress_cb):
                super().__init__()
                self.total_frames = max(total_frames, 1)
                self.progress_cb = progress_cb
                self.pass_count = 0          # how many encoding passes we've seen
                self.render_pass = 0         # how many large (frame) passes we've seen
                self.current_total = 1       # total for current pass
                self.last_reported_pct = -1  # last % we printed (avoid spam)
                self.highest_overall = 0.78  # never go below this (no backward jumps)
                import time as _time
                self._time = _time
                self.render_start = None     # set when first frame pass begins
            
            def callback(self, **changes):
                pass
            
            def bars_callback(self, bar, attr, value, old_value=None):
                if attr == 'total' and isinstance(value, (int, float)) and value > 0:
                    # A new 'total' signals start of a new encoding pass
                    self.pass_count += 1
                    self.current_total = int(value)
                    self.last_reported_pct = -1
                    
                    if self.current_total > 500:
                        # Large total = a frame rendering pass
                        self.render_pass += 1
                        self.total_frames = self.current_total
                        if self.render_pass == 1:
                            # First frame pass — start render timer
                            self.render_start = self._time.time()
                            self._report(0.80, f"Encoding video frames ({self.total_frames} frames)...")
                        # For pass 2+, just keep going — no reset message
                    return
                
                if attr != 'index' or not isinstance(value, (int, float)):
                    return
                
                pct = min(value / max(self.current_total, 1), 1.0)
                report_pct = int(pct * 100)
                
                # Skip if we already reported this percentage
                if report_pct <= self.last_reported_pct:
                    return
                
                if self.render_pass > 0:
                    # FRAME PASSES: 80% -> 92% overall
                    # Report every 5%
                    if report_pct % 5 != 0 and report_pct != 100:
                        return
                    self.last_reported_pct = report_pct
                    
                    # For multiple render passes, combine progress:
                    # pass1 covers 80-86%, pass2 covers 86-92%
                    if self.render_pass == 1:
                        overall = 0.80 + pct * 0.06
                    else:
                        overall = 0.86 + pct * 0.06
                    
                    elapsed = self._time.time() - self.render_start if self.render_start else 0
                    if pct > 0.03 and elapsed > 2:
                        eta = elapsed / pct * (1.0 - pct)
                        step_label = "Writing" if self.render_pass > 1 else "Rendering"
                        self._report(overall, f"{step_label}: {report_pct}% ({int(value)}/{self.total_frames} frames, ETA {eta:.0f}s)")
                    else:
                        step_label = "Writing" if self.render_pass > 1 else "Rendering"
                        self._report(overall, f"{step_label}: {report_pct}%")
                else:
                    # FAST PASSES: audio prep (78% -> 80% overall)
                    if report_pct % 50 != 0:
                        return
                    self.last_reported_pct = report_pct
                    overall = 0.78 + pct * 0.02
                    self._report(overall, f"Preparing audio: {report_pct}%")
            
            def _report(self, overall, msg):
                """Report progress, never going backward."""
                overall = max(overall, self.highest_overall)
                self.highest_overall = overall
                self.progress_cb(overall, msg)
        
        encoding_logger = EncodingProgressLogger(total_frames, report_progress)
        
        # Write to temp location first, then move - avoids Windows file lock issues
        import time
        import gc
        import shutil
        
        temp_output = output_path.replace('.mp4', '_encoding.mp4')
        # Explicit temp audio file path to avoid Windows TEMP_MPY lock issues
        temp_audiofile = output_path.replace('.mp4', '_temp_audio.mp4')
        
        final_video.write_videofile(
            temp_output,
            fps=FPS,
            codec='libx264',
            audio_codec='aac',
            bitrate='4000k',
            audio_bitrate='128k',
            threads=os.cpu_count() or 4,
            preset='ultrafast',
            temp_audiofile=temp_audiofile,
            remove_temp=True,
            ffmpeg_params=['-movflags', '+faststart', '-tune', 'fastdecode'],
            verbose=False,
            logger=encoding_logger
        )
        
        # Clean up temp audio file (in case remove_temp failed)
        try:
            if os.path.exists(temp_audiofile):
                os.remove(temp_audiofile)
        except:
            pass
        
        report_progress(0.92, "Encoding complete!")
        
        # Cleanup - close all clips first BEFORE moving file
        report_progress(0.94, "Releasing resources...")
        try:
            final_video.close()
        except:
            pass
        try:
            audio.close()
        except:
            pass
        try:
            if bg_audio:
                bg_audio.close()
        except:
            pass
        for clip in background_clips:
            try:
                clip.close()
            except:
                pass
        
        # Force garbage collection to release file handles on Windows
        gc.collect()
        time.sleep(1.0)  # Wait for Windows to release file handles
        
        # Move temp file to final location
        report_progress(0.97, "Finalizing output...")
        for attempt in range(3):
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                shutil.move(temp_output, output_path)
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0)
                    gc.collect()
                else:
                    # If move fails, try copy instead
                    shutil.copy2(temp_output, output_path)
                    try:
                        os.remove(temp_output)
                    except:
                        pass
        
        report_progress(0.99, "Done!")
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
        """Remove temporary files with retry for locked files"""
        import shutil
        import time
        import gc
        
        # Force garbage collection to release file handles
        gc.collect()
        
        if self.temp_dir.exists():
            # Try up to 3 times with delays
            for attempt in range(3):
                try:
                    shutil.rmtree(self.temp_dir)
                    break
                except (PermissionError, OSError) as e:
                    if attempt < 2:
                        time.sleep(1)  # Wait and retry
                        gc.collect()
                    else:
                        # Last attempt - try to delete individual files
                        for f in self.temp_dir.glob("*"):
                            try:
                                f.unlink()
                            except:
                                pass  # Skip locked files
                        try:
                            self.temp_dir.rmdir()
                        except:
                            pass  # Leave dir if not empty


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
