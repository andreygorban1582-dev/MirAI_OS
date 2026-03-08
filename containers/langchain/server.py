"""
MirAI_OS  –  LangChain rolling-context API server
• Sentence-Transformer embeddings
• ChromaDB persistent vector store
• Rolling 128 k-token context window
• REST API for orchestrator
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationTokenBufferMemory
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mirai.langchain")

# ─── Configuration ─────────────────────────────────────────────────────────────
CHROMA_URL       = os.getenv("CHROMA_URL",    "http://chromadb:8000")
CHROMA_TOKEN     = os.getenv("CHROMA_TOKEN",  "")
OLLAMA_URL       = os.getenv("OLLAMA_URL",    "http://ollama:11434")
REDIS_URL        = os.getenv("REDIS_URL",     "redis://redis:6379")
CONTEXT_WINDOW   = int(os.getenv("CONTEXT_WINDOW", "128000"))
EMBED_MODEL      = os.getenv("EMBED_MODEL",   "all-MiniLM-L6-v2")
DATA_DIR         = os.getenv("DATA_DIR",      "/app/data")

app = FastAPI(title="MirAI LangChain API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Embeddings (sentence-transformers) ────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# ─── ChromaDB vector store ────────────────────────────────────────────────────
import chromadb
from chromadb.config import Settings

chroma_client = chromadb.HttpClient(
    host=CHROMA_URL.replace("http://", "").split(":")[0],
    port=int(CHROMA_URL.split(":")[-1]),
    settings=Settings(
        chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
        chroma_client_auth_credentials=CHROMA_TOKEN,
    ) if CHROMA_TOKEN else Settings(),
)

vectorstore = Chroma(
    client=chroma_client,
    collection_name="mirai_context",
    embedding_function=embeddings,
)

# ─── LLM (Ollama) ─────────────────────────────────────────────────────────────
llm = Ollama(base_url=OLLAMA_URL, model="nous-hermes-2-mistral-7b-dpo")

# ─── Rolling-context memory ───────────────────────────────────────────────────
memory = ConversationTokenBufferMemory(
    llm=llm,
    max_token_limit=CONTEXT_WINDOW,
    memory_key="chat_history",
    return_messages=True,
    output_key="answer",
)

# ─── Retrieval chain ──────────────────────────────────────────────────────────
chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 10}),
    memory=memory,
    return_source_documents=True,
    output_key="answer",
)


# ─── Request / response models ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class IngestRequest(BaseModel):
    text: str
    metadata: Optional[dict] = {}


class ChatResponse(BaseModel):
    answer: str
    sources: list


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "context_window": CONTEXT_WINDOW}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = chain.invoke({"question": req.message})
        sources = [
            doc.metadata for doc in result.get("source_documents", [])
        ]
        return ChatResponse(answer=result["answer"], sources=sources)
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ingest")
async def ingest(req: IngestRequest) -> dict:
    """Store a text chunk in the rolling vector context."""
    try:
        vectorstore.add_texts([req.text], metadatas=[req.metadata])
        return {"status": "ingested", "chars": len(req.text)}
    except Exception as exc:
        logger.error("Ingest error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/context")
async def clear_context() -> dict:
    """Wipe in-memory conversation history (vector store is kept)."""
    memory.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
