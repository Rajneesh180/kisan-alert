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

# The container filesystem is read-only for the app user on Cloud Run and HF
# Spaces; keep the two runtime writes (SQLite, uploaded photos) under /tmp.
ENV DB_PATH=/tmp/kisan.db \
    UPLOADS_DIR=/tmp/kisan-uploads

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
