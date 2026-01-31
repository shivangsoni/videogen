---
title: YouTube Shorts Generator
emoji: 🎬
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# YouTube Shorts Video Generator

A Python tool to generate faceless YouTube Shorts (30-60 second videos) from text scripts. Perfect for creating motivational content, tips, and educational shorts.

## 🌐 Live Demo

**Try the UI version on Hugging Face Spaces:**
👉 [https://huggingface.co/spaces/shison/youtube-shorts-generator](https://huggingface.co/spaces/shison/youtube-shorts-generator)

## Features

- 🎬 Generates vertical videos (1080x1920) optimized for YouTube Shorts
- 🗣️ Automatic text-to-speech narration using Edge TTS (19 languages)
- ✨ Animated text overlays with fade transitions
- 🎨 Stock video backgrounds from Pexels
- 📝 Simple script format for easy content creation
- 🌍 **Multi-language support** - 19 languages with native voices
- 📤 **YouTube Auto-Publishing** - Publish directly to YouTube
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

## Batch Publishing (All Languages)

Generate and publish videos in **19 languages** automatically:

### Setup YouTube OAuth

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop App)
4. Download `client_secrets.json` to the project folder
5. Setup your YouTube account:
   ```bash
   python batch_video_generator.py --setup-account myaccount client_secrets.json
   ```

### Folder Structure

Create your content in `youtubeshorts/` folder:
```
youtubeshorts/
    My Video Topic/
        script.txt          # Your video script
        metadata.txt         # Keywords for stock videos
        youtube_publish.txt  # Title and description
```

**script.txt:**
```
Hook (0–2s):
Your attention-grabbing opening.

Core:
Main content here.
Each line becomes a caption.

End (CTA):
Follow for more!
```

**metadata.txt:**
```
keywords: motivation, success, mindset
```

**youtube_publish.txt:**
```
title: Your Video Title Here
description: Your video description.
#shorts #viral
```

### Publish All Languages

```bash
# Publish to all 19 languages (one at a time)
python publish_all.py "My Video Topic" myaccount

# Publish specific languages only
python publish_all.py "My Video Topic" myaccount "English,Hindi,Spanish"

# Generate single language
python batch_video_generator.py --folder "My Video Topic" --languages "English" --publish --account myaccount
```

### Supported Languages

| Language | Code | Voice |
|----------|------|-------|
| English | en | en-US-JennyNeural |
| Hindi | hi | hi-IN-SwaraNeural |
| Kannada | kn | kn-IN-SapnaNeural |
| Spanish | es | es-ES-ElviraNeural |
| French | fr | fr-FR-DeniseNeural |
| German | de | de-DE-KatjaNeural |
| Portuguese | pt | pt-BR-FranciscaNeural |
| Italian | it | it-IT-ElsaNeural |
| Japanese | ja | ja-JP-NanamiNeural |
| Korean | ko | ko-KR-SunHiNeural |
| Chinese | zh | zh-CN-XiaoxiaoNeural |
| Arabic | ar | ar-SA-ZariyahNeural |
| Russian | ru | ru-RU-SvetlanaNeural |
| Dutch | nl | nl-NL-ColetteNeural |
| Turkish | tr | tr-TR-EmelNeural |
| Polish | pl | pl-PL-AgnieszkaNeural |
| Vietnamese | vi | vi-VN-HoaiMyNeural |
| Thai | th | th-TH-PremwadeeNeural |
| Indonesian | id | id-ID-GadisNeural |

## License

MIT License - Feel free to use and modify!
