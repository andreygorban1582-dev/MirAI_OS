# ─── faster-whisper-plus  –  STT listener ────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        libsndfile1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone faster-whisper-plus
RUN git clone --depth 1 https://github.com/SesameAILabs/faster-whisper-plus.git /app/whisper_plus

WORKDIR /app/whisper_plus

RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    pip install --no-cache-dir \
        faster-whisper \
        soundfile \
        numpy \
        fastapi \
        uvicorn[standard] \
        python-multipart

COPY whisper_api.py /app/whisper_api.py

EXPOSE 8400

CMD ["python", "/app/whisper_api.py"]
