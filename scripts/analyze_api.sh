#!/usr/bin/env bash
# API 版：抽帧 + 视觉 API 三阶段分析 → prompt.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/config/settings.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/config/settings.env"
  set +a
fi

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

if [[ $# -lt 1 ]]; then
  echo "用法: bash scripts/analyze_api.sh <视频路径> [额外参数...]"
  echo "示例: bash scripts/analyze_api.sh ./dance.mp4"
  echo "      bash scripts/analyze_api.sh ./dance.mp4 --interval 0.25 --no-verify"
  exit 1
fi

VIDEO="$1"
shift || true

if [[ ! -f "$VIDEO" ]]; then
  echo "错误: 视频不存在: $VIDEO"
  exit 1
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export PYTHONUNBUFFERED=1
"$PYTHON" "$ROOT/src/main.py" "$VIDEO" --mode api "$@" 2>&1 | tee -a "$LOG_DIR/analyze.log"
