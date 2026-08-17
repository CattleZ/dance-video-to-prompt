#!/usr/bin/env bash
# 安装本地依赖（抽帧需要 opencv + pillow；API 模式额外需要 httpx）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="python3"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "未找到 python3"
  exit 1
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  "$PYTHON" -m venv "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

PIP_INDEX="${PIP_INDEX_URL:-https://pypi.org/simple}"
pip install -U pip -i "$PIP_INDEX"
pip install -r "$ROOT/requirements.txt" -i "$PIP_INDEX"

if ! python -c "import cv2" 2>/dev/null; then
  pip install opencv-python-headless -i "$PIP_INDEX"
fi

if [[ ! -f "$ROOT/config/settings.env" ]]; then
  cp "$ROOT/config/settings.example.env" "$ROOT/config/settings.env"
  echo "已生成 config/settings.env（仅 API 模式需要填写 VISION_MODEL）"
fi

chmod +x "$ROOT/scripts/"*.sh 2>/dev/null || true

echo "安装完成。"
echo "Skill/Agent 模式: bash scripts/extract_frames.sh /path/to/video.mp4"
echo "API 模式:         bash scripts/analyze_api.sh /path/to/video.mp4"
