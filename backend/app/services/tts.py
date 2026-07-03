"""Text-to-speech via Gemini's native TTS — free AI Studio key, no billing.

Telugu and Hindi lack usable browser speechSynthesis voices on most devices, so
voice output (essential for low-literacy farmers) would otherwise fall back to
poor or missing Indic speech. Gemini 2.5 TTS covers both languages on the same
free-tier key the advisory already uses — no paid Cloud Text-to-Speech, no
billing account. It returns raw PCM, which browsers can't play, so we wrap it as
WAV. Without a key (or on any failure) callers get None -> the router returns 503
and the frontend uses browser speech as a last resort.
"""

import io
import wave

from ..config import settings

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - pipeline-only environments
    genai = None
    types = None

TTS_MODEL = "gemini-2.5-flash-preview-tts"
VOICE = "Kore"  # warm female voice; Gemini detects the language from the script
SAMPLE_RATE = 24000  # Gemini TTS emits 24 kHz 16-bit mono PCM

_client = None


def _get_client():
    global _client
    if _client is None and genai is not None and settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def available() -> bool:
    return _get_client() is not None


def _to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def synthesize(text: str, lang: str) -> bytes | None:
    """Return WAV audio bytes, or None if TTS is unavailable. Language is inferred
    from the text's script, so `lang` is accepted for the API but not required."""
    cl = _get_client()
    if cl is None or not text:
        return None
    try:
        resp = cl.models.generate_content(
            model=TTS_MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
                    )
                ),
            ),
        )
        pcm = resp.candidates[0].content.parts[0].inline_data.data
        return _to_wav(pcm) if pcm else None
    except Exception:  # noqa: BLE001 - degradation to browser speech is the design
        return None
