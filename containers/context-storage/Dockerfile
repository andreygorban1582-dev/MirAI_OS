# ─── Context Storage  –  PostgreSQL optimised for 128 GB context ──────────────
FROM postgres:16-bookworm

# Install pgvector extension for semantic search
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-16-pgvector \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Optimised postgresql.conf for large RAM (128 GB context store)
COPY postgresql.conf /etc/postgresql/postgresql.conf

ENV POSTGRES_DB=mirai_context
ENV PGDATA=/var/lib/postgresql/data

EXPOSE 5432
