"""命名风格配置加载和管理."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class StyleDefinition(BaseModel):
    """单个命名风格定义."""

    name: str = Field(description="风格名称")
    description: str = Field(description="风格描述")
    language: str = Field(description="语言代码 (zh/en)")
    format: str = Field(description="格式说明")
    examples: List[str] = Field(description="示例列表")
    prompt_template: str = Field(description="提示词模板")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ["zh", "en"]:
            raise ValueError(f"Unsupported language: {v}")
        return v


class DefaultConfig(BaseModel):
    """默认配置."""

    selected_styles: List[str] = Field(description="默认启用的风格")
    candidates_per_style: int = Field(default=1, description="每个风格生成的候选数")
    total_candidates: int = Field(default=5, description="总候选数上限")
    include_actor: bool = Field(default=False, description="是否包含演员名")
    max_length: int = Field(default=80, description="文件名最大长度")
    illegal_chars_replacement: str = Field(default="_", description="非法字符替换")


class NamingStyleConfig(BaseModel):
    """完整命名风格配置."""

    styles: Dict[str, StyleDefinition] = Field(description="风格定义字典")
    default: DefaultConfig = Field(description="默认配置")
    custom_styles: Optional[Dict[str, StyleDefinition]] = Field(default=None, description="用户自定义风格")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> NamingStyleConfig:
        """从 YAML 文件加载配置.

        Args:
            yaml_path: YAML 配置文件路径

        Returns:
            NamingStyleConfig 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: YAML 格式错误或验证失败
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Config file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("Invalid YAML structure: expected dict at root")

        return cls(**data)

    def get_style(self, style_id: str) -> Optional[StyleDefinition]:
        """获取指定风格定义.

        Args:
            style_id: 风格 ID

        Returns:
            StyleDefinition 或 None（如果不存在）
        """
        # 先查标准风格，再查自定义风格
        if style_id in self.styles:
            return self.styles[style_id]
        if self.custom_styles and style_id in self.custom_styles:
            return self.custom_styles[style_id]
        return None

    def list_available_styles(self) -> List[str]:
        """列出所有可用的风格 ID.

        Returns:
            风格 ID 列表
        """
        ids = list(self.styles.keys())
        if self.custom_styles:
            ids.extend(self.custom_styles.keys())
        return ids

    def validate_styles(self, style_ids: List[str]) -> List[str]:
        """验证风格 ID 列表，返回有效的 ID.

        Args:
            style_ids: 待验证的风格 ID 列表

        Returns:
            有效的风格 ID 列表（过滤掉不存在的）
        """
        available = set(self.list_available_styles())
        return [sid for sid in style_ids if sid in available]

    def sanitize_filename(self, name: str) -> str:
        """清理文件名，替换非法字符.

        Args:
            name: 原始文件名

        Returns:
            清理后的文件名
        """
        # Windows 非法字符：< > : " / \\ | ? *
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            name = name.replace(char, self.default.illegal_chars_replacement)

        # 压缩多个空白为单个空格
        name = " ".join(name.split())

        # 长度限制
        if len(name) > self.default.max_length:
            name = name[: self.default.max_length].strip()

        return name
