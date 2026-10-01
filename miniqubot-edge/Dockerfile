FROM python:3.14-slim-bookworm

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y \
  build-essential \
  udev \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY miniqubot-edge/ ./miniqubot-edge/
COPY driver/ ./driver/

WORKDIR /app/miniqubot-edge
RUN uv sync --frozen --no-dev --no-install-project --package miniqubot-edge

ENV PYTHONPATH=/app/miniqubot-edge:/app/driver/src \
    UV_CACHE_DIR=/tmp/uv-cache
CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
