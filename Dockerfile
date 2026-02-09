FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements_hf.txt .

# Install Python dependencies with specific compatible versions
RUN pip install --no-cache-dir \
    gradio==4.19.0 \
    huggingface_hub==0.20.3 \
    moviepy==1.0.3 \
    edge-tts>=6.1.0 \
    Pillow>=9.0.0 \
    numpy>=1.20.0 \
    requests>=2.28.0 \
    nest_asyncio>=1.5.0 \
    imageio>=2.9.0 \
    imageio-ffmpeg>=0.4.7 \
    proglog>=0.1.10 \
    decorator>=4.0.2 \
    tqdm>=4.60.0 \
    google-auth-oauthlib>=1.0.0 \
    google-api-python-client>=2.100.0

# Copy app files
COPY . .

# Expose port
EXPOSE 7860

# Run the app
CMD ["python", "gradio_app.py"]
