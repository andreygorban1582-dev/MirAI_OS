FROM kalilinux/kali-rolling:latest

LABEL maintainer="MirAI OS — Future Gadget Lab"
LABEL description="MirAI OS — Hououin Kyouma AI Operative"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    git curl wget ffmpeg espeak-ng \
    redis-tools chromium-driver \
    nmap nikto gobuster sqlmap hydra john \
    netcat-traditional tcpdump tshark \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Playwright
RUN playwright install chromium --with-deps

# Copy source
COPY . .

# Create data dirs
RUN mkdir -p data/conversations data/vector_store data/capabilities data/sessions

CMD ["python3", "main.py"]
