FROM python:3.14-slim-bookworm

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY edges/syringequbot/ ./edges/syringequbot/
COPY driver/ ./driver/

WORKDIR /app/edges/syringequbot
RUN uv sync --frozen --no-dev --no-install-project --package syringequbot-edge

ENV PYTHONPATH=/app/edges/syringequbot:/app/driver/src
CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
