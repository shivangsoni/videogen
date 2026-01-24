"""
Translation module for multilingual video generation
Uses deep-translator for free Google Translate API
"""

from typing import Optional
from deep_translator import GoogleTranslator


# Language code mapping for deep-translator
LANGUAGE_CODES = {
    "en": "english",
    "en-uk": "english",
    "en-au": "english",
    "en-in": "english",
    "hi": "hindi",
    "fr": "french",
    "de": "german",
    "es": "spanish",
    "pt": "portuguese",
    "it": "italian",
    "ja": "japanese",
    "ko": "korean",
    "zh-CN": "chinese (simplified)",
    "ar": "arabic",
    "ru": "russian",
    "nl": "dutch",
    "pl": "polish",
    "tr": "turkish",
}


class Translator:
    """Handles text translation for multilingual TTS"""
    
    def __init__(self, target_language: str = "en"):
        """
        Initialize translator.
        
        Args:
            target_language: Target language code (e.g., 'hi', 'fr', 'es')
        """
        self.target_language = target_language
        self.target_lang_name = LANGUAGE_CODES.get(target_language, "english")
    
    def translate(self, text: str) -> str:
        """
        Translate text from English to target language.
        
        Args:
            text: English text to translate
            
        Returns:
            Translated text (or original if translation fails or target is English)
        """
        # Skip translation if target is English
        if self.target_language.startswith("en"):
            return text
        
        try:
            translator = GoogleTranslator(source='english', target=self.target_lang_name)
            translated = translator.translate(text)
            return translated if translated else text
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original on error
    
    def translate_segments(self, segments: list) -> list:
        """
        Translate all text in script segments for TTS.
        Creates translated versions while preserving original for captions.
        
        Args:
            segments: List of ScriptSegment objects
            
        Returns:
            List of segments with translated_text attribute added
        """
        for segment in segments:
            # Store original English text for captions
            segment.caption_text = segment.text
            segment.caption_lines = segment.display_lines.copy()
            
            # Translate text for TTS
            segment.translated_text = self.translate(segment.text)
            segment.translated_lines = [
                self.translate(line) for line in segment.display_lines
            ]
        
        return segments


def translate_text(text: str, target_language: str) -> str:
    """
    Convenience function to translate text.
    
    Args:
        text: English text
        target_language: Target language code
        
    Returns:
        Translated text
    """
    translator = Translator(target_language)
    return translator.translate(text)
