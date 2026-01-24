"""
YouTube Shorts Video Generator - Gradio App for Hugging Face Spaces
"""

import os
import uuid
import tempfile
from pathlib import Path

import gradio as gr

# Set up paths before imports
os.environ.setdefault("TEMP_DIR", tempfile.gettempdir() + "/videogen_temp")
os.environ.setdefault("OUTPUT_DIR", tempfile.gettempdir() + "/videogen_output")

from script_parser import parse_script, get_full_narration_text
from video_generator import VideoGenerator
from stock_video_fetcher import StockVideoFetcher


# Get API key from environment (set in HF Spaces secrets)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def generate_video(
    script_text: str,
    stock_keywords: str,
    voice_style: str,
    progress=gr.Progress()
) -> str:
    """Generate a YouTube Shorts video from script text."""
    
    if not script_text.strip():
        raise gr.Error("Please enter a script!")
    
    if not PEXELS_API_KEY:
        raise gr.Error("Pexels API key not configured. Please add PEXELS_API_KEY to Space secrets.")
    
    # Parse keywords
    keywords = None
    if stock_keywords.strip():
        keywords = [k.strip() for k in stock_keywords.split(",") if k.strip()]
    
    # Map voice styles to gTTS language codes - supports multiple languages
    from audio_generator import SUPPORTED_LANGUAGES
    voice = SUPPORTED_LANGUAGES.get(voice_style, "en")
    
    try:
        # Step 1: Initialize (0% -> 10%)
        progress(0.0, desc="Step 1/5: Initializing...")
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        generator.audio_generator.voice = voice
        progress(0.10, desc="Step 1/5: Initialization complete")
        
        # Step 2: Parse script (10% -> 20%)
        progress(0.15, desc="Step 2/5: Parsing script...")
        segments = parse_script(script_text)
        if not segments:
            raise gr.Error("Could not parse script. Check the format.")
        progress(0.20, desc="Step 2/5: Script parsed")
        
        # Generate unique output filename
        job_id = uuid.uuid4().hex[:8]
        output_filename = f"short_{job_id}.mp4"
        
        # Step 3: Generate audio (20% -> 40%)
        progress(0.25, desc="Step 3/5: Generating voiceover audio...")
        # Audio generation happens inside generate_video
        progress(0.40, desc="Step 3/5: Audio generated")
        
        # Step 4: Fetch stock videos (40% -> 60%)
        progress(0.45, desc="Step 4/5: Downloading stock videos...")
        progress(0.55, desc="Step 4/5: Processing video backgrounds...")
        progress(0.60, desc="Step 4/5: Videos ready")
        
        # Step 5: Build final video (60% -> 100%)
        progress(0.65, desc="Step 5/5: Building video...")
        
        # Create video (voice is the target language code for translation)
        result_path = generator.generate_video(
            segments=segments,
            output_filename=output_filename,
            stock_keywords=keywords,
            target_language=voice,  # Translate to this language for audio
        )
        
        progress(0.80, desc="Step 5/5: Encoding video...")
        progress(0.90, desc="Step 5/5: Finalizing...")
        progress(0.95, desc="Step 5/5: Cleaning up...")
        
        # Cleanup temp files
        generator.cleanup_temp_files()
        
        progress(1.0, desc="✅ Complete! Video ready.")
        
        return result_path
        
    except Exception as e:
        raise gr.Error(f"Error generating video: {str(e)}")


# Example scripts
EXAMPLE_SCRIPTS = [
    """Hook (0–2s):
Here's how to handle your life—no motivation required.

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

    """Hook (0–2s):
The secret to productivity nobody tells you.

Core:
Stop waiting for motivation.
Start with one small task.
Build momentum.

Your brain follows action,
not the other way around.

End (CTA):
Save this for later.""",

    """Hook (0–2s):
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


# Create Gradio interface
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
        max-height: 600px;
    }
    """
) as demo:
    
    gr.Markdown(
        """
        # 🎬 YouTube Shorts Video Generator
        ### Create engaging short-form videos with AI voiceover and stock footage
        """,
        elem_classes=["main-title"]
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            # Input section
            script_input = gr.Textbox(
                label="📝 Video Script",
                placeholder="""Hook (0–2s):
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
                    label="🎥 Stock Video Keywords",
                    placeholder="e.g., dark aesthetic, city lights, motivation",
                    info="Comma-separated keywords for Pexels stock videos",
                )
                
                voice_style = gr.Dropdown(
                    label="🎙️ Audio Language (auto-translates)",
                    choices=[
                        "English (US)",
                        "English (UK)",
                        "English (Australia)",
                        "English (India)",
                        "Hindi",
                        "French",
                        "German",
                        "Spanish",
                        "Portuguese",
                        "Italian",
                        "Japanese",
                        "Korean",
                        "Chinese (Simplified)",
                        "Arabic",
                        "Russian",
                        "Dutch",
                        "Polish",
                        "Turkish",
                    ],
                    value="English (US)",
                    info="Script will be auto-translated for voiceover. Captions stay in English.",
                )
            
            generate_btn = gr.Button(
                "🚀 Generate Video",
                variant="primary",
                size="lg",
            )
            
            # Examples
            gr.Examples(
                examples=[
                    [EXAMPLE_SCRIPTS[0], "dark aesthetic, discipline, motivation"],
                    [EXAMPLE_SCRIPTS[1], "productivity, work, success"],
                    [EXAMPLE_SCRIPTS[2], "sleep, bedroom, night"],
                ],
                inputs=[script_input, stock_keywords],
                label="📋 Example Scripts",
            )
        
        with gr.Column(scale=1):
            # Output section
            video_output = gr.Video(
                label="🎬 Generated Video",
                elem_classes=["output-video"],
            )
            
            gr.Markdown(
                """
                ### 📖 How to Use
                1. Write your script following the format:
                   - **Hook**: Attention-grabbing opener (0-2 seconds)
                   - **Core**: Main content (break into short lines)
                   - **End**: Call to action
                2. Add keywords for stock video backgrounds
                3. Choose a voice style
                4. Click Generate and wait 2-3 minutes
                
                ### ⚡ Tips
                - Keep lines short (3-7 words each)
                - Use powerful, emotional words
                - Match keywords to your content mood
                """
            )
    
    # Connect the generate button
    generate_btn.click(
        fn=generate_video,
        inputs=[script_input, stock_keywords, voice_style],
        outputs=video_output,
    )


# Launch for local testing
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
