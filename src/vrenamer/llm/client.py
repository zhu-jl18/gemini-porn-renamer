from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp


class GeminiClient:
    """Thin client over GPT-Load proxy for Gemini.

    Supports two transports:
    - openai_compat:   {base}/v1beta/openai/chat/completions (messages)
    - gemini_native:   {base}/v1beta/models/{model}:generateContent (parts)
    """

    def __init__(self, base_url: str, api_key: str, transport: str = "openai_compat", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.transport = transport
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",  # 明确禁用压缩
        }

    async def classify_json(
        self,
        model: str,
        system_prompt: str,
        user_text: str,
        images: List[Path],
        response_json: bool = True,
        temperature: float = 0.2,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self.transport == "openai_compat":
            url = f"{self.base_url}/v1beta/openai/chat/completions"
            msgs = self._make_messages(user_text, images, system_prompt)
            body: Dict[str, Any] = {
                "model": model,
                "messages": msgs,
                "temperature": temperature,
                "max_tokens": extra.get("max_tokens", 4096) if extra else 4096,
            }
            # Try JSON response formatting if supported
            body["response_format"] = {"type": "json_object"} if response_json else {"type": "text"}
        else:
            url = f"{self.base_url}/v1beta/models/{model}:generateContent"
            parts = [{"text": user_text}] + [self._img_part(p) for p in images]
            body = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": parts}],
                "generation_config": {"temperature": temperature, **({} if not extra else extra)},
            }
        # 使用 aiohttp，禁用自动解压缩（GPT-Load 的 gzip 头有问题）
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout, auto_decompress=False) as session:
            async with session.post(url, headers=self._headers(), json=body) as resp:
                resp.raise_for_status()
                # 读取原始字节，手动解码
                raw_bytes = await resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
            if self.transport == "openai_compat":
                # OpenAI-compatible: choices[0].message.content
                return (data.get("choices", [{}])[0].get("message", {}).get("content") or "")
            else:
                # Gemini native: candidates[0].content.parts[].text
                cands = data.get("candidates", [])
                if not cands:
                    return ""
                parts = cands[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                return "\n".join([t for t in texts if t])

    async def name_candidates(
        self,
        model: str,
        system_prompt: str,
        user_text: str,
        temperature: float = 0.3,
        json_array: bool = True,
    ) -> str:
        if self.transport == "openai_compat":
            url = f"{self.base_url}/v1beta/openai/chat/completions"
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": temperature,
            }
            if json_array:
                body["response_format"] = {"type": "json_object"}  # we'll parse array from text
        else:
            url = f"{self.base_url}/v1beta/models/{model}:generateContent"
            body = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                "generation_config": {"temperature": temperature},
            }
        # 使用 aiohttp，禁用自动解压缩（GPT-Load 的 gzip 头有问题）
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout, auto_decompress=False) as session:
            async with session.post(url, headers=self._headers(), json=body) as resp:
                resp.raise_for_status()
                # 读取原始字节，手动解码
                raw_bytes = await resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
            if self.transport == "openai_compat":
                return (data.get("choices", [{}])[0].get("message", {}).get("content") or "")
            else:
                cands = data.get("candidates", [])
                if not cands:
                    return ""
                parts = cands[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                return "\n".join([t for t in texts if t])

    def _make_messages(self, user_text: str, images: List[Path], system_prompt: str) -> list:
        content = [{"type": "text", "text": user_text}]
        for p in images:
            data = base64.b64encode(Path(p).read_bytes()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _img_part(p: Path) -> Dict[str, Any]:
        data = base64.b64encode(Path(p).read_bytes()).decode("ascii")
        return {"inline_data": {"mime_type": "image/jpeg", "data": data}}
