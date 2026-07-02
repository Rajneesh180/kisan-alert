"""Minimal Twilio Messaging gateway over the REST API (no SDK dependency).

Optional: when TWILIO_ACCOUNT_SID/AUTH_TOKEN are set the app can send real
WhatsApp/SMS via the Twilio sandbox; otherwise the in-app simulator covers the
same flow. Inbound webhooks return TwiML regardless.
"""

from xml.sax.saxutils import escape

import httpx

from ..config import settings

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def available() -> bool:
    return bool(settings.twilio_account_sid and settings.twilio_auth_token)


def twiml(message: str) -> str:
    body = f"<Response><Message>{escape(message)}</Message></Response>"
    return f'<?xml version="1.0" encoding="UTF-8"?>{body}'


def send_message(to: str, body: str) -> dict:
    """Send an outbound message. `to` may be a bare number or 'whatsapp:+91...'."""
    if not available():
        raise RuntimeError("twilio not configured")
    from_ = settings.twilio_from
    # Match channel: if sending from a whatsapp: sender, the recipient needs it too.
    if from_.startswith("whatsapp:") and not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"
    resp = httpx.post(
        API.format(sid=settings.twilio_account_sid),
        data={"From": from_, "To": to, "Body": body},
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"sid": data.get("sid"), "status": data.get("status"), "to": to}
