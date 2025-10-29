"""配置管理系统 - 使用 pydantic-settings 统一管理配置."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMBackendConfig(BaseSettings):
    """LLM 后端配置."""

    type: Literal["gemini", "openai"] = "gemini"
    base_url: str
    api_key: str
    timeout: int = 30
    retry: int = 3
    # Gemini 特有配置
    transport: str = "openai_compat"  # gemini_native | openai_compat
    # OpenAI 特有配置
    organization: str = ""


class ModelConfig(BaseSettings):
    """模型配置."""

    flash: str = "gemini-flash-latest"  # 用于分析任务
    pro: str = "gemini-2.5-pro"  # 用于命名生成


class ConcurrencyConfig(BaseSettings):
    """并发配置（两层并发）."""

    # 第一层：子任务并发数
    task_concurrency: int = 4  # 同时执行的子任务数
    # 第二层：每个子任务内的批次并发数
    batch_concurrency: int = 16  # 每个子任务内同时执行的批次数


class AnalysisConfig(BaseSettings):
    """分析配置."""

    tasks_config_path: Path = Path("config/analysis_tasks.yaml")
    prompts_dir: Path = Path("config/prompts/analysis")
    # 批次大小配置（基于 Free Tier 实测：50 张可用，建议默认 20）
    batch_size: int = 20  # 每批次的帧数（默认值，保守策略）
    batch_size_max: int = 50  # 最大批次大小（Free Tier 实测上限）

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int, info) -> int:
        """验证 batch_size 不超过 batch_size_max."""
        # 注意：此时 batch_size_max 可能还未设置，需要从 info.data 获取
        max_size = info.data.get("batch_size_max", 50)
        if v > max_size:
            raise ValueError(f"batch_size ({v}) cannot exceed batch_size_max ({max_size})")
        if v < 1:
            raise ValueError(f"batch_size ({v}) must be at least 1")
        return v


class TranscriptConfig(BaseSettings):
    """字幕/音频转写配置."""

    enabled: bool = False  # 默认禁用（待后续实现）
    backend: str = "dummy"  # dummy | gemini
    timeout: int = 60  # 音频转写超时时间（秒）


class NamingConfig(BaseSettings):
    """命名配置."""

    styles: List[str] = ["chinese_descriptive", "scene_role"]
    style_config_path: Path = Path("config/naming_styles.yaml")
    prompts_dir: Path = Path("config/prompts/naming")
    candidates_per_style: int = 1
    total_candidates: int = 5


class AppConfig(BaseSettings):
    """应用配置 - 主配置类."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # LLM 后端配置
    llm_backend: str = "gemini"  # 默认使用 Gemini
    llm_backends: Dict[str, LLMBackendConfig] = {}

    # 模型配置
    model: ModelConfig = ModelConfig()

    # 并发配置
    concurrency: ConcurrencyConfig = ConcurrencyConfig()

    # 分析配置
    analysis: AnalysisConfig = AnalysisConfig()

    # 字幕/音频转写配置
    transcript: TranscriptConfig = TranscriptConfig()

    # 命名配置
    naming: NamingConfig = NamingConfig()

    # 日志配置
    log_dir: Path = Path("logs")
    log_level: str = "INFO"

    def get_llm_backend(self) -> LLMBackendConfig:
        """获取当前 LLM 后端配置.

        Returns:
            LLM 后端配置

        Raises:
            ConfigError: 后端未配置
        """
        if self.llm_backend not in self.llm_backends:
            # 如果没有配置 llm_backends，尝试从环境变量构建默认配置
            if self.llm_backend == "gemini":
                return self._build_default_gemini_config()
            raise ValueError(f"LLM backend '{self.llm_backend}' not configured")
        return self.llm_backends[self.llm_backend]

    def _build_default_gemini_config(self) -> LLMBackendConfig:
        """从环境变量构建默认 Gemini 配置（向后兼容）."""
        import os

        return LLMBackendConfig(
            type="gemini",
            base_url=os.getenv("GEMINI_BASE_URL", "http://localhost:3001/proxy/free"),
            api_key=os.getenv("GEMINI_API_KEY", ""),
            transport=os.getenv("LLM_TRANSPORT", "openai_compat"),
            timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
            retry=int(os.getenv("RETRY", "3")),
        )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper
