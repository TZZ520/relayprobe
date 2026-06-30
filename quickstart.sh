#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
OUT="$ROOT/artifacts/quickstart"
echo "relayprobe quickstart"
echo "Project root: $ROOT"
echo "Output: $OUT"
python -m relayprobe quickstart --out "$OUT"
