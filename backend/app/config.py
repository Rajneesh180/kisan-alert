from pathlib import Path

from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    db_path: str = str(REPO_ROOT / "kisan.db")
    data_dir: Path = REPO_ROOT / "data"
    # Uploaded photos and the SQLite file are the only runtime writes. On a
    # read-only container image (Cloud Run, HF Spaces) point both at /tmp via
    # DB_PATH and UPLOADS_DIR; locally they live under the repo.
    uploads_dir: Path = REPO_ROOT / "data" / "uploads"

    # Twilio WhatsApp/SMS sandbox (optional — the in-app simulator works without it)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = "whatsapp:+14155238886"  # Twilio sandbox WhatsApp number
    # Inbound messages from unregistered numbers map to this plot (the sponsoring
    # MP's constituency, so a stage demo lands on Narasaraopet).
    default_plot_id: str = "plot-narasaraopet-01"

    model_config = {"env_file": REPO_ROOT / ".env", "extra": "ignore"}


settings = Settings()
