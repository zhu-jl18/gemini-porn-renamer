"""LLM 客户端工厂 - 根据配置创建对应的客户端."""

from __future__ import annotations

import logging

from vrenamer.core.config import AppConfig
from vrenamer.core.exceptions import ConfigError
from vrenamer.llm.base import BaseLLMClient
from vrenamer.llm.gemini import GeminiClient
from vrenamer.llm.openai import OpenAIClient


class LLMClientFactory:
    """LLM 客户端工厂."""

    @staticmethod
    def create(config: AppConfig, logger: logging.Logger = None) -> BaseLLMClient:
        """根据配置创建 LLM 客户端.

        Args:
            config: 应用配置
            logger: 日志器（可选）

        Returns:
            LLM 客户端实例

        Raises:
            ConfigError: 不支持的后端类型或配置错误
        """
        try:
            backend_config = config.get_llm_backend()
        except Exception as e:
            raise ConfigError(f"Failed to get LLM backend config: {e}")

        if backend_config.type == "gemini":
            return GeminiClient(backend_config, logger)
        elif backend_config.type == "openai":
            return OpenAIClient(backend_config, logger)
        else:
            raise ConfigError(
                f"Unsupported LLM backend: {backend_config.type}. "
                f"Supported backends: gemini, openai"
            )
