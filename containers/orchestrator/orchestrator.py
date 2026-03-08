"""
MirAI_OS Orchestrator
FastAPI service that connects to Ollama (LLM), Redis, PostgreSQL,
and optionally a Telegram bot.
"""

import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dolphin-mistral")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_in_production")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mirai.orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# LLM Client  (Ollama → OpenRouter fallback)
# ─────────────────────────────────────────────────────────────────────────────


class LLMClient:
    """Send a prompt to Ollama; fall back to OpenRouter on failure."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120.0)

    async def chat(self, prompt: str, system: str = "", history: Optional[list] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for msg in (history or []):
            messages.append(msg)
        messages.append({"role": "user", "content": prompt})

        # Try Ollama first
        try:
            reply = await self._ollama_chat(messages)
            return reply
        except Exception as exc:
            log.warning("Ollama failed (%s), falling back to OpenRouter", exc)

        # Fall back to OpenRouter
        if OPENROUTER_API_KEY:
            try:
                return await self._openrouter_chat(messages)
            except Exception as exc2:
                log.error("OpenRouter also failed: %s", exc2)

        raise RuntimeError("All LLM backends failed. Check Ollama and OPENROUTER_API_KEY.")

    async def _ollama_chat(self, messages: list) -> str:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]

    async def _openrouter_chat(self, messages: list) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "nousresearch/nous-hermes-2-mistral-7b-dpo",
            "messages": messages,
        }
        resp = await self._http.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            resp = await self._http.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._http.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# App lifecycle
# ─────────────────────────────────────────────────────────────────────────────

llm_client: LLMClient
redis_client: aioredis.Redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global llm_client, redis_client

    log.info("Starting MirAI_OS Orchestrator…")

    llm_client = LLMClient()
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    # Check Ollama availability
    available = await llm_client.is_available()
    if available:
        log.info("Ollama is reachable at %s (model: %s)", OLLAMA_HOST, OLLAMA_MODEL)
    else:
        log.warning(
            "Ollama not reachable at %s – will retry on first request", OLLAMA_HOST
        )

    # Start Telegram bot if token provided
    if TELEGRAM_TOKEN:
        asyncio.create_task(_start_telegram_bot())

    yield

    # Cleanup
    await llm_client.close()
    await redis_client.aclose()
    log.info("Orchestrator shut down cleanly.")


app = FastAPI(title="MirAI_OS Orchestrator", version="1.0.0", lifespan=lifespan)

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    system: str = (
        "You are Okabe Rintaro, a mad scientist AI assistant known as MirAI. "
        "You are helpful, brilliant, and slightly dramatic."
    )


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model: str


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    ollama_ok = await llm_client.is_available()
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "ok" if (ollama_ok and redis_ok) else "degraded"
    return JSONResponse(
        {
            "status": status,
            "ollama": ollama_ok,
            "redis": redis_ok,
            "model": OLLAMA_MODEL,
        }
    )


@app.get("/")
async def root():
    return {"name": "MirAI_OS Orchestrator", "version": "1.0.0", "status": "running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Load conversation history from Redis
    history_key = f"history:{req.session_id}"
    raw = await redis_client.lrange(history_key, 0, -1)  # list of JSON strings
    history = [json.loads(m) for m in raw]

    # Call LLM
    try:
        reply = await llm_client.chat(req.message, system=req.system, history=history)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Persist conversation turn
    await redis_client.rpush(history_key, json.dumps({"role": "user", "content": req.message}))
    await redis_client.rpush(history_key, json.dumps({"role": "assistant", "content": reply}))
    await redis_client.ltrim(history_key, -80, -1)  # keep last 40 turns (80 entries)

    return ChatResponse(reply=reply, session_id=req.session_id, model=OLLAMA_MODEL)


@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    await redis_client.delete(f"history:{session_id}")
    return {"cleared": session_id}


@app.get("/models")
async def list_models():
    """List models available in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Optional Telegram Bot
# ─────────────────────────────────────────────────────────────────────────────


async def _start_telegram_bot() -> None:
    """Run a simple Telegram bot that forwards messages to the /chat endpoint."""
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

        async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            await update.message.reply_text(
                "Hahaha! I am Okabe Rintaro – MirAI, the mad scientist AI. "
                "Ask me anything, Lab Member!"
            )

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            session_id = str(update.effective_chat.id)
            user_text = update.message.text or ""
            if not user_text.strip():
                return

            await update.message.chat.send_action("typing")

            # Load history from Redis
            history_key = f"history:tg:{session_id}"
            raw = await redis_client.lrange(history_key, 0, -1)
            history = [json.loads(m) for m in raw]

            try:
                reply = await llm_client.chat(user_text, history=history)
            except Exception as exc:
                reply = f"El Psy Kongroo... an error occurred: {exc}"

            # Persist
            await redis_client.rpush(
                history_key, json.dumps({"role": "user", "content": user_text})
            )
            await redis_client.rpush(
                history_key, json.dumps({"role": "assistant", "content": reply})
            )
            await redis_client.ltrim(history_key, -80, -1)

            await update.message.reply_text(reply)

        tg_app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .build()
        )
        tg_app.add_handler(CommandHandler("start", start_cmd))
        tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        log.info("Telegram bot starting…")
        await tg_app.run_polling(close_loop=False)
    except Exception as exc:
        log.error("Telegram bot failed to start: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("orchestrator:app", host="0.0.0.0", port=8080, reload=False)
