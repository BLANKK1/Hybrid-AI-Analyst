"""
server.py — FastAPI backend for the Hybrid AI Analyst
Run: uvicorn server:app --reload --port 8000
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from data.setup_db import setup as setup_db
from src.rag_pipeline import build_index
from src.agent import run_agent
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Hybrid AI Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id → history list
sessions: dict[str, list] = {}

# ── Startup: init DB + RAG index ─────────────────────────────────────────────
@app.on_event("startup")
def startup():
    print("🔧 Setting up database...")
    setup_db()
    print("📄 Building RAG index...")
    n = build_index()
    print(f"✅ Ready — {n} document chunks indexed")

# ── Request/Response models ───────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:    str
    session_id: str = "default"

class ChatResponse(BaseModel):
    reply:      str
    route:      list[str]   # e.g. ["SQL"], ["RAG"], ["SQL", "RAG"]
    sql_queries: list[str]
    rag_queries: list[str]
    session_id: str

# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = sessions.get(req.session_id, [])
    reply, new_history, debug = run_agent(req.message, history)
    sessions[req.session_id] = new_history

    # Build readable route labels
    tools  = debug.get("tools_called", [])
    route  = []
    if "run_sql_query"    in tools: route.append("SQL")
    if "search_documents" in tools: route.append("RAG")
    if "ask_clarification" in tools: route.append("CLARIFY")

    return ChatResponse(
        reply       = reply,
        route       = route,
        sql_queries = debug.get("sql_queries", []),
        rag_queries = debug.get("rag_queries", []),
        session_id  = req.session_id,
    )

# ── Reset session ─────────────────────────────────────────────────────────────
@app.delete("/session/{session_id}")
def reset_session(session_id: str):
    sessions.pop(session_id, None)
    return {"status": "cleared"}

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "sessions": len(sessions)}

# ── Serve frontend ────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")
