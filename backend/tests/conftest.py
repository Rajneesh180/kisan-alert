import os

# Tests exercise the deterministic floor: force the LLM offline even when a
# real key exists in .env (env vars take precedence over the dotenv file).
os.environ["GEMINI_API_KEY"] = ""
