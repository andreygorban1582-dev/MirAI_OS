FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl git build-essential libssl-dev libffi-dev \
        portaudio19-dev libespeak-ng1 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs

CMD ["python", "main.py"]
