"""
Translation module for multilingual video generation
Uses Google Translate via multiple methods for reliability
"""

import os
import requests
import json
import re
import html
from typing import Optional
from urllib.parse import quote

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


# Map voice display names to language codes for translation
VOICE_TO_LANGUAGE = {
    "English - Male": "en",
    "English - Female": "en",
    "Hindi - Male": "hi",
    "Hindi - Female": "hi",
    "Kannada - Male": "kn",
    "Kannada - Female": "kn",
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
    "Punjabi - Male": "pa",
    "Punjabi - Female": "pa",
    "Malayalam - Male": "ml",
    "Malayalam - Female": "ml",
    "Indonesian - Male": "id",
    "Indonesian - Female": "id",
}


class Translator:
    """Handles text translation using Google Translate"""
    
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
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _translate_method1(self, text: str, target: str) -> Optional[str]:
        """Method 1: Google Translate API (translate.googleapis.com)"""
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'en',
                'tl': target,
                'dt': 't',
                'q': text,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and isinstance(result, list) and result[0]:
                    translated = ''.join(
                        part[0] for part in result[0] 
                        if part and isinstance(part, list) and part[0]
                    )
                    if translated:
                        return translated
        except Exception as e:
            print(f"      Method 1 failed: {e}")
        return None
    
    def _translate_method2(self, text: str, target: str) -> Optional[str]:
        """Method 2: Google Translate (clients5.google.com)"""
        try:
            url = "https://clients5.google.com/translate_a/t"
            params = {
                'client': 'dict-chrome-ex',
                'sl': 'en',
                'tl': target,
                'q': text,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and isinstance(result, list):
                    # Format: [["translated text"]]
                    if result[0] and isinstance(result[0], list):
                        return result[0][0]
                    elif isinstance(result[0], str):
                        return result[0]
        except Exception as e:
            print(f"      Method 2 failed: {e}")
        return None
    
    def _translate_method3(self, text: str, target: str) -> Optional[str]:
        """Method 3: Google Translate web scraping fallback"""
        try:
            encoded_text = quote(text)
            url = f"https://translate.google.com/m?sl=en&tl={target}&q={encoded_text}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Extract translation from HTML
                match = re.search(r'class="result-container">(.*?)</div>', response.text)
                if match:
                    translated = html.unescape(match.group(1))
                    return translated
        except Exception as e:
            print(f"      Method 3 failed: {e}")
        return None
    
    def translate(self, text: str) -> str:
        """
        Translate text from English to target language using Google Translate.
        Tries multiple methods for reliability.
        
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
        
        target = self.target_language
        
        # Try method 1
        result = self._translate_method1(text, target)
        if result:
            safe_print(f"      Translated: '{text[:30]}...' -> '{result[:30]}...'")
            return result
        
        # Try method 2
        result = self._translate_method2(text, target)
        if result:
            safe_print(f"      Translated (m2): '{text[:30]}...' -> '{result[:30]}...'")
            return result
        
        # Try method 3
        result = self._translate_method3(text, target)
        if result:
            safe_print(f"      Translated (m3): '{text[:30]}...' -> '{result[:30]}...'")
            return result
        
        safe_print(f"      Translation failed, using original: '{text[:30]}...'")
        return text
    
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
