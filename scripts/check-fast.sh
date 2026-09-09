#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT/engine"
uv run pytest -q \
  tests/test_time.py \
  tests/test_sidereal.py \
  tests/test_ephem.py \
  tests/test_geo.py \
  tests/test_token.py \
  tests/test_claims.py \
  tests/test_stars_sky.py

cd "$ROOT/web"
uv run pytest -q

echo "check-fast: PASS"
