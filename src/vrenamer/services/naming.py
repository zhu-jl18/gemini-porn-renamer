"""命名生成服务 - 封装命名生成逻辑."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from vrenamer.core.config import AppConfig
from vrenamer.llm.base import BaseLLMClient
from vrenamer.naming import NamingGenerator, NamingStyleConfig


class NamingService:
    """命名生成服务."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        config: AppConfig,
        logger: logging.Logger,
    ):
        """初始化命名服务.

        Args:
            llm_client: LLM 客户端
            config: 应用配置
            logger: 日志器
        """
        self.llm = llm_client
        self.config = config
        self.logger = logger

        # 加载风格配置
        self.style_config = NamingStyleConfig.from_yaml(config.naming.style_config_path)

        # 创建生成器
        self.generator = NamingGenerator(
            llm_client=llm_client, style_config=self.style_config, model=config.model.pro
        )

    async def generate_candidates(
        self,
        analysis: Dict[str, Any],
        style_ids: Optional[List[str]] = None,
        n_per_style: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """生成命名候选.

        Args:
            analysis: 视频分析结果
            style_ids: 风格 ID 列表（None 则使用配置默认值）
            n_per_style: 每个风格的候选数（None 则使用配置默认值）

        Returns:
            候选名称列表，每个元素包含 {style_id, style_name, filename, language}
        """
        self.logger.info("开始生成命名候选")

        # 使用配置的默认值
        if style_ids is None:
            style_ids = self.config.naming.styles

        if n_per_style is None:
            n_per_style = self.config.naming.candidates_per_style

        self.logger.info(f"使用风格: {style_ids}, 每个风格 {n_per_style} 个候选")

        # 生成候选
        candidates = await self.generator.generate_candidates(
            analysis=analysis, style_ids=style_ids, n_per_style=n_per_style
        )

        # 转换为字典列表
        result = [
            {
                "style_id": c.style_id,
                "style_name": c.style_name,
                "filename": c.filename,
                "language": c.language,
            }
            for c in candidates
        ]

        self.logger.info(f"生成了 {len(result)} 个候选名称")
        return result
