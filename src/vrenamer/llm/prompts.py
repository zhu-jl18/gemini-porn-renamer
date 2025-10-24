"""提示词加载器 - 从 YAML 配置文件加载提示词."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from vrenamer.core.exceptions import ConfigError


class PromptLoader:
    """提示词加载器."""

    @staticmethod
    def load_prompt_config(prompt_file: Path) -> Dict[str, Any]:
        """从 YAML 文件加载提示词配置.

        Args:
            prompt_file: 提示词配置文件路径

        Returns:
            提示词配置字典

        Raises:
            ConfigError: 文件不存在或格式错误
        """
        if not prompt_file.exists():
            raise ConfigError(f"Prompt file not found: {prompt_file}")

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigError(f"Invalid prompt config format in {prompt_file}")

            return config
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML in {prompt_file}: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load prompt config from {prompt_file}: {e}")

    @staticmethod
    def build_prompt(
        config: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建提示词.

        Args:
            config: 提示词配置
            variables: 变量字典（用于模板替换）

        Returns:
            构建好的提示词

        Raises:
            ConfigError: 配置缺少必需字段
        """
        # 获取系统提示词
        system_prompt = config.get("system_prompt", "")

        # 获取用户提示词模板
        user_prompt_template = config.get("user_prompt_template", "")

        # 如果有变量，进行模板替换
        if variables and user_prompt_template:
            try:
                user_prompt = user_prompt_template.format(**variables)
            except KeyError as e:
                raise ConfigError(f"Missing variable in prompt template: {e}")
        else:
            user_prompt = user_prompt_template

        # 组合提示词
        if system_prompt and user_prompt:
            return f"{system_prompt}\n\n{user_prompt}"
        elif system_prompt:
            return system_prompt
        elif user_prompt:
            return user_prompt
        else:
            raise ConfigError("Prompt config must contain system_prompt or user_prompt_template")

    @staticmethod
    def get_prompt_params(config: Dict[str, Any]) -> Dict[str, Any]:
        """获取提示词参数（温度、最大 token 等）.

        Args:
            config: 提示词配置

        Returns:
            参数字典
        """
        return {
            "response_format": config.get("response_format", "json"),
            "temperature": config.get("temperature", 0.1),
            "max_tokens": config.get("max_tokens", 512),
        }
