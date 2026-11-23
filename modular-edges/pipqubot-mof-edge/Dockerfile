# Build from this repo. Ingredients stay in qubot-submodules and are not copied into git.
# docker build -f pipqubot-mof-edge/Dockerfile \
#   --build-context ingredients=../qubot-submodules \
#   --build-arg CONTRACT_VERSION=1 \
#   -t ghcr.io/pudap/pipqubot-mof-edge:1 .

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
COPY pipqubot-mof-edge ./pipqubot-mof-edge

RUN uv sync --frozen --no-dev --no-install-project --package pipqubot-mof-edge

ARG CONTRACT_VERSION=1
ENV CONTRACT_VERSION=${CONTRACT_VERSION} \
    PYTHONPATH=/src/qubot-modules/pipqubot-mof-edge
WORKDIR /src/qubot-modules/pipqubot-mof-edge
CMD ["uv", "run", "--frozen", "--no-sync", "python", "main.py"]
