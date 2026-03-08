FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        xdotool \
        x11-apps \
        x11-utils \
        libx11-dev \
        libxtst-dev \
        scrot \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        pynput \
        pyautogui \
        pillow \
        uvicorn[standard] \
        fastapi \
        pydantic \
        python-multipart

COPY server.py .

EXPOSE 8500

CMD ["python", "server.py"]
