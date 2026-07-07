FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY backend/ backend/
COPY data/ data/
COPY pipeline/ pipeline/
COPY --from=frontend /build/dist frontend/dist

# The container runs as a non-root user with a read-only home on Cloud Run and
# HF Spaces. Keep the two runtime writes (SQLite, uploaded photos) under /tmp,
# and point HOME there so any library cache has somewhere to write.
ENV DB_PATH=/tmp/kisan.db \
    UPLOADS_DIR=/tmp/kisan-uploads \
    HOME=/tmp

# Invoke the venv built above directly. `uv run` would re-check the lockfile and
# touch a uv cache under HOME at start-up, which stalls on a read-only home.
EXPOSE 8000
CMD [".venv/bin/uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
