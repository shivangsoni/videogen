---
title: YouTube Shorts Generator
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: docker
app_file: gradio_app.py
pinned: false
license: mit
---

# 🎬 YouTube Shorts Video Generator

Create engaging short-form videos with AI voiceover and stock footage - completely free!

## Features

- 🎙️ **AI Voiceover**: Multiple voice styles using Edge TTS
- 🎥 **Stock Videos**: Automatic background videos from Pexels
- 🖼️ **Image-to-Script**: Upload or capture a photo to generate a script
- 🎞️ **Custom GIF Backgrounds**: Use your own GIF/video as the background
- 🎵 **Custom Soundtrack**: Add your own music with volume control
- 📝 **Easy Script Format**: Simple Hook → Core → CTA structure
- ⚡ **Fast Generation**: Videos ready in 2-3 minutes
- 📱 **Shorts Format**: Perfect 9:16 aspect ratio for YouTube Shorts, TikTok, Reels

## How to Use

1. **Write your script** following this format:
   ```
   Hook (0–2s):
   Your attention-grabbing opening line.

   Core:
   Your main content here.
   Break it into short lines.
   Each line becomes a caption.

   End (CTA):
   Your call to action.
   ```

2. **Add stock video keywords** (comma-separated) to match your content mood

   *Optional*: Upload a custom GIF/video background or a soundtrack

3. **Choose a voice style** from the dropdown

4. **Click Generate** and wait 2-3 minutes

## Tips for Great Videos

- Keep lines short (3-7 words each)
- Use powerful, emotional words in the hook
- Match keywords to your content mood (e.g., "dark aesthetic" for motivation)
- End with a clear call to action

## Setup (for your own Space)

Add your Pexels API key as a secret:
1. Go to Space Settings → Repository secrets
2. Add `PEXELS_API_KEY` with your free key from [pexels.com/api](https://www.pexels.com/api/)

To enable script generation (topic or image), also add:
- `GROQ_API_KEY` from [console.groq.com](https://console.groq.com)
- `GEMINI_API_KEY` from [Google AI Studio](https://makersuite.google.com/app/apikey) (for image-to-script)

## Tech Stack

- Gradio for the UI
- MoviePy for video editing
- Edge TTS for text-to-speech
- Pexels API for stock videos
- PIL for text overlays

## License

MIT License - Feel free to use and modify!
