"""
YouTube Shorts Video Generator - Gradio App for Hugging Face Spaces
"""

import os
import uuid
import tempfile
import shutil
import threading
import json
import base64
import requests
from pathlib import Path

# Load environment variables (optional - for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not needed on HF Spaces (uses secrets)

import gradio as gr

# Set up paths before imports
TEMP_DIR = tempfile.gettempdir() + "/videogen_temp"
OUTPUT_DIR = tempfile.gettempdir() + "/videogen_output"
os.environ.setdefault("TEMP_DIR", TEMP_DIR)
os.environ.setdefault("OUTPUT_DIR", OUTPUT_DIR)

# Global cancellation flag - shared across all requests
_cancel_flag = threading.Event()
_current_job_id = None
_job_lock = threading.Lock()

def request_cancel():
    """Request cancellation of current job"""
    global _cancel_flag
    _cancel_flag.set()
    print("[App] Cancellation requested!")
    return " Cancellation requested. Please wait..."

def is_cancelled():
    """Check if cancellation was requested"""
    return _cancel_flag.is_set()

def reset_cancel():
    """Reset cancellation flag for new job"""
    global _cancel_flag
    _cancel_flag.clear()

# Clean up stale temp files on startup
def cleanup_stale_files():
    """Clean up any stale temp files from previous runs"""
    try:
        temp_path = Path(TEMP_DIR)
        if temp_path.exists():
            for f in temp_path.glob("*"):
                try:
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        shutil.rmtree(f)
                except Exception:
                    pass
            print("[Startup] Cleaned up stale temp files")
    except Exception as e:
        print(f"[Startup] Cleanup error: {e}")

cleanup_stale_files()

from script_parser import parse_script, get_full_narration_text
from video_generator import VideoGenerator
from stock_video_fetcher import StockVideoFetcher
from audio_generator import AudioGenerator, EDGE_TTS_VOICES
from translator import Translator

# Get API keys from environment (set in HF Spaces secrets)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Groq API (for script generation)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Topic presets for one-click script generation
TOPIC_PRESETS = [
    {
        "label": "Hydration & Morning Water",
        "topic": "Your health begins with how you treat your body before the first bite of food. Hydration in the morning changes everything.",
        "keywords": "hydration, water, morning routine, health, wellness, energy"
    },
    {
        "label": "Discipline Over Motivation",
        "topic": "You don’t need motivation. You need discipline. Small consistent actions beat big bursts of effort.",
        "keywords": "discipline, consistency, habits, mindset, success"
    },
    {
        "label": "The 1% Rule",
        "topic": "Improve 1% every day. Small wins compound into massive transformation over time.",
        "keywords": "self improvement, compounding, habits, growth, consistency"
    },
    {
        "label": "Sleep Quality Matters",
        "topic": "It’s not just how long you sleep. It’s how well you sleep. Fix your sleep quality and everything improves.",
        "keywords": "sleep, recovery, health, focus, energy"
    },
    {
        "label": "Custom (write your own)",
        "topic": "",
        "keywords": ""
    }
]

# YouTube credentials directory
YOUTUBE_CREDS_DIR = Path(__file__).parent / ".youtube_creds"

# Optional: load OAuth credentials from env (HF Secrets)
YOUTUBE_OAUTH_CREDENTIALS_JSON = os.environ.get("YOUTUBE_OAUTH_CREDENTIALS_JSON", "")
YOUTUBE_OAUTH_CREDENTIALS_B64 = os.environ.get("YOUTUBE_OAUTH_CREDENTIALS_B64", "")

# YouTube category IDs by language
LANGUAGE_CATEGORIES = {
    "English": "22", "Hindi": "24", "Kannada": "24", "Telugu": "24",
    "Tamil": "24", "Marathi": "24", "Bengali": "24", "Gujarati": "24",
    "Spanish": "24", "French": "22", "German": "22", "Portuguese": "24",
    "Italian": "22", "Russian": "24", "Dutch": "22", "Polish": "22",
    "Swedish": "22", "Norwegian": "22", "Danish": "22", "Turkish": "24",
    "Japanese": "24", "Korean": "24", "Chinese": "24", "Thai": "24",
    "Vietnamese": "24", "Indonesian": "24", "Arabic": "24",
}

# ============================================================================
# YOUTUBE PUBLISHING
# ============================================================================

# Global YouTube state
_yt_credentials = None
_yt_service = None
_yt_account_name = None


def get_youtube_accounts() -> list:
    """List available YouTube accounts from .youtube_creds/ or env"""
    accounts = []
    if YOUTUBE_CREDS_DIR.exists():
        accounts.extend([f.stem for f in YOUTUBE_CREDS_DIR.glob("*.json")])
    if YOUTUBE_OAUTH_CREDENTIALS_JSON or YOUTUBE_OAUTH_CREDENTIALS_B64:
        accounts.insert(0, "env")
    return accounts


def _load_env_credentials() -> str:
    """Return OAuth credentials JSON string from env, if present"""
    if YOUTUBE_OAUTH_CREDENTIALS_JSON:
        return YOUTUBE_OAUTH_CREDENTIALS_JSON
    if YOUTUBE_OAUTH_CREDENTIALS_B64:
        try:
            return base64.b64decode(YOUTUBE_OAUTH_CREDENTIALS_B64).decode("utf-8")
        except Exception:
            return ""
    return ""


def youtube_authenticate(account_name: str) -> str:
    """Authenticate with a saved YouTube account"""
    global _yt_credentials, _yt_service, _yt_account_name
    
    if not account_name:
        return "❌ Please select an account"
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        
        if account_name == "env":
            env_json = _load_env_credentials()
            if not env_json:
                return "❌ Env credentials not found. Set YOUTUBE_OAUTH_CREDENTIALS_JSON or YOUTUBE_OAUTH_CREDENTIALS_B64"
            creds = Credentials.from_authorized_user_info(json.loads(env_json), SCOPES)
        else:
            creds_file = YOUTUBE_CREDS_DIR / f"{account_name}.json"
            if not creds_file.exists():
                return f"❌ Credentials not found for '{account_name}'"
            creds = Credentials.from_authorized_user_file(str(creds_file), SCOPES)
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token (file-based only)
            if account_name != "env":
                creds_file.write_text(creds.to_json())
        
        _yt_credentials = creds
        _yt_service = build('youtube', 'v3', credentials=creds)
        _yt_account_name = account_name
        
        return f"✅ Authenticated as: {account_name}"
        
    except ImportError:
        return "❌ Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client"
    except Exception as e:
        return f"❌ Authentication failed: {e}"


def youtube_setup_new_account(account_name: str, client_secret_json: str) -> str:
    """Set up a new YouTube account using client secret JSON content"""
    global _yt_credentials, _yt_service, _yt_account_name
    
    if not account_name or not account_name.strip():
        return "❌ Please enter an account name"
    if not client_secret_json or not client_secret_json.strip():
        return "❌ Please paste the client_secret.json content"
    
    try:
        import json as _json
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        
        # Parse the JSON
        secret_data = _json.loads(client_secret_json)
        
        # Save temporarily for the flow
        temp_secret = Path(tempfile.gettempdir()) / f"client_secret_{uuid.uuid4().hex[:8]}.json"
        temp_secret.write_text(_json.dumps(secret_data))
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(temp_secret), SCOPES)
            credentials = flow.run_local_server(port=8080, open_browser=True)
        finally:
            temp_secret.unlink(missing_ok=True)
        
        # Save credentials
        YOUTUBE_CREDS_DIR.mkdir(exist_ok=True)
        creds_file = YOUTUBE_CREDS_DIR / f"{account_name.strip()}.json"
        creds_file.write_text(credentials.to_json())
        
        _yt_credentials = credentials
        _yt_service = build('youtube', 'v3', credentials=credentials)
        _yt_account_name = account_name.strip()
        
        return f"✅ Account '{account_name.strip()}' set up and authenticated! You can now publish videos."
        
    except ImportError:
        return "❌ Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client"
    except _json.JSONDecodeError:
        return "❌ Invalid JSON. Please paste the full content of your client_secret.json file."
    except Exception as e:
        return f"❌ Setup failed: {e}"


def translate_text_for_youtube(text: str, language: str) -> str:
    """Translate text to the target language for YouTube title/description"""
    if language == "English" or not text.strip():
        return text
    try:
        translator = Translator(target_language=f"{language} - Female")
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"[YouTube] Translation failed: {e}")
        return text


def publish_to_youtube(
    video_path: str,
    title: str,
    description: str,
    language: str,
    privacy: str,
    auto_translate: bool,
    progress=gr.Progress()
) -> str:
    """Publish the generated video to YouTube"""
    global _yt_service
    
    if not _yt_service:
        return "❌ Not authenticated. Please authenticate with YouTube first."
    
    if not video_path:
        return "❌ No video to publish. Generate a video first."
    
    if not Path(video_path).exists():
        return "❌ Video file not found. Generate a new video."
    
    if not title.strip():
        return "❌ Please enter a video title."
    
    try:
        import time as _time
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        
        progress(0.1, desc="Preparing upload...")
        
        # Auto-translate title and description if needed
        final_title = title
        final_description = description
        if auto_translate and language != "English":
            progress(0.15, desc=f"Translating to {language}...")
            final_title = translate_text_for_youtube(title, language)
            final_description = translate_text_for_youtube(description, language)
        
        # Add #shorts hashtag
        if "#shorts" not in final_description.lower():
            final_description += "\n\n#shorts"
        
        category_id = LANGUAGE_CATEGORIES.get(language, "22")
        
        body = {
            'snippet': {
                'title': final_title[:100],
                'description': final_description[:5000],
                'tags': ['shorts', 'viral', language.lower()],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy.lower(),
                'selfDeclaredMadeForKids': False,
                'shorts': {'shortsVideoMetadata': {}}
            }
        }
        
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=5 * 1024 * 1024
        )
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                progress(0.2, desc=f"Uploading to YouTube{' (retry ' + str(attempt) + ')' if attempt > 1 else ''}...")
                
                request = _yt_service.videos().insert(
                    part='snippet,status',
                    body=body,
                    media_body=media
                )
                
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        pct = 0.2 + (status.progress() * 0.7)
                        progress(pct, desc=f"Uploading: {int(status.progress() * 100)}%")
                
                video_id = response.get('id')
                video_url = f"https://youtube.com/shorts/{video_id}"
                
                progress(1.0, desc="✅ Published!")
                
                lang_note = f" ({language})" if language != "English" else ""
                return f"✅ Published to YouTube!\n\n🔗 {video_url}\n\n📺 Title: {final_title}{lang_note}\n🔒 Privacy: {privacy}"
                
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504) and attempt < max_retries:
                    wait = 2 ** attempt * 5
                    progress(0.2, desc=f"Server error, retrying in {wait}s...")
                    _time.sleep(wait)
                else:
                    return f"❌ Upload failed: {e}"
            except Exception as e:
                if attempt < max_retries:
                    wait = 2 ** attempt * 5
                    progress(0.2, desc=f"Error, retrying in {wait}s...")
                    _time.sleep(wait)
                else:
                    return f"❌ Upload failed after {max_retries} attempts: {e}"
        
        return "❌ Upload failed after all retries"
        
    except ImportError:
        return "❌ Google API libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client"
    except Exception as e:
        return f"❌ Error: {e}"

# Voice options organized by language and gender
VOICE_OPTIONS = {
    "English": {
        "Male": [
            ("Christopher (US)", "en-US-ChristopherNeural"),
            ("Guy (US)", "en-US-GuyNeural"),
            ("Eric (US)", "en-US-EricNeural"),
            ("Ryan (UK)", "en-GB-RyanNeural"),
            ("Ravi (India)", "en-IN-PrabhatNeural"),
        ],
        "Female": [
            ("Jenny (US)", "en-US-JennyNeural"),
            ("Aria (US)", "en-US-AriaNeural"),
            ("Ava (US)", "en-US-AvaNeural"),
            ("Michelle (US)", "en-US-MichelleNeural"),
            ("Emma (US)", "en-US-EmmaNeural"),
            ("Sonia (UK)", "en-GB-SoniaNeural"),
            ("Neerja (India)", "en-IN-NeerjaNeural"),
        ],
    },
    "Hindi": {
        "Male": [("Madhur", "hi-IN-MadhurNeural")],
        "Female": [("Swara", "hi-IN-SwaraNeural")],
    },
    "Spanish": {
        "Male": [("Alvaro (Spain)", "es-ES-AlvaroNeural"), ("Jorge (Mexico)", "es-MX-JorgeNeural")],
        "Female": [("Elvira (Spain)", "es-ES-ElviraNeural"), ("Dalia (Mexico)", "es-MX-DaliaNeural")],
    },
    "French": {
        "Male": [("Henri", "fr-FR-HenriNeural")],
        "Female": [("Denise", "fr-FR-DeniseNeural")],
    },
    "German": {
        "Male": [("Conrad", "de-DE-ConradNeural")],
        "Female": [("Katja", "de-DE-KatjaNeural")],
    },
    "Portuguese": {
        "Male": [("Antonio (Brazil)", "pt-BR-AntonioNeural")],
        "Female": [("Francisca (Brazil)", "pt-BR-FranciscaNeural")],
    },
    "Italian": {
        "Male": [("Diego", "it-IT-DiegoNeural")],
        "Female": [("Elsa", "it-IT-ElsaNeural")],
    },
    "Japanese": {
        "Male": [("Keita", "ja-JP-KeitaNeural")],
        "Female": [("Nanami", "ja-JP-NanamiNeural")],
    },
    "Korean": {
        "Male": [("InJoon", "ko-KR-InJoonNeural")],
        "Female": [("SunHi", "ko-KR-SunHiNeural")],
    },
    "Chinese": {
        "Male": [("Yunyang", "zh-CN-YunyangNeural")],
        "Female": [("Xiaoxiao", "zh-CN-XiaoxiaoNeural")],
    },
    "Arabic": {
        "Male": [("Hamed", "ar-SA-HamedNeural")],
        "Female": [("Zariyah", "ar-SA-ZariyahNeural")],
    },
    "Russian": {
        "Male": [("Dmitry", "ru-RU-DmitryNeural")],
        "Female": [("Svetlana", "ru-RU-SvetlanaNeural")],
    },
    "Dutch": {
        "Male": [("Maarten", "nl-NL-MaartenNeural")],
        "Female": [("Colette", "nl-NL-ColetteNeural")],
    },
    "Turkish": {
        "Male": [("Ahmet", "tr-TR-AhmetNeural")],
        "Female": [("Emel", "tr-TR-EmelNeural")],
    },
    "Polish": {
        "Male": [("Marek", "pl-PL-MarekNeural")],
        "Female": [("Zofia", "pl-PL-ZofiaNeural")],
    },
    "Swedish": {
        "Male": [("Mattias", "sv-SE-MattiasNeural")],
        "Female": [("Sofie", "sv-SE-SofieNeural")],
    },
    "Norwegian": {
        "Male": [("Finn", "nb-NO-FinnNeural")],
        "Female": [("Pernille", "nb-NO-PernilleNeural")],
    },
    "Danish": {
        "Male": [("Jeppe", "da-DK-JeppeNeural")],
        "Female": [("Christel", "da-DK-ChristelNeural")],
    },
    "Kannada": {
        "Male": [("Gagan", "kn-IN-GaganNeural")],
        "Female": [("Sapna", "kn-IN-SapnaNeural")],
    },
    "Tamil": {
        "Male": [("Valluvar", "ta-IN-ValluvarNeural")],
        "Female": [("Pallavi", "ta-IN-PallaviNeural")],
    },
    "Telugu": {
        "Male": [("Mohan", "te-IN-MohanNeural")],
        "Female": [("Shruti", "te-IN-ShrutiNeural")],
    },
    "Marathi": {
        "Male": [("Manohar", "mr-IN-ManoharNeural")],
        "Female": [("Aarohi", "mr-IN-AarohiNeural")],
    },
    "Bengali": {
        "Male": [("Bashkar", "bn-IN-BashkarNeural")],
        "Female": [("Tanishaa", "bn-IN-TanishaaNeural")],
    },
    "Gujarati": {
        "Male": [("Niranjan", "gu-IN-NiranjanNeural")],
        "Female": [("Dhwani", "gu-IN-DhwaniNeural")],
    },
}

# Hello translations for preview
HELLO_TRANSLATIONS = {
    "English": "Hello! This is how I sound.",
    "Hindi": "नमसत! म ऐस बलत ह",
    "Spanish": "Hola! Así es como sueno.",
    "French": "Bonjour! Voici comment je parle.",
    "German": "Hallo! So klinge ich.",
    "Portuguese": "Olá! É assim que eu falo.",
    "Italian": "Ciao! Ecco come parlo.",
    "Japanese": "こんにちは！私の声はこんな感じです。",
    "Korean": "안녕하세요! 제 목소리는 이렇습니다.",
    "Chinese": "你好！这是我说话的声音。",
    "Arabic": "مرحبا! هذا هو صوتي.",
    "Russian": "Привет! Вот как я звучу.",
    "Dutch": "Hallo! Zo klink ik.",
    "Turkish": "Merhaba! Sesim böyle.",
    "Polish": "Cześć! Tak brzmi mój głos.",
    "Swedish": "Hej! Så här låter jag.",
    "Norwegian": "Hei! Slik høres jeg ut.",
    "Danish": "Hej! Sådan lyder jeg.",
    "Kannada": "ನಮಸ್ಕಾರ! ನಾನು ಹೀಗೆ ಮಾತನಾಡುತ್ತೇನೆ.",
    "Tamil": "வணக்கம்! நான் இப்படி பேசுவேன்.",
    "Telugu": "నమస్కారం! నేను ఇలా మాట్లాడతాను.",
    "Marathi": "नमस्कार! मी असा बोलतो.",
    "Bengali": "নমস্কার! আমি এইভাবে কথা বলি.",
    "Gujarati": "નમસ્તે! હું આવી રીતે બોલું છું.",
}


def get_voice_choices(language: str, voice_type: str) -> list:
    """Get voice choices based on language and gender"""
    if language in VOICE_OPTIONS and voice_type in VOICE_OPTIONS[language]:
        return [name for name, _ in VOICE_OPTIONS[language][voice_type]]
    return ["Default"]


def get_voice_id(language: str, voice_type: str, voice_name: str) -> str:
    """Get the Edge TTS voice ID from selections"""
    if language in VOICE_OPTIONS and voice_type in VOICE_OPTIONS[language]:
        for name, voice_id in VOICE_OPTIONS[language][voice_type]:
            if name == voice_name:
                return voice_id
    # Fallback
    return EDGE_TTS_VOICES.get(f"{language} - {voice_type}", "en-US-ChristopherNeural")


def update_voice_dropdown(language: str, voice_type: str):
    """Update voice dropdown when language or voice type changes"""
    choices = get_voice_choices(language, voice_type)
    return gr.update(choices=choices, value=choices[0] if choices else "Default")


def preview_voice(language: str, voice_type: str, voice_name: str):
    """Generate a preview audio of the selected voice saying Hello"""
    import asyncio

    try:
        voice_id = get_voice_id(language, voice_type, voice_name)
        hello_text = HELLO_TRANSLATIONS.get(language, "Hello! This is how I sound.")

        # Generate preview audio
        temp_dir = Path(tempfile.gettempdir()) / "videogen_temp"
        temp_dir.mkdir(exist_ok=True)
        preview_path = temp_dir / f"preview_{uuid.uuid4().hex[:8]}.mp3"

        import edge_tts

        async def generate():
            communicate = edge_tts.Communicate(hello_text, voice_id)
            await communicate.save(str(preview_path))

        asyncio.run(generate())

        return str(preview_path)

    except Exception as e:
        print(f"Preview error: {e}")
        return None


def update_topic_fields(selected_label: str):
    """Populate topic and keywords based on preset selection"""
    for preset in TOPIC_PRESETS:
        if preset["label"] == selected_label:
            return preset["topic"], preset["keywords"]
    return "", ""


def _format_hashtags(keywords: str) -> str:
    tags = []
    for kw in [k.strip() for k in keywords.split(",") if k.strip()]:
        tag = "#" + "".join(ch for ch in kw if ch.isalnum() or ch == " ").strip().replace(" ", "")
        if tag != "#":
            tags.append(tag)
    if "#shorts" not in [t.lower() for t in tags]:
        tags.append("#shorts")
    return " ".join(tags)


def _parse_groq_response(raw: str) -> tuple:
    """Parse Groq response for SCRIPT/TITLE/DESCRIPTION/KEYWORDS"""
    script = ""
    title = ""
    description = ""
    keywords = ""
    current_section = None

    for line in raw.split("\n"):
        line_lower = line.lower().strip()
        if line_lower.startswith("script:"):
            current_section = "script"
            continue
        elif line_lower.startswith("title:"):
            current_section = "title"
            continue
        elif line_lower.startswith("description:"):
            current_section = "description"
            continue
        elif line_lower.startswith("keywords:"):
            current_section = "keywords"
            continue

        if current_section == "script":
            script += line + "\n"
        elif current_section == "title":
            if line.strip():
                title = line.strip()
                current_section = None
        elif current_section == "description":
            description += line + "\n"
        elif current_section == "keywords":
            if line.strip():
                keywords += line.strip() + " "

    script = script.strip() if script else raw
    description = description.strip()
    keywords = keywords.strip().replace(";", ",")

    return script, keywords, title, description


def _encode_image_to_base64(image) -> str:
    """Encode PIL/numpy image to base64 data URL"""
    import io
    from PIL import Image
    import numpy as np

    if image is None:
        return ""

    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def generate_script_from_topic(
    topic: str,
    keywords: str,
    language: str,
    progress=gr.Progress()
):
    """Generate script + keywords + title + description from topic using Groq"""
    if not topic.strip():
        raise gr.Error("Please enter a topic")
    if not GROQ_API_KEY:
        raise gr.Error("GROQ_API_KEY not set. Add it to Space secrets.")

    prompt = f"""Create a YouTube Shorts script about: {topic}
Keywords to use: {keywords or 'none'}

Follow this EXACT format:

SCRIPT:
Hook (0-2s):
[One powerful opening line that stops scrolling]

Core:
[4-7 short punchy lines, each on its own line]
[Use line breaks between thoughts]
[Keep each line under 10 words]

End (CTA):
[Call to action - save/follow/share]

TITLE:
[Catchy YouTube title under 60 chars, use emotion words]

DESCRIPTION:
[3-4 lines with emojis, include the hook and CTA]

Return ONLY the content in this format, no explanations."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are a viral YouTube Shorts script writer. Create punchy, impactful content that hooks viewers in 2 seconds and delivers value in under 60 seconds. Use short sentences. Be direct. No fluff."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 1000
    }

    progress(0.1, desc="Generating script with Groq...")
    response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=60)
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()

    script, parsed_keywords, title, description = _parse_groq_response(raw)

    # Append hashtags based on keywords
    keywords_out = keywords.strip() or parsed_keywords.strip()
    if keywords_out:
        hashtags = _format_hashtags(keywords_out)
        if hashtags:
            description = (description + "\n" + hashtags).strip()

    progress(1.0, desc="Content ready")

    # Return script, keywords, title, description
    return script, keywords_out, title, description


def generate_script_from_image(
    image,
    language: str,
    progress=gr.Progress()
):
    """Generate script + keywords + title + description from an image using Groq Vision"""
    if image is None:
        raise gr.Error("Please upload or capture an image")
    if not GROQ_API_KEY:
        raise gr.Error("GROQ_API_KEY not set. Add it to Space secrets.")

    image_b64 = _encode_image_to_base64(image)
    if not image_b64:
        raise gr.Error("Could not read image")

    prompt = """Create a YouTube Shorts script based on the image.
Follow this EXACT format:

SCRIPT:
Hook (0-2s):
[One powerful opening line that stops scrolling]

Core:
[4-7 short punchy lines, each on its own line]
[Use line breaks between thoughts]
[Keep each line under 10 words]

End (CTA):
[Call to action - save/follow/share]

TITLE:
[Catchy YouTube title under 60 chars, use emotion words]

DESCRIPTION:
[3-4 lines with emojis, include the hook and CTA]

KEYWORDS:
[Comma-separated keywords derived from the image]

Return ONLY the content in this format, no explanations."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.2-11b-vision-preview",
        "messages": [
            {
                "role": "system",
                "content": "You are a viral YouTube Shorts script writer. Create punchy, impactful content that hooks viewers in 2 seconds and delivers value in under 60 seconds. Use short sentences. Be direct. No fluff."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_b64}}
                ]
            }
        ],
        "temperature": 0.8,
        "max_tokens": 1000
    }

    progress(0.1, desc="Analyzing image with Groq...")
    response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"].strip()

    script, keywords, title, description = _parse_groq_response(raw)

    if keywords:
        hashtags = _format_hashtags(keywords)
        if hashtags:
            description = (description + "\n" + hashtags).strip()

    progress(1.0, desc="Content ready")

    return script, keywords, title, description


def generate_video(
    script_text: str,
    stock_keywords: str,
    language: str,
    voice_type: str,
    voice_name: str,
    use_anime_clips: bool,
    use_giphy_clips: bool,
    use_pixabay_clips: bool,
    custom_gif,
    custom_soundtrack,
    soundtrack_volume: float,
    progress=gr.Progress()
) -> str:
    """Generate a YouTube Shorts video from script text."""
    
    # Reset cancellation flag at start of new job
    reset_cancel()
    
    if not script_text.strip():
        raise gr.Error("Please enter a script!")

    if (
        not PEXELS_API_KEY
        and not use_anime_clips
        and not use_giphy_clips
        and not use_pixabay_clips
        and not custom_gif
    ):
        raise gr.Error("Pexels API key not configured. Please add PEXELS_API_KEY to Space secrets or use anime/GIPHY/Pixabay/custom GIF clips.")

    # Check if GIPHY is requested but API key is missing
    if use_giphy_clips and not GIPHY_API_KEY:
        raise gr.Error("GIPHY API key not configured. Please add GIPHY_API_KEY to Space secrets.")
    
    # Check if Pixabay is requested but API key is missing
    if use_pixabay_clips and not PIXABAY_API_KEY:
        raise gr.Error("Pixabay API key not configured. Please add PIXABAY_API_KEY to Space secrets.")

    # Parse keywords
    keywords = None
    if stock_keywords.strip():
        keywords = [k.strip() for k in stock_keywords.split(",") if k.strip()]

    # Get the specific voice ID
    voice_id = get_voice_id(language, voice_type, voice_name)
    voice = f"{language} - {voice_type}"  # For translation
    print(f"[generate_video] Selected: language={language}, voice_type={voice_type}, voice_name={voice_name}")
    print(f"[generate_video] voice_id resolved to: {voice_id}")

    try:
        # Check for cancellation
        if is_cancelled():
            raise gr.Error("Generation cancelled")
            
        # Initialize
        progress(0.01, desc="Initializing video generator...")
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        generator.audio_generator.voice = voice
        generator.audio_generator.voice_id = voice_id  # Use specific voice ID
        print(f"[generate_video] Set audio_generator.voice_id = {generator.audio_generator.voice_id}")

        # Check for cancellation
        if is_cancelled():
            raise gr.Error("Generation cancelled")
            
        # Parse script
        progress(0.03, desc="Parsing script...")
        segments = parse_script(script_text)
        if not segments:
            raise gr.Error("Could not parse script. Check the format.")

        # Generate unique output filename
        job_id = uuid.uuid4().hex[:8]
        output_filename = f"short_{job_id}.mp4"

        # Create progress callback that checks for cancellation
        def progress_callback(pct, msg):
            if is_cancelled():
                raise Exception("Generation cancelled by user")
            progress(pct, desc=msg)

        # Check for cancellation
        if is_cancelled():
            raise gr.Error("Generation cancelled")
            
        # Resolve file paths from Gradio components
        custom_gif_path = None
        if custom_gif and isinstance(custom_gif, str):
            custom_gif_path = custom_gif
        elif custom_gif and hasattr(custom_gif, "name"):
            custom_gif_path = custom_gif.name

        custom_soundtrack_path = None
        if custom_soundtrack and isinstance(custom_soundtrack, str):
            custom_soundtrack_path = custom_soundtrack
        elif custom_soundtrack and hasattr(custom_soundtrack, "name"):
            custom_soundtrack_path = custom_soundtrack.name

        # Generate video with real-time progress updates
        result_path = generator.generate_video(
            segments=segments,
            output_filename=output_filename,
            stock_keywords=keywords,
            target_language=voice,
            progress_callback=progress_callback,
            use_anime_clips=use_anime_clips,
            use_giphy_clips=use_giphy_clips,
            use_pixabay_clips=use_pixabay_clips,
            custom_gif_path=custom_gif_path,
            custom_soundtrack_path=custom_soundtrack_path,
            soundtrack_volume=soundtrack_volume,
        )

        progress(1.0, desc=" Complete! Video ready.")

        # Cleanup temp files
        generator.cleanup_temp_files()

        return result_path

    except Exception as e:
        if "cancelled" in str(e).lower():
            raise gr.Error(" Generation cancelled")
        raise gr.Error(f"Error generating video: {str(e)}")


# Example scripts
EXAMPLE_SCRIPTS = [
    """Hook (02s):
Here's how to handle your lifeno motivation required.

Core:
Fix your sleep.
Fix your diet.
Fix your room.

You don't need a new mindset.
You need basic discipline.

Chaos outside
creates chaos inside.

End (CTA):
Follow for more raw truth.""",
    """Hook (02s):
The secret to productivity nobody tells you.

Core:
Stop waiting for motivation.
Start with one small task.
Build momentum.

Your brain follows action,
not the other way around.

End (CTA):
Save this for later.""",
    """Hook (02s):
Why you're always tired.

Core:
It's not about sleep hours.
It's about sleep quality.

No screens one hour before bed.
Cold room. Dark room.
Same time every night.

End (CTA):
Try this tonight.""",
]


# Create Gradio interface - NO QUEUE for immediate response
with gr.Blocks(
    title="YouTube Shorts Generator",
    theme=gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
    ),
    css="""
    .main-title {
        text-align: center;
        margin-bottom: 0.5em;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .output-video {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 600px;
    }
    .output-video video {
        max-height: 85vh !important;
        height: auto !important;
        width: auto !important;
        max-width: 100% !important;
        object-fit: contain;
    }
    """
) as demo:

    # Hidden status for cancellation
    status_text = gr.State("")

    gr.Markdown(
        """
        #  YouTube Shorts Video Generator
        ### Create engaging short-form videos with AI voiceover and stock footage
         **Note**: Only one video can be generated at a time. Refresh the page to cancel and start fresh.
        """,
        elem_classes=["main-title"]
    )

    with gr.Row():
        with gr.Column(scale=1):
            # Input section
            with gr.Accordion("✨ Generate Script from Topic", open=True):
                topic_dropdown = gr.Dropdown(
                    label="Topic Preset",
                    choices=[p["label"] for p in TOPIC_PRESETS],
                    value=TOPIC_PRESETS[0]["label"],
                )
                topic_input = gr.Textbox(
                    label="Topic",
                    placeholder="Describe the idea in 1-2 sentences",
                    value=TOPIC_PRESETS[0]["topic"],
                    lines=2,
                )
                topic_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="comma-separated keywords",
                    value=TOPIC_PRESETS[0]["keywords"],
                    lines=1,
                )
                generate_script_btn = gr.Button("⚡ Generate Script + Title + Description", size="sm")

            with gr.Accordion("🖼️ Generate Script from Image", open=False):
                image_input = gr.Image(
                    label="Upload or Capture Image",
                    sources=["upload", "webcam"],
                    type="pil",
                )
                generate_image_script_btn = gr.Button("🔍 Generate from Image", size="sm")

            script_input = gr.Textbox(
                label=" Video Script",
                placeholder="""Hook (02s):
Your attention-grabbing opening line.

Core:
Your main content here.
Break it into short lines.
Each line becomes a caption.

End (CTA):
Your call to action.""",
                lines=15,
                max_lines=25,
            )

            with gr.Row():
                stock_keywords = gr.Textbox(
                    label=" Stock Video Keywords",
                    placeholder="e.g., dark aesthetic, city lights, motivation",
                    info="Comma-separated keywords for Pexels stock videos",
                )

            with gr.Row():
                language = gr.Dropdown(
                    label=" Language",
                    choices=[
                        "English",
                        "Hindi",
                        "Kannada",
                        "Tamil",
                        "Telugu",
                        "Marathi",
                        "Bengali",
                        "Gujarati",
                        "French",
                        "German",
                        "Spanish",
                        "Portuguese",
                        "Italian",
                        "Dutch",
                        "Japanese",
                        "Korean",
                        "Chinese",
                        "Arabic",
                        "Russian",
                        "Turkish",
                        "Polish",
                        "Swedish",
                        "Norwegian",
                        "Danish",
                    ],
                    value="English",
                    info="Script auto-translates to selected language",
                )

                voice_type = gr.Dropdown(
                    label=" Voice Type",
                    choices=["Male", "Female"],
                    value="Male",
                    info="Select male or female voice",
                )

            with gr.Row():
                voice_name = gr.Dropdown(
                    label=" Voice",
                    choices=get_voice_choices("English", "Male"),
                    value="Christopher (US)",
                    info="Select specific voice",
                )

                preview_btn = gr.Button(
                    " Preview",
                    size="sm",
                    scale=0,
                )

            # Audio preview output (hidden until played)
            voice_preview = gr.Audio(
                label="Voice Preview",
                visible=True,
                autoplay=True,
            )

            with gr.Row():
                use_anime_clips = gr.Checkbox(
                    label="🎬 Use Anime Clips (Trace Moe API)",
                    value=False,
                    info="Uses anime clips instead of Pexels stock videos",
                )
                use_giphy_clips = gr.Checkbox(
                    label="🎭 Use GIPHY (Animated GIFs)",
                    value=False,
                    info="Uses animated GIFs from GIPHY",
                )
                use_pixabay_clips = gr.Checkbox(
                    label="🖼️ Use Pixabay (Free Videos)",
                    value=False,
                    info="Uses free stock videos from Pixabay",
                )

            with gr.Row():
                custom_gif = gr.File(
                    label="Custom GIF/Video Background (optional)",
                    file_types=[".gif", ".mp4", ".mov", ".webm"],
                )

            with gr.Row():
                custom_soundtrack = gr.Audio(
                    label="Custom Soundtrack (optional)",
                    type="filepath",
                )
                soundtrack_volume = gr.Slider(
                    label="Soundtrack Volume",
                    minimum=0.0,
                    maximum=1.0,
                    value=0.2,
                    step=0.05,
                )

            with gr.Row():
                generate_btn = gr.Button(
                    " Generate Video",
                    variant="primary",
                    size="lg",
                )
                stop_btn = gr.Button(
                    " Cancel",
                    variant="stop",
                    size="lg",
                )
            
            cancel_status = gr.Textbox(label="Status", visible=False)

            # Examples
            gr.Examples(
                examples=[
                    [EXAMPLE_SCRIPTS[0], "dark aesthetic, discipline, motivation"],
                    [EXAMPLE_SCRIPTS[1], "productivity, work, success"],
                    [EXAMPLE_SCRIPTS[2], "sleep, bedroom, night"],
                ],
                inputs=[script_input, stock_keywords],
                label=" Example Scripts",
            )

        with gr.Column(scale=1):
            # Output section
            video_output = gr.Video(
                label=" Generated Video",
                elem_classes=["output-video"],
            )

            gr.Markdown(
                """
                ###  How to Use
                1. Write your script following the format:
                   - **Hook**: Attention-grabbing opener (0-2 seconds)
                   - **Core**: Main content (break into short lines)
                   - **End**: Call to action
                2. Add keywords for stock video backgrounds
                3. Choose a voice style
                4. Click Generate and wait 2-3 minutes

                ###  Tips
                - Keep lines short (3-7 words each)
                - Use powerful, emotional words
                - Match keywords to your content mood
                
                ###  To Cancel
                - Click **Cancel** or simply **refresh the page**
                
                ###  Progress
                - Real-time encoding progress shown during video rendering
                - Watch the progress bar for frame-by-frame status
                """
            )

            # YouTube Publishing Section
            gr.Markdown("---")
            gr.Markdown("### 📤 Publish to YouTube")
            
            with gr.Accordion("🔑 YouTube Authentication", open=False):
                saved_accounts = get_youtube_accounts()
                
                gr.Markdown("**HF Secrets option:** set `YOUTUBE_OAUTH_CREDENTIALS_JSON` (or `YOUTUBE_OAUTH_CREDENTIALS_B64`) to use the `env` account.")

                if saved_accounts:
                    gr.Markdown("**Use a saved account:**")
                    with gr.Row():
                        yt_account_dropdown = gr.Dropdown(
                            label="Saved Account",
                            choices=saved_accounts,
                            value=saved_accounts[0] if saved_accounts else None,
                            info="Select a previously configured account",
                        )
                        yt_auth_btn = gr.Button("🔐 Authenticate", size="sm")
                else:
                    yt_account_dropdown = gr.Dropdown(
                        label="Saved Account",
                        choices=[],
                        value=None,
                        visible=False,
                    )
                    yt_auth_btn = gr.Button("🔐 Authenticate", visible=False, size="sm")
                
                gr.Markdown("**Or set up a new account:**")
                yt_new_account_name = gr.Textbox(
                    label="Account Name",
                    placeholder="e.g., mychannel",
                    info="A name to identify this YouTube account",
                )
                yt_client_secret = gr.Textbox(
                    label="Client Secret JSON",
                    placeholder='Paste the full content of your client_secret.json file here',
                    lines=3,
                    info="From Google Cloud Console > OAuth 2.0 credentials",
                )
                yt_setup_btn = gr.Button("⚙️ Set Up New Account", size="sm")
                
                yt_auth_status = gr.Textbox(
                    label="Auth Status",
                    interactive=False,
                    value="Not authenticated",
                )
            
            yt_title = gr.Textbox(
                label="📺 Video Title",
                placeholder="Enter your YouTube Shorts title",
                info="Max 100 characters. Auto-translates to video language.",
                max_lines=1,
            )
            yt_description = gr.Textbox(
                label="📝 Description",
                placeholder="Enter video description. #shorts will be added automatically.",
                lines=3,
                info="Max 5000 characters. Auto-translates to video language.",
            )
            with gr.Row():
                yt_privacy = gr.Dropdown(
                    label="🔒 Privacy",
                    choices=["Private", "Unlisted", "Public"],
                    value="Private",
                    info="Start with Private, change later on YouTube",
                )
                yt_auto_translate = gr.Checkbox(
                    label="🌐 Auto-translate title & description",
                    value=True,
                    info="Translate to the selected video language",
                )
            
            yt_publish_btn = gr.Button(
                "📤 Publish to YouTube",
                variant="primary",
                size="lg",
            )
            
            yt_publish_result = gr.Textbox(
                label="Publish Result",
                interactive=False,
                lines=4,
            )

    # Connect the generate button
    generate_btn.click(
        fn=generate_video,
        inputs=[
            script_input,
            stock_keywords,
            language,
            voice_type,
            voice_name,
            use_anime_clips,
            use_giphy_clips,
            use_pixabay_clips,
            custom_gif,
            custom_soundtrack,
            soundtrack_volume,
        ],
        outputs=video_output,
    )

    # Stop button sets cancellation flag
    stop_btn.click(
        fn=request_cancel,
        inputs=None,
        outputs=cancel_status,
    )

    # Update voice dropdown when language or voice type changes
    language.change(
        fn=update_voice_dropdown,
        inputs=[language, voice_type],
        outputs=voice_name,
    )

    voice_type.change(
        fn=update_voice_dropdown,
        inputs=[language, voice_type],
        outputs=voice_name,
    )

    # Preview voice button
    preview_btn.click(
        fn=preview_voice,
        inputs=[language, voice_type, voice_name],
        outputs=voice_preview,
    )

    # Topic preset change
    topic_dropdown.change(
        fn=update_topic_fields,
        inputs=[topic_dropdown],
        outputs=[topic_input, topic_keywords],
    )

    # Generate script from topic
    generate_script_btn.click(
        fn=generate_script_from_topic,
        inputs=[topic_input, topic_keywords, language],
        outputs=[script_input, stock_keywords, yt_title, yt_description],
    )

    generate_image_script_btn.click(
        fn=generate_script_from_image,
        inputs=[image_input, language],
        outputs=[script_input, stock_keywords, yt_title, yt_description],
    )

    # YouTube auth button
    yt_auth_btn.click(
        fn=youtube_authenticate,
        inputs=[yt_account_dropdown],
        outputs=yt_auth_status,
    )

    # YouTube setup new account button
    yt_setup_btn.click(
        fn=youtube_setup_new_account,
        inputs=[yt_new_account_name, yt_client_secret],
        outputs=yt_auth_status,
    )

    # YouTube publish button
    yt_publish_btn.click(
        fn=publish_to_youtube,
        inputs=[video_output, yt_title, yt_description, language, yt_privacy, yt_auto_translate],
        outputs=yt_publish_result,
    )


# Enable queue so gr.Progress() can push real-time updates to the browser
demo.queue(max_size=1, default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )

# v2.5 - Added topic-based script generation (Groq) with title/description
