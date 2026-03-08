FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        util-linux \
        procps \
        bash \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir schedule

COPY setup_swap.sh /setup_swap.sh
RUN chmod +x /setup_swap.sh

CMD ["/setup_swap.sh"]
