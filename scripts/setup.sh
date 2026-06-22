#!/usr/bin/env bash
# Dev convenience: install web + worker dependencies in one shot.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"
corepack enable >/dev/null 2>&1 || true
pnpm install
(cd services/worker && uv sync)
echo "Setup complete. Run 'pnpm dev' (web) or 'uv run leadmachine hello' (worker)."
