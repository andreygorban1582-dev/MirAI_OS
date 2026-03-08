# ─── Agentverse: Next.js + Open WebUI (Ollama front-end) ─────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install Open WebUI (a polished Next.js/SvelteKit Ollama interface)
# We clone the official open-webui which gives us a full Agentverse UI
RUN apk add --no-cache git python3 make g++ && \
    git clone --depth 1 https://github.com/open-webui/open-webui.git /app

# Install dependencies and build
RUN npm ci --legacy-peer-deps && \
    OLLAMA_BASE_URL=http://ollama:11434 npm run build

# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

CMD ["node", "server.js"]
