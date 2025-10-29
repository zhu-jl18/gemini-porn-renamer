"""字幕/音频转写服务 - 占位接口（待后续实现）.

本模块提供音频转写的抽象接口和默认实现。
当前版本仅提供占位实现（返回空字符串），实际转写功能待后续开发。

设计说明：
- 抽象基类 TranscriptExtractor 定义统一接口
- DummyTranscriptExtractor 提供默认占位实现
- 通过配置开关 transcript.enabled 控制是否启用
- 预留扩展点，便于后续集成 Gemini Audio API 或其他转写服务

参考文档：
- docs/decisions.md: Free Tier 音频转写测试结果
- docs/maintenance.md: 音频转写功能预留说明
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class TranscriptExtractor(ABC):
    """音频转写抽象基类.
    
    定义统一的音频转写接口，支持多种后端实现。
    """

    @abstractmethod
    async def extract(self, video_path: Path) -> str:
        """从视频中提取音频并转写为文本.
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            转写后的文本内容（纯文本，无时间戳）
            
        Raises:
            TranscriptError: 转写失败时抛出
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查转写服务是否可用.
        
        Returns:
            True 表示服务可用，False 表示不可用
        """
        pass


class TranscriptError(Exception):
    """音频转写错误."""
    pass


class DummyTranscriptExtractor(TranscriptExtractor):
    """占位实现 - 不执行实际转写，返回空字符串.
    
    用于在音频转写功能未实现时提供默认行为。
    """

    async def extract(self, video_path: Path) -> str:
        """返回空字符串（占位实现）.
        
        Args:
            video_path: 视频文件路径（未使用）
            
        Returns:
            空字符串
        """
        return ""

    def is_available(self) -> bool:
        """始终返回 False（占位实现不可用）.
        
        Returns:
            False
        """
        return False


class GeminiTranscriptExtractor(TranscriptExtractor):
    """Gemini Audio API 转写实现（待实现）.
    
    计划使用 Gemini 2.5 Flash 的音频输入能力进行转写。
    
    待实现功能：
    1. 使用 ffmpeg 提取音频为 16kHz mono WAV
    2. 调用 Gemini API 进行音频转写
    3. 处理 gzip 压缩响应
    4. 实现重试和错误处理
    
    参考：
    - test_audio_transcription.py: 测试脚本（gzip 解压问题待修复）
    - src/vrenamer/llm/client.py: 现有 Gemini 客户端实现
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "gemini-2.5-flash",
        transport: str = "openai_compat",
        timeout: int = 60,
        retry: int = 3,
    ):
        """初始化 Gemini 转写器.
        
        Args:
            base_url: GPT-Load 代理地址
            api_key: API 密钥
            model: 模型名称
            transport: 传输协议（openai_compat 或 gemini_native）
            timeout: 请求超时时间（秒）
            retry: 重试次数
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.transport = transport
        self.timeout = timeout
        self.retry = retry

    async def extract(self, video_path: Path) -> str:
        """从视频中提取音频并转写（待实现）.
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            转写后的文本内容
            
        Raises:
            NotImplementedError: 当前版本未实现
        """
        raise NotImplementedError(
            "Gemini 音频转写功能待实现。"
            "参考 scripts/debug/test_audio_transcription.py 测试脚本。"
        )

    def is_available(self) -> bool:
        """检查服务是否可用（待实现）.
        
        Returns:
            False（当前版本未实现）
        """
        return False


def create_transcript_extractor(
    enabled: bool = False,
    backend: str = "dummy",
    **kwargs,
) -> TranscriptExtractor:
    """工厂函数：创建音频转写器实例.
    
    Args:
        enabled: 是否启用音频转写
        backend: 后端类型（dummy | gemini）
        **kwargs: 后端特定参数
        
    Returns:
        TranscriptExtractor 实例
        
    Examples:
        >>> # 默认占位实现
        >>> extractor = create_transcript_extractor()
        >>> await extractor.extract(video_path)  # 返回空字符串
        
        >>> # Gemini 后端（待实现）
        >>> extractor = create_transcript_extractor(
        ...     enabled=True,
        ...     backend="gemini",
        ...     base_url="http://localhost:3001/proxy/free",
        ...     api_key="your-key",
        ... )
    """
    if not enabled or backend == "dummy":
        return DummyTranscriptExtractor()
    
    if backend == "gemini":
        return GeminiTranscriptExtractor(**kwargs)
    
    raise ValueError(f"Unknown transcript backend: {backend}")

