# Build from this repo. Ingredients stay in qubot-submodules and are not copied into git.
# docker build -f miniqubot-edge/Dockerfile \
#   --build-context ingredients=../qubot-submodules \
#   --build-arg CONTRACT_VERSION=1 \
#   -t ghcr.io/pudap/miniqubot-edge:1 .

FROM python:3.14-slim-bookworm

WORKDIR /src/qubot-modules
ENV UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ingredients / /src/qubot-submodules
COPY pyproject.toml uv.lock ./
COPY miniqubot-edge ./miniqubot-edge

RUN uv sync --frozen --no-dev --no-install-project --package miniqubot-edge

ARG CONTRACT_VERSION=1
ENV CONTRACT_VERSION=${CONTRACT_VERSION} \
    PYTHONPATH=/src/qubot-modules/miniqubot-edge
WORKDIR /src/qubot-modules/miniqubot-edge
CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
