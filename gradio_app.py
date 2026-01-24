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
    language: str,
    voice_type: str,
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
    
    # Combine language and voice type (e.g., "Hindi" + "Male" -> "Hindi - Male")
    voice = f"{language} - {voice_type}"
    
    try:
        # Initialize
        progress(0.01, desc="Initializing video generator...")
        generator = VideoGenerator(pexels_api_key=PEXELS_API_KEY)
        generator.audio_generator.voice = voice
        
        # Parse script
        progress(0.03, desc="Parsing script...")
        segments = parse_script(script_text)
        if not segments:
            raise gr.Error("Could not parse script. Check the format.")
        
        # Generate unique output filename
        job_id = uuid.uuid4().hex[:8]
        output_filename = f"short_{job_id}.mp4"
        
        # Create progress callback for real-time updates
        def progress_callback(pct, msg):
            progress(pct, desc=msg)
        
        # Generate video with real-time progress updates
        result_path = generator.generate_video(
            segments=segments,
            output_filename=output_filename,
            stock_keywords=keywords,
            target_language=voice,
            progress_callback=progress_callback,
        )
        
        progress(1.0, desc="✅ Complete! Video ready.")
        
        # Cleanup temp files
        generator.cleanup_temp_files()
        
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
            
            with gr.Row():
                language = gr.Dropdown(
                    label="🌍 Language",
                    choices=[
                        "English",
                        "Hindi",
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
                    label="🎙️ Voice Type",
                    choices=["Male", "Female"],
                    value="Male",
                    info="Select male or female voice",
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
        inputs=[script_input, stock_keywords, language, voice_type],
        outputs=video_output,
    )


# Launch for local testing
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
