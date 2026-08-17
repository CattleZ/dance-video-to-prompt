#!/usr/bin/env bash
# 视频音轨节奏分析（BPM / 拍点 / 能量）→ rhythm_analysis.json + rhythm_brief.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 2 ]]; then
  echo "用法: bash scripts/analyze_rhythm.sh <视频路径> <输出目录 OUT_DIR>"
  exit 1
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON" "$ROOT/src/analyze_rhythm.py" "$1" -o "$2"
