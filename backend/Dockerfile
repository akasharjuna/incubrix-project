FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Whisper model (base, ~145MB) at build time to avoid runtime delay
RUN python -c "import whisper; whisper.load_model('base')" || true

# Copy source
COPY app/ ./app/

# Create artifact and temp dirs
RUN mkdir -p /artifacts/jobs /temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
