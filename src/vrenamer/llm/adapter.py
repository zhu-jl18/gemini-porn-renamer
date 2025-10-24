from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from vrenamer.llm.base import BaseLLMClient


class GeminiLLMAdapter(BaseLLMClient):
    """Adapter that exposes GeminiClient via the BaseLLMClient contract."""

    def __init__(self, client, model_flash: str, model_pro: str):
        self._client = client
        self._model_flash = model_flash
        self._model_pro = model_pro

    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        response_json = response_format == "json"
        extra = {"max_output_tokens": max_tokens} if max_tokens else None
        return await self._client.classify_json(
            model=self._model_flash,
            system_prompt="仅输出JSON对象，禁止额外文本。",
            user_text=prompt,
            images=images,
            response_json=response_json,
            temperature=temperature,
            extra=extra,
        )

    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        json_array = response_format == "json"
        return await self._client.name_candidates(
            model=self._model_pro,
            system_prompt="仅输出JSON对象，字段 names 为字符串数组。",
            user_text=prompt,
            temperature=temperature,
            json_array=json_array,
        )
