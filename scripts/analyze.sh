#!/usr/bin/env bash
# 统一入口：默认 agent 模式；可用 --mode api
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/config/settings.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/config/settings.env"
  set +a
fi

if [[ $# -lt 1 ]]; then
  echo "用法:"
  echo "  bash scripts/analyze.sh <视频>                  # 默认 agent：只抽帧+工作包"
  echo "  bash scripts/analyze.sh <视频> --mode api       # API 全自动"
  echo "  bash scripts/extract_frames.sh <视频>           # 同 agent"
  echo "  bash scripts/analyze_api.sh <视频>              # 同 api"
  exit 1
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON" "$ROOT/src/main.py" "$@"
