# ─── Robin  –  Tor dark-web SOCKS5 proxy ──────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        tor \
        torsocks \
        curl \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
        uvicorn \
        fastapi \
        httpx[socks] \
        pydantic

COPY torrc /etc/tor/torrc
COPY robin_api.py /app/robin_api.py

EXPOSE 9050 9051 8600

CMD ["/bin/bash", "-c", "tor -f /etc/tor/torrc & sleep 5 && python3 /app/robin_api.py"]
