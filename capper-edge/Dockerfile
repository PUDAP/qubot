FROM python:3.14-slim-bookworm

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

# Copy the workspace packages
COPY capper-edge/ ./capper-edge/
COPY driver/ ./driver/

# Install dependencies using uv only for this package
WORKDIR /app/capper-edge
RUN uv sync --frozen --no-dev --no-install-project --package capper-edge

ENV PYTHONPATH=/app/capper-edge:/app/driver/src

CMD ["uv", "run", "python", "main.py"]
