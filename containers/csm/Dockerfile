# ─── Sesame AI CSM  –  speech synthesis ──────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        libsndfile1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone CSM repo
RUN git clone --depth 1 https://github.com/SesameAILabs/csm.git /app/csm

WORKDIR /app/csm

RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    pip install --no-cache-dir \
        torch \
        torchaudio \
        transformers \
        accelerate \
        soundfile \
        fastapi \
        uvicorn[standard] \
        huggingface_hub

# Wrapper REST API
COPY csm_api.py /app/csm_api.py

EXPOSE 8300

CMD ["python", "/app/csm_api.py"]
