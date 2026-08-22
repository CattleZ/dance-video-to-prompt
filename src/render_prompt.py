"""校验并规范化 7 段模板输出。"""

from __future__ import annotations

import re

REQUIRED_SECTIONS = [
    "视觉风格",
    "场景叙述",
    "拍摄场景",
    "摄影技术",
    "动作清单",
    "对话/文字",
    "背景声音",
]


def normalize_prompt_markdown(text: str) -> str:
    """尽量规整模型输出为标准 7 段 Markdown。"""
    text = text.strip()
    # 去掉可能的代码围栏
    if text.startswith("```"):
        text = re.sub(r"^```(?:markdown|md)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    sections = _split_sections(text)
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    if missing:
        # 若结构不完整，原样返回，由上层记录警告
        return text

    parts: list[str] = []
    for title in REQUIRED_SECTIONS:
        body = sections[title].strip()
        parts.append(f"## {title}\n\n{body}")
    return "\n\n".join(parts).strip() + "\n"


def _split_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s*(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    result: dict[str, str] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        # 兼容「对话／文字」全角斜杠
        title = title.replace("／", "/")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[title] = text[start:end].strip()
    return result


def validate_prompt(text: str) -> list[str]:
    issues: list[str] = []
    sections = _split_sections(text)
    for title in REQUIRED_SECTIONS:
        if title not in sections:
            issues.append(f"缺少章节：{title}")
        elif not sections[title].strip():
            issues.append(f"章节为空：{title}")
    return issues
