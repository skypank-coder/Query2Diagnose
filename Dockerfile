# Query2Diagnose: API + website in one image.
#   docker compose up --build        -> http://localhost:8000

FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/app/.cache/hf
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY pyproject.toml README.md ./
COPY core core
COPY bench bench
COPY eval eval
COPY sim sim
COPY systems systems
COPY api api
RUN pip install --no-cache-dir -e .
COPY configs configs
COPY data data
COPY results results
COPY --from=web /web/dist web/dist
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
