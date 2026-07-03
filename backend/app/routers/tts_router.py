from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..services import tts

router = APIRouter(prefix="/api", tags=["tts"])


class TtsIn(BaseModel):
    text: str
    lang: str = "en"


@router.post("/tts")
def synthesize(payload: TtsIn):
    if not tts.available():
        raise HTTPException(503, "Cloud TTS not configured")
    if payload.lang not in ("en", "hi", "te"):
        raise HTTPException(422, "lang must be en, hi or te")
    audio = tts.synthesize(payload.text, payload.lang)
    if audio is None:
        raise HTTPException(502, "TTS synthesis failed")
    return Response(content=audio, media_type="audio/wav")
