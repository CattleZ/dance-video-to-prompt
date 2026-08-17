#!/usr/bin/env bash
# 抽帧封装：自动定位 REPO_ROOT，不调用模型 API
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

resolve_repo_root() {
  if [[ -n "${DANCE_VIDEO_PROMPT_ROOT:-}" && -d "${DANCE_VIDEO_PROMPT_ROOT}" ]]; then
    echo "$DANCE_VIDEO_PROMPT_ROOT"
    return
  fi

  # skills/dance-video-to-prompt → 上两级为仓库根
  local cand
  cand="$(cd "$SKILL_DIR/../.." && pwd)"
  if [[ -x "$cand/scripts/extract_frames.sh" ]]; then
    echo "$cand"
    return
  fi

  # .grok/skills/dance-video-to-prompt → 上三级
  cand="$(cd "$SKILL_DIR/../../.." && pwd)"
  if [[ -x "$cand/scripts/extract_frames.sh" ]]; then
    echo "$cand"
    return
  fi

  # 默认：仓库根（skills/xxx 的上两级）
  echo "$(cd "$SKILL_DIR/../.." && pwd)"
}

REPO_ROOT="$(resolve_repo_root)"
EXTRACT="$REPO_ROOT/scripts/extract_frames.sh"

if [[ ! -f "$EXTRACT" ]]; then
  echo "错误: 找不到抽帧脚本: $EXTRACT"
  echo "请设置 DANCE_VIDEO_PROMPT_ROOT 指向项目根目录"
  exit 1
fi

exec bash "$EXTRACT" "$@"
