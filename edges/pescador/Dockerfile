FROM python:3.14-slim-bookworm

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y \
  build-essential \
  udev \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

COPY edges/pescador/ ./edges/pescador/
COPY driver/ ./driver/

WORKDIR /app/edges/pescador
RUN uv sync --frozen --no-dev --no-install-project --package pescador-pipqubot-edge

ENV PYTHONPATH=/app/edges/pescador:/app/driver/src

CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
