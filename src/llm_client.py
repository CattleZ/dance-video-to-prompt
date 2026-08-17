"""Anthropic 兼容多模态 API 客户端。"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VisionLLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("ANTHROPIC_BASE_URL")
            or os.getenv("VISION_BASE_URL")
            or ""
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.getenv("ANTHROPIC_AUTH_TOKEN")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("VISION_API_KEY")
            or ""
        )
        self.model = (
            model
            or os.getenv("VISION_MODEL")
            or os.getenv("ANTHROPIC_MODEL")
            or ""
        )
        self.timeout = timeout

        if not self.base_url:
            raise ValueError("缺少 ANTHROPIC_BASE_URL / VISION_BASE_URL")
        if not self.api_key:
            raise ValueError("缺少 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY")
        if not self.model:
            raise ValueError("缺少 VISION_MODEL（需为支持看图的多模态模型）")

    def complete_with_images(
        self,
        system: str,
        user_text: str,
        image_paths: list[Path],
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        content: list[dict[str, Any]] = []
        for path in image_paths:
            media_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
            data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data,
                    },
                }
            )
        content.append({"type": "text", "text": user_text})

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
        }
        # 透传自定义头（部分公司网关需要）
        custom = os.getenv("ANTHROPIC_CUSTOM_HEADERS", "")
        if custom:
            for part in custom.split(";"):
                part = part.strip()
                if ":" in part:
                    k, v = part.split(":", 1)
                    headers[k.strip()] = v.strip()

        url = f"{self.base_url}/v1/messages"
        logger.info("调用视觉模型 model=%s images=%d", self.model, len(image_paths))
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"模型调用失败 HTTP {resp.status_code}: {resp.text[:800]}"
                )
            data = resp.json()

        return _extract_text(data)


def _extract_text(data: dict[str, Any]) -> str:
    # Anthropic messages 格式
    content = data.get("content")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            return "\n".join(parts).strip()

    # 部分网关兼容 OpenAI chat 格式
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        text = msg.get("content")
        if isinstance(text, str):
            return text.strip()

    raise RuntimeError(f"无法解析模型响应: {str(data)[:500]}")
