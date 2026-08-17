#!/usr/bin/env bash
# 将 skill 同步到项目 .grok 与用户全局目录，方便复用
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_NAME="dance-video-to-prompt"

# 仓库根：skills/xxx 的上两级
REPO_ROOT="$(cd "$SKILL_DIR/../.." && pwd)"

echo "源 skill: $SKILL_DIR"
echo "仓库根:   $REPO_ROOT"

sync_to() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  mkdir -p "$dest"
  # 拷贝内容（不跟 .git）
  cp -R "$SKILL_DIR/." "$dest/"
  # 保证脚本可执行
  chmod +x "$dest/scripts/"*.sh 2>/dev/null || true
  echo "已同步 → $dest"
}

# 1) 项目内 Grok 发现路径
sync_to "$REPO_ROOT/.grok/skills/$SKILL_NAME"

# 2) 用户 Grok 全局
if [[ -d "${HOME}/.grok" ]] || mkdir -p "${HOME}/.grok/skills" 2>/dev/null; then
  sync_to "${HOME}/.grok/skills/$SKILL_NAME"
fi

# 3) Claude / agents 全局（自动创建目录）
if mkdir -p "${HOME}/.agents/skills" 2>/dev/null; then
  sync_to "${HOME}/.agents/skills/$SKILL_NAME"
fi

# 4) Claude Code skills（自动创建目录）
if mkdir -p "${HOME}/.claude/skills" 2>/dev/null; then
  sync_to "${HOME}/.claude/skills/$SKILL_NAME"
fi

echo ""
echo "完成。主副本（请以此为准维护）:"
echo "  $REPO_ROOT/skills/$SKILL_NAME"
echo ""
echo "使用示例:"
echo "  /dance-video-to-prompt /path/to/video.mp4"
echo "  或: bash $REPO_ROOT/skills/$SKILL_NAME/scripts/run_extract.sh /path/to/video.mp4"
