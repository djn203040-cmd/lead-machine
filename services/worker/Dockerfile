# Lead Machine worker — container for the worker host (Fly.io / Railway).
#
# The pipeline runs as CLI commands (`leadmachine discover|qualify|...`). This
# image gives you a long-lived box you can `exec`/cron into. Scrapling's
# StealthyFetcher (the documented escalation for hard anti-bot sites) needs a
# real browser; it is NOT a base dependency, so install it on the host only if
# you need it — see the commented block below.

FROM python:3.11-slim

# uv for fast, locked installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first (cache layer), then the project.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# --- optional: Scrapling browser fetch (uncomment when a host needs it) ------
# RUN uv pip install scrapling && python -m scrapling install
# (Scrapling pulls Playwright/Camoufox; this adds a browser + system libs.)
# -----------------------------------------------------------------------------

# Default to the smoke test; the host/cron overrides the whole command, e.g.
#   docker run --env-file .env <image> leadmachine discover -b 960210 -p 2200
# NB: no ENTRYPOINT — fly.toml's `[processes] app = "sleep infinity"` must fully
# replace the command to keep the box alive; an ENTRYPOINT would prepend
# `leadmachine` and turn it into `leadmachine sleep infinity` (exits instantly).
CMD ["leadmachine", "hello"]
