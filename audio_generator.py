"""
Audio generator with multiple voice options (Male/Female)
Uses Edge TTS (Microsoft) for high-quality voices with gTTS fallback
"""

import asyncio
import os
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Apply nest_asyncio at module load to fix asyncio in HF Spaces/Gradio
try:
    import nest_asyncio
    nest_asyncio.apply()
    print("[AudioGenerator] nest_asyncio applied successfully")
except ImportError:
    print("[AudioGenerator] nest_asyncio not available")

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


# Edge TTS voices - high quality, multiple male/female options per language
EDGE_TTS_VOICES = {
    # English voices
    "English - Male": "en-US-ChristopherNeural",
    "English - Female": "en-US-JennyNeural",
    # Hindi voices
    "Hindi - Male": "hi-IN-MadhurNeural",
    "Hindi - Female": "hi-IN-SwaraNeural",
    # Spanish voices
    "Spanish - Male": "es-ES-AlvaroNeural",
    "Spanish - Female": "es-ES-ElviraNeural",
    # French voices
    "French - Male": "fr-FR-HenriNeural",
    "French - Female": "fr-FR-DeniseNeural",
    # German voices
    "German - Male": "de-DE-ConradNeural",
    "German - Female": "de-DE-KatjaNeural",
    # Portuguese voices
    "Portuguese - Male": "pt-BR-AntonioNeural",
    "Portuguese - Female": "pt-BR-FranciscaNeural",
    # Italian voices
    "Italian - Male": "it-IT-DiegoNeural",
    "Italian - Female": "it-IT-ElsaNeural",
    # Japanese voices
    "Japanese - Male": "ja-JP-KeitaNeural",
    "Japanese - Female": "ja-JP-NanamiNeural",
    # Korean voices
    "Korean - Male": "ko-KR-InJoonNeural",
    "Korean - Female": "ko-KR-SunHiNeural",
    # Chinese voices
    "Chinese - Male": "zh-CN-YunyangNeural",
    "Chinese - Female": "zh-CN-XiaoxiaoNeural",
    # Arabic voices
    "Arabic - Male": "ar-SA-HamedNeural",
    "Arabic - Female": "ar-SA-ZariyahNeural",
    # Russian voices
    "Russian - Male": "ru-RU-DmitryNeural",
    "Russian - Female": "ru-RU-SvetlanaNeural",
    # Dutch voices
    "Dutch - Male": "nl-NL-MaartenNeural",
    "Dutch - Female": "nl-NL-ColetteNeural",
    # Turkish voices
    "Turkish - Male": "tr-TR-AhmetNeural",
    "Turkish - Female": "tr-TR-EmelNeural",
    # Polish voices
    "Polish - Male": "pl-PL-MarekNeural",
    "Polish - Female": "pl-PL-ZofiaNeural",
    # Swedish voices
    "Swedish - Male": "sv-SE-MattiasNeural",
    "Swedish - Female": "sv-SE-SofieNeural",
    # Norwegian voices
    "Norwegian - Male": "nb-NO-FinnNeural",
    "Norwegian - Female": "nb-NO-PernilleNeural",
    # Danish voices
    "Danish - Male": "da-DK-JeppeNeural",
    "Danish - Female": "da-DK-ChristelNeural",
    # Kannada voices
    "Kannada - Male": "kn-IN-GaganNeural",
    "Kannada - Female": "kn-IN-SapnaNeural",
    # Tamil voices
    "Tamil - Male": "ta-IN-ValluvarNeural",
    "Tamil - Female": "ta-IN-PallaviNeural",
    # Telugu voices
    "Telugu - Male": "te-IN-MohanNeural",
    "Telugu - Female": "te-IN-ShrutiNeural",
    # Marathi voices
    "Marathi - Male": "mr-IN-ManoharNeural",
    "Marathi - Female": "mr-IN-AarohiNeural",
    # Bengali voices
    "Bengali - Male": "bn-IN-BashkarNeural",
    "Bengali - Female": "bn-IN-TanishaaNeural",
    # Gujarati voices
    "Gujarati - Male": "gu-IN-NiranjanNeural",
    "Gujarati - Female": "gu-IN-DhwaniNeural",
}

# gTTS fallback - language codes only (no voice variety)
GTTS_LANGUAGES = {
    "English - Male (US, Guy)": "en",
    "English - Male (US, Deep)": "en",
    "English - Male (UK)": "en-uk",
    "English - Female (US, Jenny)": "en",
    "English - Female (US, Aria)": "en",
    "English - Female (UK)": "en-uk",
    "English - Female (Australia)": "en-au",
    "English - Male (India)": "en-in",
    "English - Female (India)": "en-in",
    "Hindi - Male": "hi",
    "Hindi - Female": "hi",
    "Spanish - Male": "es",
    "Spanish - Female": "es",
    "French - Male": "fr",
    "French - Female": "fr",
    "German - Male": "de",
    "German - Female": "de",
    "Portuguese - Male": "pt",
    "Portuguese - Female": "pt",
    "Italian - Male": "it",
    "Italian - Female": "it",
    "Japanese - Male": "ja",
    "Japanese - Female": "ja",
    "Korean - Male": "ko",
    "Korean - Female": "ko",
    "Chinese - Male": "zh-CN",
    "Chinese - Female": "zh-CN",
    "Arabic - Male": "ar",
    "Arabic - Female": "ar",
    "Russian - Male": "ru",
    "Russian - Female": "ru",
    "Dutch - Male": "nl",
    "Dutch - Female": "nl",
    "Turkish - Male": "tr",
    "Turkish - Female": "tr",
    "Kannada - Male": "kn",
    "Kannada - Female": "kn",
    "Tamil - Male": "ta",
    "Tamil - Female": "ta",
    "Telugu - Male": "te",
    "Telugu - Female": "te",
    "Bengali - Male": "bn",
    "Bengali - Female": "bn",
    "Marathi - Male": "mr",
    "Marathi - Female": "mr",
    "Gujarati - Male": "gu",
    "Gujarati - Female": "gu",
    "Indonesian - Male": "id",
    "Indonesian - Female": "id",
}

# Export for UI - list of voice display names
SUPPORTED_VOICES = list(EDGE_TTS_VOICES.keys())

# For backward compatibility
SUPPORTED_LANGUAGES = {v: GTTS_LANGUAGES.get(v, "en") for v in SUPPORTED_VOICES}

DEFAULT_VOICE = "English - Male (US, Deep)"


class AudioGenerator:
    def __init__(self, voice: str = DEFAULT_VOICE):
        """
        Initialize audio generator.
        
        Args:
            voice: Voice display name from SUPPORTED_VOICES
        """
        self.voice = voice
        self.voice_id = None  # Can be set directly for specific voice
        self.temp_dir = Path(TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        self._edge_tts_available = None
    
    def _check_edge_tts(self) -> bool:
        """Check if edge-tts is available and working"""
        if self._edge_tts_available is None:
            try:
                import edge_tts
                self._edge_tts_available = True
            except ImportError:
                self._edge_tts_available = False
        return self._edge_tts_available
    
    async def _generate_audio_edge_tts(
        self,
        text: str,
        output_path: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> str:
        """Generate audio using Edge TTS"""
        import edge_tts
        
        # Use voice_id if set, otherwise look up from voice name
        if self.voice_id:
            voice_id = self.voice_id
            print(f"      Using specific voice_id: {voice_id}")
        else:
            voice_id = EDGE_TTS_VOICES.get(self.voice, "en-US-ChristopherNeural")
            print(f"      Using voice lookup: {self.voice} -> {voice_id}")
        
        communicate = edge_tts.Communicate(
            text,
            voice_id,
            rate=rate,
            pitch=pitch
        )
        await communicate.save(output_path)
        return output_path
    
    def _generate_audio_gtts(
        self,
        text: str,
        output_path: str,
        slow: bool = False
    ) -> str:
        """Generate audio using gTTS (fallback)"""
        from gtts import gTTS
        
        lang = GTTS_LANGUAGES.get(self.voice, "en")
        tts = gTTS(text=text, lang=lang, slow=slow)
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
        Tries Edge TTS first (high quality voices), falls back to gTTS.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio
            rate: Speed adjustment for Edge TTS
            pitch: Pitch adjustment for Edge TTS
            
        Returns:
            Tuple of (audio_path, duration_in_seconds)
        """
        print(f"      [AudioGenerator] voice={self.voice}, voice_id={self.voice_id}")
        
        # Try Edge TTS first (better quality, voice variety)
        if self._check_edge_tts():
            try:
                # Python 3.10+ requires asyncio.run() or creating a new event loop
                print(f"      [AudioGenerator] Starting Edge TTS with voice_id={self.voice_id}")
                asyncio.run(self._generate_audio_edge_tts(text, output_path, rate, pitch))
                print(f"      [AudioGenerator] Edge TTS SUCCESS with voice_id={self.voice_id}")
                audio = AudioFileClip(output_path)
                duration = audio.duration
                audio.close()
                return output_path, duration
            except Exception as e:
                import traceback
                print(f"      [AudioGenerator] Edge TTS FAILED: {type(e).__name__}: {e}")
                print(f"      [AudioGenerator] Traceback: {traceback.format_exc()}")
                print(f"      [AudioGenerator] Falling back to gTTS...")
        
        # Fallback to gTTS (NOTE: gTTS has only ONE voice per language!)
        print(f"      [AudioGenerator] Using gTTS fallback (voice variety NOT available)")
        slow = "-" in rate
        self._generate_audio_gtts(text, output_path, slow=slow)
        
        audio = AudioFileClip(output_path)
        duration = audio.duration
        audio.close()
        
        return output_path, duration
    
    def generate_segment_audio(
        self,
        segments,
        rate: str = "-5%"
    ) -> Tuple[List[AudioSegment], str, float]:
        """
        Generate audio for each segment and combine them.
        
        Returns:
            Tuple of (list of AudioSegments with timing, combined audio path, total duration)
        """
        audio_segments = []
        current_time = 0.0
        
        for i, segment in enumerate(segments):
            text = segment.text.strip()
            if not text:
                continue
            
            segment_path = str(self.temp_dir / f"segment_{i}.mp3")
            _, duration = self.generate_audio(text, segment_path, rate=rate)
            
            audio_segments.append(AudioSegment(
                text=text,
                audio_path=segment_path,
                start_time=current_time,
                end_time=current_time + duration,
                duration=duration
            ))
            
            current_time += duration
        
        # Combine segments
        if audio_segments:
            from moviepy.editor import concatenate_audioclips
            
            clips = [AudioFileClip(seg.audio_path) for seg in audio_segments]
            combined = concatenate_audioclips(clips)
            combined_path = str(self.temp_dir / "combined_audio.mp3")
            combined.write_audiofile(combined_path, verbose=False, logger=None)
            
            total_duration = combined.duration
            combined.close()
            for clip in clips:
                clip.close()
            
            return audio_segments, combined_path, total_duration
        
        return [], "", 0.0
