"""Gemini 客户端实现 - 支持两种传输格式."""

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


class GeminiClient(BaseLLMClient):
    """Gemini 客户端（支持 openai_compat 和 gemini_native 两种格式）."""

    def __init__(self, config: LLMBackendConfig, logger: logging.Logger = None):
        """初始化 Gemini 客户端.

        Args:
            config: LLM 后端配置
            logger: 日志器（可选）
        """
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.transport = config.transport  # openai_compat | gemini_native
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
        if self.transport == "openai_compat":
            return await self._classify_openai_format(
                prompt, images, response_format, temperature, max_tokens
            )
        else:
            return await self._classify_gemini_format(
                prompt, images, response_format, temperature, max_tokens
            )

    async def _classify_openai_format(
        self, prompt: str, images: List[Path], response_format: str, temperature: float, max_tokens: int
    ) -> str:
        """OpenAI 兼容格式."""
        url = f"{self.base_url}/v1beta/openai/chat/completions"

        # 构建消息
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
            )

        body = {
            "model": "gemini-flash-latest",
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            body["response_format"] = {"type": "json_object"}

        # 发送请求
        self.logger.debug(f"Calling Gemini API (OpenAI format): {url}")
        self.logger.debug(f"Request body: model={body['model']}, temperature={temperature}, images={len(images)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                self.logger.debug(f"HTTP Status: {resp.status}")
                self.logger.debug(f"Response Headers: {dict(resp.headers)}")

                if resp.status != 200:
                    error_text = await resp.text()
                    self.logger.error(f"API Error: {error_text}")
                    raise APIError(
                        f"Gemini API returned status {resp.status}",
                        status_code=resp.status,
                        response=error_text,
                    )

                # 读取原始字节
                raw_bytes = await resp.read()
                self.logger.debug(f"Raw response length: {len(raw_bytes)} bytes")

                try:
                    data = json.loads(raw_bytes.decode("utf-8"))
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode failed: {e}")
                    self.logger.error(f"Raw content (first 500): {raw_bytes[:500]}")
                    raise APIError(f"Failed to decode JSON response: {e}", response=raw_bytes[:500].decode("utf-8", errors="ignore"))

                # 提取内容
                choices = data.get("choices", [])
                if not choices:
                    self.logger.error(f"Empty choices array. Full response: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
                    raise APIError("Empty choices array in response", response=json.dumps(data)[:500])

                content = choices[0].get("message", {}).get("content") or ""
                self.logger.debug(f"Response content length: {len(content)} chars")
                self.logger.debug(f"Response preview: {content[:200]}")

                return content

    async def _classify_gemini_format(
        self, prompt: str, images: List[Path], response_format: str, temperature: float, max_tokens: int
    ) -> str:
        """Gemini 原生格式."""
        url = f"{self.base_url}/v1beta/models/gemini-flash-latest:generateContent"

        # 构建 parts
        parts = [{"text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_data}})

        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generation_config": {"temperature": temperature, "max_output_tokens": max_tokens},
        }

        # 发送请求
        self.logger.debug(f"Calling Gemini API (native format): {url}")

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
                        f"Gemini API returned status {resp.status}",
                        status_code=resp.status,
                        response=error_text,
                    )

                raw_bytes = await resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))

                # 提取内容
                candidates = data.get("candidates", [])
                if not candidates:
                    self.logger.error(f"Empty candidates array. Full response: {json.dumps(data)[:1000]}")
                    raise APIError("Empty candidates array in response")

                parts = candidates[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                result = "\n".join([t for t in texts if t])

                self.logger.debug(f"Response length: {len(result)} chars")
                return result

    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成任务（纯文本）."""
        if self.transport == "openai_compat":
            url = f"{self.base_url}/v1beta/openai/chat/completions"
            body = {
                "model": "gemini-2.5-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format == "json":
                body["response_format"] = {"type": "json_object"}
        else:
            url = f"{self.base_url}/v1beta/models/gemini-2.5-pro:generateContent"
            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generation_config": {"temperature": temperature, "max_output_tokens": max_tokens},
            }

        self.logger.debug(f"Calling Gemini API for generation: {url}")

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
                        f"Gemini API returned status {resp.status}",
                        status_code=resp.status,
                        response=error_text,
                    )

                raw_bytes = await resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))

                if self.transport == "openai_compat":
                    choices = data.get("choices", [])
                    if not choices:
                        raise APIError("Empty choices array in response")
                    return choices[0].get("message", {}).get("content") or ""
                else:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise APIError("Empty candidates array in response")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                    return "\n".join([t for t in texts if t])

    def _headers(self) -> dict:
        """构建请求头."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
