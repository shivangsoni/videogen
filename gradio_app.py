"""
YouTube Shorts Video Generator - Gradio App for Hugging Face Spaces
"""

import os
import uuid
import tempfile
import shutil
import threading
from pathlib import Path

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

# Get API key from environment (set in HF Spaces secrets)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

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


def generate_video(
    script_text: str,
    stock_keywords: str,
    language: str,
    voice_type: str,
    voice_name: str,
    use_anime_clips: bool,
    progress=gr.Progress()
) -> str:
    """Generate a YouTube Shorts video from script text."""
    
    # Reset cancellation flag at start of new job
    reset_cancel()
    
    if not script_text.strip():
        raise gr.Error("Please enter a script!")

    if not PEXELS_API_KEY and not use_anime_clips:
        raise gr.Error("Pexels API key not configured. Please add PEXELS_API_KEY to Space secrets or use anime clips.")

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
            
        # Generate video with real-time progress updates
        result_path = generator.generate_video(
            segments=segments,
            output_filename=output_filename,
            stock_keywords=keywords,
            target_language=voice,
            progress_callback=progress_callback,
            use_anime_clips=use_anime_clips,
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
                    label=" Use Anime Clips (Trace Moe API)",
                    value=False,
                    info="When checked, uses anime clips instead of Pexels stock videos",
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
                """
            )

    # Connect the generate button
    generate_btn.click(
        fn=generate_video,
        inputs=[script_input, stock_keywords, language, voice_type, voice_name, use_anime_clips],
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


# Launch WITHOUT queue - refreshing page kills the job
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )

# v2.2 - Removed queue, refresh page to cancel
