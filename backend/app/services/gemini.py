"""Gemini at the edges: Indic conversation, speech and vision only.

All agronomy numbers come from the deterministic engines; Gemini receives them
as grounding context and is instructed not to invent data. Without an API key —
or on any Gemini failure — callers get {"degraded": True} and must serve their
deterministic fallback, so the platform stays useful with zero LLM availability.
"""

import json

from ..config import settings

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - pipeline-only environments
    genai = None
    types = None

LANG_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu"}

ADVISORY_SYSTEM = (
    "You are Kisan Alert, an agricultural advisor for small farmers in Andhra Pradesh. "
    "Answer in {language}, in simple words a farmer with basic schooling understands. "
    "Maximum 120 words. Ground every number strictly in the CONTEXT JSON — never invent "
    "measurements, prices or dates. The CONTEXT may include reference_practices from "
    "ICAR/TNAU package-of-practices guides; prefer these over general knowledge for crop "
    "management advice. If the question is outside crops, water or plant health, say you "
    "can only help with farming."
)

DIAGNOSIS_SYSTEM = (
    "You are a plant-pathology assistant for Anantapur farmers. Identify the most likely "
    "problem from the photo and/or the farmer's note. Reply as JSON with keys: diagnosis "
    "(short, in {language}), confidence (number 0-1), severity (mild|moderate|severe), "
    "treatment (a single string: 2-3 practical low-cost steps in {language}, separated by "
    "newlines). Be conservative with confidence."
)

_client = None


REQUEST_TIMEOUT_MS = 30_000  # cap so a slow LLM call can't hold a request thread


def _get_client():
    global _client
    if _client is None and genai is not None and settings.gemini_api_key:
        _client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
    return _client


def available() -> bool:
    return _get_client() is not None


def ask_advisory(
    question: str | None,
    context: dict,
    lang: str,
    audio: tuple[bytes, str] | None = None,
) -> dict:
    cl = _get_client()
    if cl is None:
        return {"degraded": True}
    parts: list = []
    if audio:
        parts.append(types.Part.from_bytes(data=audio[0], mime_type=audio[1]))
    task = (
        "The farmer's question is in the attached audio. Transcribe it first, then answer. "
        'Reply as JSON: {"transcript": "...", "answer": "..."}'
        if audio
        else f"QUESTION: {question}"
    )
    parts.append(f"CONTEXT: {json.dumps(context, ensure_ascii=False)}\n\n{task}")
    try:
        resp = cl.models.generate_content(
            model=settings.gemini_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=ADVISORY_SYSTEM.format(language=LANG_NAMES.get(lang, "English")),
                response_mime_type="application/json" if audio else None,
                temperature=0.4,
            ),
        )
        if audio:
            data = json.loads(resp.text)
            return {
                "transcript": data.get("transcript"),
                "answer": data.get("answer"),
                "degraded": False,
            }
        return {"answer": resp.text, "degraded": False}
    except Exception as exc:  # noqa: BLE001 - degradation is the designed failure mode
        return {"degraded": True, "error": type(exc).__name__}


def diagnose(photo: tuple[bytes, str] | None, note: str | None, lang: str) -> dict:
    cl = _get_client()
    if cl is None:
        return {"degraded": True}
    parts: list = []
    if photo:
        parts.append(types.Part.from_bytes(data=photo[0], mime_type=photo[1]))
    if note:
        parts.append(f"Farmer note: {note}")
    try:
        resp = cl.models.generate_content(
            model=settings.gemini_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=DIAGNOSIS_SYSTEM.format(
                    language=LANG_NAMES.get(lang, "English")
                ),
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        data = json.loads(resp.text)
        treatment = data.get("treatment")
        if isinstance(treatment, list):  # model sometimes ignores the single-string ask
            treatment = "\n".join(str(step) for step in treatment)
        return {
            "diagnosis": data.get("diagnosis"),
            "confidence": float(data.get("confidence") or 0.0),
            "severity": data.get("severity"),
            "treatment": treatment,
            "degraded": False,
        }
    except Exception as exc:  # noqa: BLE001 - degradation is the designed failure mode
        return {"degraded": True, "error": type(exc).__name__}
