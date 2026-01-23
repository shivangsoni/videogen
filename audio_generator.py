"""
Audio generator using gTTS (Google Text-to-Speech) for reliable cloud deployment
Falls back to Edge TTS if gTTS fails
"""

import asyncio
import os
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from gtts import gTTS
from moviepy.editor import AudioFileClip

from config import TEMP_DIR


@dataclass
class AudioSegment:
    """Represents an audio segment with timing info"""
    text: str
    audio_path: str
    start_time: float
    end_time: float
    duration: float


# Voice styles for gTTS (language codes)
# Supports multiple languages including Hindi, French, German, Spanish, etc.
VOICES = {
    # English variants
    "en": "en",
    "en-us": "en",
    "en-uk": "en-uk",
    "en-au": "en-au",
    "en-in": "en-in",
    # Other languages
    "hi": "hi",      # Hindi
    "fr": "fr",      # French
    "de": "de",      # German
    "es": "es",      # Spanish
    "pt": "pt",      # Portuguese
    "it": "it",      # Italian
    "ja": "ja",      # Japanese
    "ko": "ko",      # Korean
    "zh": "zh-CN",   # Chinese (Simplified)
    "ar": "ar",      # Arabic
    "ru": "ru",      # Russian
    "nl": "nl",      # Dutch
    "pl": "pl",      # Polish
    "tr": "tr",      # Turkish
}

# Supported languages with display names
SUPPORTED_LANGUAGES = {
    "English (US)": "en",
    "English (UK)": "en-uk",
    "English (Australia)": "en-au",
    "English (India)": "en-in",
    "Hindi": "hi",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Portuguese": "pt",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Simplified)": "zh-CN",
    "Arabic": "ar",
    "Russian": "ru",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
}

DEFAULT_VOICE = "en"


class AudioGenerator:
    def __init__(self, voice: str = DEFAULT_VOICE):
        """
        Initialize audio generator.
        
        Args:
            voice: Language code for gTTS
        """
        self.voice = voice
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
    
    def _generate_audio_gtts(
        self,
        text: str,
        output_path: str,
        slow: bool = False
    ) -> str:
        """Generate audio file from text using gTTS"""
        tts = gTTS(text=text, lang=self.voice, slow=slow)
        tts.save(output_path)
        return output_path
    
    def generate_audio(
        self,
        text: str,
        output_path: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> Tuple[str, float]:
        """
        Generate audio and return path and duration.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio
            rate: Speed adjustment (ignored for gTTS, kept for API compatibility)
            pitch: Pitch adjustment (ignored for gTTS, kept for API compatibility)
            
        Returns:
            Tuple of (audio_path, duration_in_seconds)
        """
        # Use gTTS (more reliable on cloud)
        slow = "-" in rate  # If rate is negative, use slow mode
        self._generate_audio_gtts(text, output_path, slow=slow)
        
        # Get duration
        audio = AudioFileClip(output_path)
        duration = audio.duration
        audio.close()
        
        return output_path, duration
    
    def generate_segment_audio(
        self,
        segments,
        rate: str = "-5%"  # Slightly slower for clarity
    ) -> Tuple[List[AudioSegment], str, float]:
        """
        Generate audio for each segment and combine them.
        
        Returns:
            Tuple of (list of AudioSegments with timing, combined audio path, total duration)
        """
        audio_segments = []
        current_time = 0.0
        
        # Generate audio for each segment
        for i, segment in enumerate(segments):
            # Clean text for TTS
            text = segment.text.strip()
            if not text:
                continue
            
            # Generate individual segment audio
            segment_path = str(self.temp_dir / f"segment_{i}.mp3")
            _, duration = self.generate_audio(text, segment_path, rate=rate)
            
            audio_segments.append(AudioSegment(
                text=text,
                audio_path=segment_path,
                start_time=current_time,
                end_time=current_time + duration,
                duration=duration
            ))
            
            current_time += duration + 0.3  # Small gap between segments
        
        # Combine all audio files
        combined_path = str(self.temp_dir / "combined_audio.mp3")
        total_duration = self._combine_audio_files(audio_segments, combined_path)
        
        return audio_segments, combined_path, total_duration
    
    def _combine_audio_files(
        self,
        audio_segments: List[AudioSegment],
        output_path: str
    ) -> float:
        """Combine multiple audio files with gaps"""
        from moviepy.editor import concatenate_audioclips, AudioFileClip
        from moviepy.audio.AudioClip import AudioClip
        
        clips = []
        
        for i, seg in enumerate(audio_segments):
            # Add the audio segment
            clip = AudioFileClip(seg.audio_path)
            clips.append(clip)
            
            # Add silence gap (except after last segment)
            if i < len(audio_segments) - 1:
                # Create 0.3 second silence
                silence = AudioClip(lambda t: 0, duration=0.3, fps=44100)
                clips.append(silence)
        
        # Concatenate all clips
        if clips:
            final_audio = concatenate_audioclips(clips)
            final_audio.write_audiofile(output_path, fps=44100, verbose=False, logger=None)
            duration = final_audio.duration
            final_audio.close()
            
            # Close individual clips
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            
            return duration
        
        return 0.0
    
    def generate_line_timings(
        self,
        display_lines: List[str],
        total_duration: float
    ) -> List[Tuple[str, float, float]]:
        """
        Generate timing for each display line based on word count.
        
        Returns:
            List of (text, start_time, end_time)
        """
        # Calculate total words
        total_words = sum(len(line.split()) for line in display_lines)
        
        if total_words == 0:
            return []
        
        # Time per word
        time_per_word = total_duration / total_words
        
        timings = []
        current_time = 0.0
        
        for line in display_lines:
            word_count = len(line.split())
            # Minimum 1.5 seconds per line, based on word count otherwise
            line_duration = max(1.5, word_count * time_per_word)
            
            timings.append((line, current_time, current_time + line_duration))
            current_time += line_duration
        
        # Adjust to fit total duration
        if timings:
            scale = total_duration / current_time
            timings = [
                (text, start * scale, end * scale)
                for text, start, end in timings
            ]
        
        return timings


def list_available_voices():
    """List all available Edge TTS voices"""
    async def get_voices():
        voices = await edge_tts.list_voices()
        return voices
    
    voices = asyncio.run(get_voices())
    
    # Filter English voices
    english_voices = [v for v in voices if v["Locale"].startswith("en-")]
    
    print("Available English voices:")
    for v in english_voices:
        print(f"  {v['ShortName']}: {v['Gender']} - {v['Locale']}")


if __name__ == "__main__":
    # Test audio generation
    generator = AudioGenerator()
    
    test_text = "Here's how to handle your life. No motivation required."
    output_path = "temp/test_audio.mp3"
    
    os.makedirs("temp", exist_ok=True)
    
    path, duration = generator.generate_audio(test_text, output_path)
    print(f"Generated audio: {path}")
    print(f"Duration: {duration:.2f}s")
    
    # List voices
    print("\n")
    list_available_voices()
