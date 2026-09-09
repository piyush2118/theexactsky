#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v resvg >/dev/null 2>&1; then
  echo "check-render: UNVERIFIED — resvg is not installed" >&2
  exit 2
fi

cd "$ROOT/engine"
uv run pytest -q tests/test_render.py -rs

echo "check-render: PASS"
