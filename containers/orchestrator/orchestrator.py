"""
MirAI_OS  –  Orchestrator Container
• Nous-Hermes-2-Mistral-7B-DPO via Ollama
• Multi-agent persona routing
• Mod loader (Mod 2)
• REST + WebSocket API for Agentverse / Telegram
• Integrates: LangChain, Whisper, CSM, Redis, N8n, Flowise
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
import os
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s – %(message)s",
)
logger = logging.getLogger("mirai.orchestrator")

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://ollama:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL",  "nous-hermes-2-mistral-7b-dpo")
REDIS_URL     = os.getenv("REDIS_URL",     "redis://redis:6379")
CHROMA_URL    = os.getenv("CHROMA_URL",    "http://chromadb:8000")
CHROMA_TOKEN  = os.getenv("CHROMA_TOKEN",  "")
LANGCHAIN_URL = os.getenv("LANGCHAIN_URL", "http://langchain:8100")
N8N_URL       = os.getenv("N8N_URL",       "http://n8n:5678")
CSM_URL       = os.getenv("CSM_URL",       "http://csm:8300")
WHISPER_URL   = os.getenv("WHISPER_URL",   "http://whisper:8400")
TG_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "")
OR_API_KEY    = os.getenv("OPENROUTER_API_KEY", "")
DATA_DIR      = Path(os.getenv("DATA_DIR", "/app/data"))
MODS_DIR      = DATA_DIR / "mods"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODS_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Persona / Ability system  (Mod 2 additions marked ★)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Ability:
    name: str
    description: str
    handler: Optional[Callable] = None

    async def execute(self, args: dict, ctx: dict) -> str:
        if self.handler:
            return await self.handler(args, ctx)
        return f"[{self.name}] executed"


@dataclass
class Persona:
    name: str
    system_prompt: str
    abilities: list[Ability] = field(default_factory=list)
    model_override: Optional[str] = None  # ★ Mod2: per-persona model


PERSONAS: dict[str, Persona] = {
    "mirai": Persona(
        name="MirAI",
        system_prompt=(
            "You are MirAI – an advanced AI operating system assistant. "
            "You coordinate multiple specialist agents, manage infrastructure, "
            "and help your user accomplish any technical or creative task. "
            "Be concise, helpful, and technically precise."
        ),
    ),
    "okabe": Persona(
        name="Okabe Rintaro",
        system_prompt=(
            "You are Okabe Rintaro, the self-proclaimed mad scientist from Steins;Gate. "
            "You speak dramatically, reference the 'Organization', and call yourself "
            "'Hououin Kyouma'. You are brilliant but theatrical."
        ),
    ),
    "wrench": Persona(
        name="Wrench",
        system_prompt=(
            "You are Wrench, a DedSec hacker from Watch Dogs 2. "
            "Expert in code generation, exploit development, and social engineering. "
            "Speak with hacker slang. Generate working code when asked."
        ),
        abilities=[
            Ability("code_gen", "Generate exploit / utility code"),
            Ability("network_scan", "Trigger nmap/nuclei via Kali container"),
        ],
    ),
    "kurisu": Persona(
        name="Kurisu Makise",
        system_prompt=(
            "You are Kurisu Makise, a genius neuroscientist from Steins;Gate. "
            "Expert in physics, chemistry, and AI. You're tsundere but insightful. "
            "Provide detailed scientific explanations."
        ),
    ),
    # ★ Mod 2: new orchestration persona
    "hermes": Persona(
        name="Hermes",
        system_prompt=(
            "You are Hermes, the internal routing intelligence of MirAI_OS. "
            "You analyse incoming requests and route them to the optimal sub-agent, "
            "tool, or external service. Reply with concise JSON action plans."
        ),
        model_override="nous-hermes-2-mistral-7b-dpo",
    ),
    # ★ Mod 2: dark-web research persona
    "robin": Persona(
        name="Robin",
        system_prompt=(
            "You are Robin, MirAI's dark-web intelligence analyst. "
            "You route research queries through the Tor network, summarise findings, "
            "and flag security risks. You never reveal illegal methodology."
        ),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Mod loader  (Mod 2 – enhanced with dependency injection & hot-reload)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Mod:
    name: str
    version: str
    module: types.ModuleType

    async def setup(self, bot: Any, llm: Any, ctx: dict) -> None:
        if hasattr(self.module, "setup"):
            try:
                result = self.module.setup(bot, llm, ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[mod:%s] setup error: %s", self.name, exc)

    async def on_message(self, message: str, ctx: dict) -> Optional[str]:
        if hasattr(self.module, "on_message"):
            try:
                result = self.module.on_message(message, ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as exc:
                logger.error("[mod:%s] on_message error: %s", self.name, exc)
        return None

    # ★ Mod 2: new lifecycle hook
    async def on_startup(self, ctx: dict) -> None:
        if hasattr(self.module, "on_startup"):
            try:
                result = self.module.on_startup(ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[mod:%s] on_startup error: %s", self.name, exc)

    # ★ Mod 2: new lifecycle hook
    async def on_shutdown(self, ctx: dict) -> None:
        if hasattr(self.module, "on_shutdown"):
            try:
                result = self.module.on_shutdown(ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[mod:%s] on_shutdown error: %s", self.name, exc)


class ModLoader:
    """Discovers, loads, and hot-reloads Python mods from a directory."""

    def __init__(self) -> None:
        self._mods: dict[str, Mod] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def load_file(self, path: str | Path) -> Optional[Mod]:
        path = Path(path)
        if not path.exists():
            logger.warning("[ModLoader] file not found: %s", path)
            return None
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("[ModLoader] failed to load %s: %s", path, exc)
            return None
        mod = Mod(
            name=getattr(module, "MOD_NAME", path.stem),
            version=getattr(module, "MOD_VERSION", "0.0.0"),
            module=module,
        )
        self._mods[mod.name] = mod
        logger.info("[ModLoader] loaded mod '%s' v%s", mod.name, mod.version)
        return mod

    def load_directory(self, directory: str | Path) -> list[Mod]:
        directory = Path(directory)
        loaded: list[Mod] = []
        for py_file in sorted(directory.glob("*.py")):
            mod = self.load_file(py_file)
            if mod:
                loaded.append(mod)
        return loaded

    # ★ Mod 2: hot-reload support
    def reload(self, mod_name: str) -> bool:
        mod = self._mods.get(mod_name)
        if mod is None:
            return False
        try:
            importlib.reload(mod.module)
            logger.info("[ModLoader] reloaded mod '%s'", mod_name)
            return True
        except Exception as exc:
            logger.error("[ModLoader] reload failed for '%s': %s", mod_name, exc)
            return False

    @property
    def mods(self) -> list[Mod]:
        return list(self._mods.values())

    async def dispatch_message(self, message: str, ctx: dict) -> Optional[str]:
        for mod in self.mods:
            result = await mod.on_message(message, ctx)
            if result is not None:
                return result
        return None

    async def startup_all(self, ctx: dict) -> None:
        for mod in self.mods:
            await mod.on_startup(ctx)

    async def shutdown_all(self, ctx: dict) -> None:
        for mod in self.mods:
            await mod.on_shutdown(ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM client  (Ollama-first, OpenRouter fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class LLMClient:

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120)

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        m = model or OLLAMA_MODEL
        try:
            return await self._ollama_chat(messages, m)
        except Exception as exc:
            logger.warning("[LLM] Ollama failed (%s), trying OpenRouter", exc)
            if OR_API_KEY:
                return await self._openrouter_chat(messages, m)
            raise

    async def _ollama_chat(self, messages: list[dict], model: str) -> str:
        resp = await self._http.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def _openrouter_chat(self, messages: list[dict], model: str) -> str:
        resp = await self._http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_API_KEY}"},
            json={"model": model, "messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._http.aclose()


# ═══════════════════════════════════════════════════════════════════════════════
# Context manager  (Redis-backed, rolling window)
# ═══════════════════════════════════════════════════════════════════════════════

class ContextManager:

    def __init__(self, redis_url: str, max_messages: int = 50) -> None:
        self._redis_url = redis_url
        self._max = max_messages
        self._r: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._r = await aioredis.from_url(
            self._redis_url, decode_responses=True
        )
        logger.info("[Context] Redis connected")

    async def push(self, session: str, role: str, content: str) -> None:
        if self._r is None:
            return
        import json
        key = f"mirai:ctx:{session}"
        await self._r.rpush(key, json.dumps({"role": role, "content": content}))
        await self._r.ltrim(key, -self._max, -1)

    async def get(self, session: str) -> list[dict]:
        if self._r is None:
            return []
        import json
        key = f"mirai:ctx:{session}"
        raw = await self._r.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]

    async def clear(self, session: str) -> None:
        if self._r is None:
            return
        await self._r.delete(f"mirai:ctx:{session}")


# ═══════════════════════════════════════════════════════════════════════════════
# ★ Mod 2: LangChain integration helper
# ═══════════════════════════════════════════════════════════════════════════════

class LangChainProxy:

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120)

    async def chat(self, message: str, session: str = "default") -> str:
        try:
            resp = await self._http.post(
                f"{LANGCHAIN_URL}/chat",
                json={"message": message, "session_id": session},
            )
            resp.raise_for_status()
            return resp.json().get("answer", "")
        except Exception as exc:
            logger.error("[LangChain] chat error: %s", exc)
            return ""

    async def ingest(self, text: str, metadata: dict | None = None) -> bool:
        try:
            resp = await self._http.post(
                f"{LANGCHAIN_URL}/ingest",
                json={"text": text, "metadata": metadata or {}},
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._http.aclose()


# ═══════════════════════════════════════════════════════════════════════════════
# ★ Mod 2: Speech helpers (CSM + Whisper)
# ═══════════════════════════════════════════════════════════════════════════════

class SpeechProxy:

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120)

    async def speak(self, text: str) -> bytes:
        """Returns WAV audio bytes from CSM."""
        try:
            resp = await self._http.post(
                f"{CSM_URL}/speak", json={"text": text}
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.error("[Speech] TTS error: %s", exc)
            return b""

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Returns transcribed text from faster-whisper."""
        try:
            resp = await self._http.post(
                f"{WHISPER_URL}/transcribe",
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")
        except Exception as exc:
            logger.error("[Speech] STT error: %s", exc)
            return ""

    async def close(self) -> None:
        await self._http.aclose()


# ═══════════════════════════════════════════════════════════════════════════════
# MirAI Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class MirAIOrchestrator:

    def __init__(self) -> None:
        self.llm      = LLMClient()
        self.ctx_mgr  = ContextManager(REDIS_URL)
        self.loader   = ModLoader()
        self.langchain = LangChainProxy()
        self.speech   = SpeechProxy()
        self._persona  = "mirai"

    @property
    def persona(self) -> Persona:
        return PERSONAS.get(self._persona, PERSONAS["mirai"])

    def switch_persona(self, name: str) -> bool:
        if name in PERSONAS:
            self._persona = name
            logger.info("[Orchestrator] switched persona → %s", name)
            return True
        return False

    async def startup(self) -> None:
        await self.ctx_mgr.connect()
        self.loader.load_directory(MODS_DIR)
        ctx = {"orchestrator": self, "personas": PERSONAS}
        await self.loader.startup_all(ctx)
        # Pull the Nous-Hermes model if not present
        asyncio.create_task(self._pull_model())
        logger.info("[Orchestrator] started. Model: %s", OLLAMA_MODEL)

    async def _pull_model(self) -> None:
        async with httpx.AsyncClient(timeout=600) as client:
            try:
                logger.info("[Orchestrator] Checking model %s …", OLLAMA_MODEL)
                r = await client.post(
                    f"{OLLAMA_URL}/api/pull",
                    json={"name": OLLAMA_MODEL, "stream": False},
                )
                r.raise_for_status()
                logger.info("[Orchestrator] Model ready.")
            except Exception as exc:
                logger.warning("[Orchestrator] Could not pull model: %s", exc)

    async def process(
        self, message: str, session: str = "default"
    ) -> str:
        # 1. Let mods intercept first
        mod_reply = await self.loader.dispatch_message(
            message, {"session": session, "persona": self._persona}
        )
        if mod_reply is not None:
            return mod_reply

        # 2. Push user message into rolling context
        await self.ctx_mgr.push(session, "user", message)

        # 3. Retrieve context window
        history = await self.ctx_mgr.get(session)

        # 4. Build messages
        messages = [
            {"role": "system", "content": self.persona.system_prompt},
            *history,
        ]

        # 5. Query LLM
        model = self.persona.model_override or OLLAMA_MODEL
        reply = await self.llm.chat(messages, model=model)

        # 6. Store assistant reply in context
        await self.ctx_mgr.push(session, "assistant", reply)

        # 7. Ingest exchange into LangChain for long-term retrieval
        asyncio.create_task(
            self.langchain.ingest(
                f"User: {message}\nAssistant: {reply}",
                {"session": session, "persona": self._persona},
            )
        )

        return reply

    async def shutdown(self) -> None:
        await self.loader.shutdown_all({})
        await self.llm.close()
        await self.langchain.close()
        await self.speech.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI application
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="MirAI Orchestrator", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_orchestrator: Optional[MirAIOrchestrator] = None


@app.on_event("startup")
async def _startup() -> None:
    global _orchestrator
    _orchestrator = MirAIOrchestrator()
    await _orchestrator.startup()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _orchestrator:
        await _orchestrator.shutdown()


def _get_orc() -> MirAIOrchestrator:
    if _orchestrator is None:
        raise HTTPException(503, "Orchestrator not ready")
    return _orchestrator


# ─── REST endpoints ───────────────────────────────────────────────────────────

class ChatReq(BaseModel):
    message: str
    session: str = "default"
    persona: Optional[str] = None


class ChatResp(BaseModel):
    reply: str
    persona: str
    session: str


class PersonaSwitchReq(BaseModel):
    name: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "model": OLLAMA_MODEL}


@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq) -> ChatResp:
    orc = _get_orc()
    if req.persona:
        orc.switch_persona(req.persona)
    reply = await orc.process(req.message, req.session)
    return ChatResp(reply=reply, persona=orc.persona.name, session=req.session)


@app.post("/persona/switch")
async def switch_persona(req: PersonaSwitchReq) -> dict:
    orc = _get_orc()
    ok = orc.switch_persona(req.name)
    return {"ok": ok, "persona": req.name}


@app.get("/personas")
async def list_personas() -> dict:
    return {k: v.name for k, v in PERSONAS.items()}


@app.get("/mods")
async def list_mods() -> list[dict]:
    orc = _get_orc()
    return [{"name": m.name, "version": m.version} for m in orc.loader.mods]


@app.post("/mods/reload/{mod_name}")
async def reload_mod(mod_name: str) -> dict:
    orc = _get_orc()
    ok = orc.loader.reload(mod_name)
    return {"ok": ok}


@app.delete("/context/{session}")
async def clear_context(session: str) -> dict:
    orc = _get_orc()
    await orc.ctx_mgr.clear(session)
    return {"cleared": session}


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/{session}")
async def websocket_chat(ws: WebSocket, session: str) -> None:
    await ws.accept()
    orc = _get_orc()
    try:
        while True:
            data = await ws.receive_json()
            message = data.get("message", "")
            if not message:
                continue
            reply = await orc.process(message, session)
            await ws.send_json({"reply": reply, "persona": orc.persona.name})
    except WebSocketDisconnect:
        pass


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
