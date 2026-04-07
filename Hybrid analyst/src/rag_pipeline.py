"""
rag_pipeline.py
Chunks business documents → embeds them → stores in ChromaDB.
On query, retrieves the top-K most semantically relevant chunks.
"""

import os
import re
from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

DOCS_DIR    = Path(__file__).parent.parent / "documents"
CHROMA_DIR  = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION  = "business_docs"
CHUNK_SIZE  = 400          # characters per chunk
CHUNK_OVERLAP = 80         # overlap to avoid cutting mid-sentence
TOP_K       = 4            # chunks returned per query

# Load once — small, fast, free model
_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_text(text: str, size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Sliding-window character chunker."""
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        start += size - overlap
    return [c for c in chunks if len(c) > 50]   # drop tiny trailing chunks


def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION)


def build_index(force: bool = False) -> int:
    """
    Chunk + embed all .txt documents and store in ChromaDB.
    Returns number of chunks indexed.
    Skips rebuild if collection already has data (unless force=True).
    """
    col = _get_collection()
    if col.count() > 0 and not force:
        return col.count()

    model = _get_model()
    doc_paths = list(DOCS_DIR.glob("*.txt"))
    all_ids, all_docs, all_embeddings, all_meta = [], [], [], []

    chunk_idx = 0
    for path in doc_paths:
        text   = path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{path.stem}_{i}"
            embedding = model.encode(chunk).tolist()
            all_ids.append(chunk_id)
            all_docs.append(chunk)
            all_embeddings.append(embedding)
            all_meta.append({"source": path.name, "chunk_index": i})
            chunk_idx += 1

    # Upsert in batches
    batch = 100
    for i in range(0, len(all_ids), batch):
        col.upsert(
            ids        = all_ids[i:i+batch],
            documents  = all_docs[i:i+batch],
            embeddings = all_embeddings[i:i+batch],
            metadatas  = all_meta[i:i+batch],
        )

    return chunk_idx


def retrieve(query: str, top_k: int = TOP_K) -> List[dict]:
    """
    Embed the query and retrieve top_k relevant chunks from ChromaDB.
    Returns list of { text, source, score }.
    """
    model     = _get_model()
    q_embed   = model.encode(query).tolist()
    col       = _get_collection()

    results = col.query(
        query_embeddings = [q_embed],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":   doc,
            "source": meta.get("source", "unknown"),
            "score":  round(1 - dist, 3),   # convert distance → similarity
        })
    return chunks


def format_rag_result(chunks: List[dict]) -> str:
    """Format retrieved chunks as a readable context block for the LLM."""
    if not chunks:
        return "No relevant documents found."
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"[Source: {c['source']} | Relevance: {c['score']}]")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Building document index...")
    n = build_index(force=True)
    print(f"Indexed {n} chunks.")
    test = retrieve("What is the refund policy for Pro plan?")
    print(format_rag_result(test))
