from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_base_url: str = "http://localhost:3001/proxy/free"
    gemini_api_key: str = ""
    model_flash: str = "gemini-flash-latest"
    model_pro: str = "gemini-2.5-pro"
    llm_transport: str = "openai_compat"  # openai_compat | gemini_native
    max_concurrency: int = 64  # 提升默认并发数，充分利用 GPT-Load 资源
    request_timeout: int = 30
    retry: int = 3

    # 分析配置（基于 Free Tier 实测：50 张可用，建议默认 20）
    analysis_batch_size: int = 20  # 每批次的帧数（Free Tier 保守策略）
    analysis_batch_size_max: int = 50  # 最大批次大小（Free Tier 实测上限）

    # 命名风格配置
    naming_styles: str = "chinese_descriptive,scene_role,pornhub_style,concise"
    naming_style_config: str = "examples/naming_styles.yaml"
    candidates_per_style: int = 1
    total_candidates: int = 5

    # 日志目录配置
    log_dir: str = "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_style_ids(self) -> list[str]:
        """解析命名风格 ID 列表."""
        return [s.strip() for s in self.naming_styles.split(",") if s.strip()]

    def get_style_config_path(self) -> Path:
        """获取命名风格配置文件路径."""
        return Path(self.naming_style_config)
