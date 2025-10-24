"""LLM 客户端抽象基类 - 定义统一的接口."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类.

    所有 LLM 客户端实现必须继承此类并实现抽象方法。
    """

    @abstractmethod
    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        """分类任务（多模态）.

        Args:
            prompt: 提示词
            images: 图片路径列表
            response_format: 响应格式（json/text）
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 响应文本

        Raises:
            APIError: API 调用失败
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成任务（纯文本）.

        Args:
            prompt: 提示词
            response_format: 响应格式（json/text）
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 响应文本

        Raises:
            APIError: API 调用失败
        """
        pass
