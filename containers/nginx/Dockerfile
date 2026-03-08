FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

# Generate self-signed TLS cert (replace with real cert in production)
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:4096 \
        -keyout /etc/nginx/ssl/mirai.key \
        -out    /etc/nginx/ssl/mirai.crt \
        -subj "/C=US/ST=State/L=City/O=MirAI/CN=mirai.local"

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80 443
