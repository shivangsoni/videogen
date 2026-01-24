"""
Translation module for multilingual video generation
Uses Google Translate API directly via HTTP requests
"""

import requests
import json
import re
from typing import Optional
from urllib.parse import quote


# Language code mapping for googletrans
LANGUAGE_CODES = {
    "en": "en",
    "hi": "hi",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "pt": "pt",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "zh-CN": "zh-cn",
    "ar": "ar",
    "ru": "ru",
    "nl": "nl",
    "pl": "pl",
    "tr": "tr",
    "sv": "sv",
    "no": "no",
    "da": "da",
}

# Map voice display names to language codes for translation
VOICE_TO_LANGUAGE = {
    "English - Male": "en",
    "English - Female": "en",
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
    "Polish - Male": "pl",
    "Polish - Female": "pl",
    "Swedish - Male": "sv",
    "Swedish - Female": "sv",
    "Norwegian - Male": "no",
    "Norwegian - Female": "no",
    "Danish - Male": "da",
    "Danish - Female": "da",
}


class Translator:
    """Handles text translation for multilingual TTS using Google Translate directly"""
    
    # Google Translate API endpoint
    TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
    
    def __init__(self, target_language: str = "en"):
        """
        Initialize translator.
        
        Args:
            target_language: Target language code OR voice display name
        """
        # Handle voice display names like "Hindi - Male"
        if " - " in target_language:
            self.target_language = VOICE_TO_LANGUAGE.get(target_language, "en")
        else:
            self.target_language = target_language
        
        # Map to language code
        self.target_lang_code = LANGUAGE_CODES.get(self.target_language, "en")
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _google_translate(self, text: str, target: str, source: str = "en") -> str:
        """
        Call Google Translate API directly.
        
        Args:
            text: Text to translate
            target: Target language code
            source: Source language code
            
        Returns:
            Translated text
        """
        params = {
            'client': 'gtx',
            'sl': source,
            'tl': target,
            'dt': 't',
            'q': text,
        }
        
        response = self.session.get(self.TRANSLATE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse the response - it's a nested JSON array
        result = response.json()
        
        # Extract translated text from response
        # Response format: [[["translated text","original text",null,null,10]],null,"en",...]
        if result and isinstance(result, list) and result[0]:
            translated_parts = []
            for part in result[0]:
                if part and isinstance(part, list) and part[0]:
                    translated_parts.append(part[0])
            return ''.join(translated_parts)
        
        return text
    
    def translate(self, text: str) -> str:
        """
        Translate text from English to target language using Google Translate.
        
        Args:
            text: English text to translate
            
        Returns:
            Translated text (or original if translation fails or target is English)
        """
        # Skip translation if target is English
        if self.target_language.startswith("en"):
            return text
        
        # Skip empty text
        if not text or not text.strip():
            return text
        
        try:
            return self._google_translate(text, self.target_lang_code, "en")
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
