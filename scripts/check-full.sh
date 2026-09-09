#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v resvg >/dev/null 2>&1; then
  echo "check-full: UNVERIFIED — resvg is required. Install the pinned/expected renderer first." >&2
  exit 2
fi

if command -v sha256sum >/dev/null 2>&1; then
  HASH_CREATE=(sha256sum)
  HASH_CHECK=(sha256sum -c)
elif command -v shasum >/dev/null 2>&1; then
  HASH_CREATE=(shasum -a 256)
  HASH_CHECK=(shasum -a 256 -c)
else
  echo "check-full: UNVERIFIED — need sha256sum or shasum for determinism verification" >&2
  exit 2
fi

required=(
  "$ROOT/engine/data/ephe/sepl_18.se1"
  "$ROOT/engine/data/_reference/de421.bsp"
  "$ROOT/engine/data/_reference/hip_bright.tsv"
)
for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "check-full: UNVERIFIED — missing required data: $path" >&2
    echo "Prepare data with the repository fetch/build scripts before treating this as a release gate." >&2
    exit 2
  fi
done

HASH_FILE="$(mktemp "${TMPDIR:-/tmp}/skurious-first.XXXXXX")"
trap 'rm -f "$HASH_FILE"' EXIT

cd "$ROOT/engine"
uv run pytest -q

cd "$ROOT/web"
uv run pytest -q

cd "$ROOT/engine"
rm -rf out
mkdir -p out

uv run sk render sky --date 2019-02-14 --time 19:30 --place 5097529 \
  --size 8x10 --names "Priya,Arjun" --occasion "Wedding night" --out render1
uv run sk claims plate data/claims/mahabharata --out render2
uv run sk conj find --bodies jupiter,saturn --from "-0007-01-01" \
  --to "-0005-12-31" --place jerusalem --calendar julian --render \
  --size 8x10 --out render3

"${HASH_CREATE[@]}" out/*.svg out/*.png > "$HASH_FILE"

uv run sk render sky --date 2019-02-14 --time 19:30 --place 5097529 \
  --size 8x10 --names "Priya,Arjun" --occasion "Wedding night" --out render1
uv run sk claims plate data/claims/mahabharata --out render2
uv run sk conj find --bodies jupiter,saturn --from "-0007-01-01" \
  --to "-0005-12-31" --place jerusalem --calendar julian --render \
  --size 8x10 --out render3

"${HASH_CHECK[@]}" "$HASH_FILE"

echo "check-full: PASS"
