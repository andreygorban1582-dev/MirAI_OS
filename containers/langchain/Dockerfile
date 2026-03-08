FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir \
        uvicorn[standard] \
        fastapi \
        pydantic \
        langchain==0.2.16 \
        langchain-community==0.2.16 \
        langchain-core==0.2.38 \
        langchain-ollama==0.1.3 \
        chromadb==0.5.5 \
        sentence-transformers==3.1.1 \
        torch --index-url https://download.pytorch.org/whl/cpu \
        redis

COPY server.py .

RUN mkdir -p /app/data

EXPOSE 8100

CMD ["python", "server.py"]
