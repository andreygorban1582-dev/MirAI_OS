FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        uvicorn[standard] \
        fastapi \
        pydantic \
        httpx \
        redis \
        python-dotenv \
        python-telegram-bot==21.6

COPY orchestrator.py .

RUN mkdir -p /app/data/mods

EXPOSE 8080

CMD ["python", "orchestrator.py"]
