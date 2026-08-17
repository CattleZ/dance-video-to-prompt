#!/usr/bin/env bash
# 共用：只抽帧，不调用任何模型 API（Skill 版 / API 版都依赖此脚本）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  echo "用法: bash scripts/extract_frames.sh <视频路径> [--interval 0.33] [--max-frames 36] [-o 输出目录]"
  exit 1
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON" "$ROOT/src/main.py" "$@" --mode agent
