#!/usr/bin/env bash
# 节奏分析封装：定位 REPO_ROOT 后调用 scripts/analyze_rhythm.sh
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

resolve_repo_root() {
  if [[ -n "${DANCE_VIDEO_PROMPT_ROOT:-}" && -d "${DANCE_VIDEO_PROMPT_ROOT}" ]]; then
    echo "$DANCE_VIDEO_PROMPT_ROOT"
    return
  fi
  local cand
  cand="$(cd "$SKILL_DIR/../.." && pwd)"
  if [[ -f "$cand/scripts/analyze_rhythm.sh" ]]; then
    echo "$cand"
    return
  fi
  cand="$(cd "$SKILL_DIR/../../.." && pwd)"
  if [[ -f "$cand/scripts/analyze_rhythm.sh" ]]; then
    echo "$cand"
    return
  fi
  echo "$(cd "$SKILL_DIR/../.." && pwd)"
}

REPO_ROOT="$(resolve_repo_root)"
exec bash "$REPO_ROOT/scripts/analyze_rhythm.sh" "$@"
