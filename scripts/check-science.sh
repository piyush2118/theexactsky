#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT/engine"
uv run pytest -q \
  tests/test_time.py \
  tests/test_sidereal.py \
  tests/test_ephem.py \
  tests/test_stars_sky.py \
  tests/test_claims.py \
  tests/test_reference.py \
  -rs

echo "check-science: command completed. Inspect the pytest summary: skipped reference tests are UNVERIFIED, not PASS."
