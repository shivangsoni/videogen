# YouTube Shorts Video Generator

A Python tool to generate faceless YouTube Shorts (30-60 second videos) from text scripts. Perfect for creating motivational content, tips, and educational shorts.

## Features

- 🎬 Generates vertical videos (1080x1920) optimized for YouTube Shorts
- 🗣️ Automatic text-to-speech narration using Google TTS (free)
- ✨ Animated text overlays with fade transitions
- 🎨 Dark themed backgrounds perfect for text-based content
- 📝 Simple script format for easy content creation
- 🆓 100% free - uses open source libraries only

## Installation

1. **Clone/navigate to the project directory:**
   ```bash
   cd videogen
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg** (required for video processing):
   - Download from: https://ffmpeg.org/download.html
   - Or use chocolatey: `choco install ffmpeg`
   - Or use winget: `winget install ffmpeg`
   - Make sure `ffmpeg` is in your system PATH

## Script Format

Create a text file with the following structure:

```
Hook (0–2s):
Your attention-grabbing opening line.

Core:
Main point 1.
Main point 2.
Main point 3.

Additional thoughts here.
Each line becomes a separate text overlay.

End (CTA):
Your call to action.
Follow for more!
```

### Sections:
- **Hook**: Opening line to grab attention
- **Core**: Main content (can have multiple paragraphs)
- **End (CTA)**: Call to action

## Usage

### Basic usage:
```bash
python main.py scripts/example_script.txt
```

### Custom output name:
```bash
python main.py scripts/my_script.txt -o my_video.mp4
```

### Keep temporary files:
```bash
python main.py scripts/example_script.txt --no-cleanup
```

## Output

Videos are saved to the `output/` directory.

## Configuration

Edit `config.py` to customize:

- Video dimensions (default: 1080x1920)
- Font sizes for different sections
- Background colors
- Animation timings
- TTS language settings

## Example Scripts

Check the `scripts/` folder for example scripts you can use as templates.

## Tips for Better Videos

1. **Keep it short**: Aim for 8-12 text segments for a 30-60 second video
2. **One idea per line**: Each line becomes a separate text overlay
3. **Strong hook**: First line should grab attention immediately
4. **Clear CTA**: End with a clear call to action

## Troubleshooting

### "FFmpeg not found"
Make sure FFmpeg is installed and added to your system PATH. Restart your terminal after installation.

### "Font not found"
The generator will use system fonts. If text doesn't appear correctly, install Arial or update the font path in `config.py`.

### Video too long/short
Adjust `TEXT_DISPLAY_TIME` in `config.py` or modify your script length.

## License

MIT License - Feel free to use and modify!
