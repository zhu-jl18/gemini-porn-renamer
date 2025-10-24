"""共享类型定义 - 数据类和类型别名."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class VideoInfo:
    """视频信息."""

    path: Path
    duration: float  # 秒
    size_bytes: int
    format: str  # 文件格式（如 mp4, mkv）


@dataclass
class FrameSampleResult:
    """视频抽帧结果."""

    directory: Path  # 帧保存目录
    frames: List[Path]  # 帧文件路径列表
    duration: float  # 视频时长
    fps: float  # 抽帧帧率


@dataclass
class AnalysisResult:
    """分析结果."""

    tags: Dict[str, List[str]]  # 标签字典，如 {"role_archetype": ["人妻"], ...}
    confidence: Dict[str, float]  # 置信度字典
    metadata: Dict[str, Any]  # 元数据
    timestamp: datetime  # 分析时间


@dataclass
class NameCandidate:
    """命名候选."""

    filename: str  # 文件名（不含扩展名）
    style_id: str  # 风格 ID
    style_name: str  # 风格名称
    language: str  # 语言（zh/en）
    score: Optional[float] = None  # 评分（可选）


@dataclass
class RenameOperation:
    """重命名操作记录."""

    source: Path  # 源文件路径
    target: Path  # 目标文件路径
    analysis: AnalysisResult  # 分析结果
    selected_candidate: NameCandidate  # 选中的候选
    timestamp: datetime  # 操作时间
    dry_run: bool  # 是否为预览模式
