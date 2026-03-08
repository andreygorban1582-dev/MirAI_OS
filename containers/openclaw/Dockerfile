# ─── OpenClaw  –  Game-agent sandbox (Commander Keen engine) ─────────────────
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        cmake \
        build-essential \
        libsdl2-dev \
        libsdl2-mixer-dev \
        libsdl2-image-dev \
        libsdl2-ttf-dev \
        python3 \
        python3-pip \
        xvfb \
        x11vnc \
    && rm -rf /var/lib/apt/lists/*

# Build OpenClaw from source
RUN git clone --depth 1 https://github.com/pjasicek/OpenClaw.git /app/openclaw && \
    mkdir -p /app/openclaw/build && \
    cd /app/openclaw/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release 2>/dev/null && \
    make -j$(nproc) 2>/dev/null || echo "[openclaw] build skipped"

# AI agent REST wrapper
RUN pip3 install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        pydantic

COPY agent_api.py /app/agent_api.py

EXPOSE 8200

CMD ["python3", "/app/agent_api.py"]
