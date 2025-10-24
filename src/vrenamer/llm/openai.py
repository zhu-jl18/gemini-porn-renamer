"""OpenAI 客户端实现."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import List

import aiohttp

from vrenamer.core.config import LLMBackendConfig
from vrenamer.core.exceptions import APIError
from vrenamer.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端."""

    def __init__(self, config: LLMBackendConfig, logger: logging.Logger = None):
        """初始化 OpenAI 客户端.

        Args:
            config: LLM 后端配置
            logger: 日志器（可选）
        """
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.organization = config.organization
        self.timeout = config.timeout
        self.retry = config.retry
        self.logger = logger or logging.getLogger(__name__)

    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        """分类任务（多模态）."""
        url = f"{self.base_url}/chat/completions"

        # 构建消息
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
            )

        body = {
            "model": "gpt-4-vision-preview",
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            body["response_format"] = {"type": "json_object"}

        self.logger.debug(f"Calling OpenAI API: {url}")
        self.logger.debug(f"Request: model={body['model']}, images={len(images)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                self.logger.debug(f"HTTP Status: {resp.status}")

                if resp.status != 200:
                    error_text = await resp.text()
                    self.logger.error(f"API Error: {error_text}")
                    raise APIError(
                        f"OpenAI API returned status {resp.status}",
                        status_code=resp.status,
                        response=error_text,
                    )

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise APIError("Empty choices array in response")

                content = choices[0].get("message", {}).get("content") or ""
                self.logger.debug(f"Response length: {len(content)} chars")
                return content

    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成任务（纯文本）."""
        url = f"{self.base_url}/chat/completions"

        body = {
            "model": "gpt-4-turbo-preview",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            body["response_format"] = {"type": "json_object"}

        self.logger.debug(f"Calling OpenAI API for generation: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise APIError(
                        f"OpenAI API returned status {resp.status}",
                        status_code=resp.status,
                        response=error_text,
                    )

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise APIError("Empty choices array in response")

                return choices[0].get("message", {}).get("content") or ""

    def _headers(self) -> dict:
        """构建请求头."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers
