FROM python:3.11-slim

WORKDIR /app

# System deps for audio (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev libespeak-ng1 ffmpeg curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

RUN mkdir -p data logs

CMD ["python", "main.py", "--mode", "cli"]
