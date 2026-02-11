FROM python:3.10-slim

WORKDIR /app

# Install system dependencies with minimal footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for caching
COPY requirements_hf.txt .

# Install Python dependencies with no cache to save space
RUN pip install --no-cache-dir -r requirements_hf.txt

# Copy app files
COPY . .

# Expose port
EXPOSE 7860

# Run the app
CMD ["python", "gradio_app.py"]
