"""RAG retrieval over ICAR/TNAU package-of-practices text.

Chunks are loaded from data/knowledge/practices.json at boot and embedded with
Gemini's text-embedding-004 model. At query time the farmer's question is
embedded and the top-k most relevant passages are injected into the advisory
prompt, so Gemini answers from authoritative agronomic text rather than
parametric memory alone.

Degrades silently: without an API key or on embedding failure, the advisory
still works — it just uses the existing deterministic grounding context.
"""

from __future__ import annotations

import json
import math

from ..config import settings

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

EMBED_MODEL = "text-embedding-004"
TOP_K = 3

_chunks: list[dict] = []
_embeddings: list[list[float]] = []
_client = None


def _get_client():
    global _client
    if _client is None and genai is not None and settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def load_knowledge() -> None:
    """Load and embed the knowledge base. Called once at boot."""
    global _chunks, _embeddings
    kb_path = settings.data_dir / "knowledge" / "practices.json"
    if not kb_path.exists():
        return
    _chunks = json.loads(kb_path.read_text())
    cl = _get_client()
    if cl is None or not _chunks:
        return
    texts = [c["text"] for c in _chunks]
    try:
        result = cl.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        _embeddings = [e.values for e in result.embeddings]
    except Exception:
        _embeddings = []


def retrieve(question: str, crop: str | None = None) -> list[str]:
    """Return the top-k most relevant practice passages for a question."""
    if not _embeddings or not _chunks:
        return []
    cl = _get_client()
    if cl is None:
        return []
    try:
        result = cl.models.embed_content(
            model=EMBED_MODEL,
            contents=[question],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        q_emb = result.embeddings[0].values
    except Exception:
        return []

    scored = []
    for i, (chunk, emb) in enumerate(zip(_chunks, _embeddings, strict=True)):
        sim = _cosine(q_emb, emb)
        if crop and chunk.get("crop") and chunk["crop"] != crop:
            sim *= 0.7
        scored.append((sim, i))
    scored.sort(reverse=True)
    return [_chunks[i]["text"] for _, i in scored[:TOP_K]]
