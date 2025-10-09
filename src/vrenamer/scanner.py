"""视频文件扫描器."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, List, Optional

import chardet


class VideoScanner:
    """扫描目录中的视频文件."""

    # 支持的视频扩展名
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}

    def __init__(self, root_dir: Path, skip_patterns: Optional[List[str]] = None):
        """初始化扫描器.

        Args:
            root_dir: 根目录
            skip_patterns: 跳过的文件名模式（如已处理标记）
        """
        self.root_dir = Path(root_dir).resolve()
        self.skip_patterns = skip_patterns or []

    def scan(self, recursive: bool = True) -> Iterator[Path]:
        """扫描视频文件.

        Args:
            recursive: 是否递归扫描子目录

        Yields:
            视频文件路径
        """
        if recursive:
            for root, dirs, files in os.walk(self.root_dir):
                # 跳过特殊目录
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["logs", "temp", "tmp"]]

                for file in files:
                    file_path = Path(root) / file
                    if self._is_video_file(file_path) and not self._should_skip(file_path):
                        yield file_path
        else:
            for file_path in self.root_dir.iterdir():
                if file_path.is_file() and self._is_video_file(file_path) and not self._should_skip(file_path):
                    yield file_path

    def _is_video_file(self, file_path: Path) -> bool:
        """判断是否为视频文件."""
        return file_path.suffix.lower() in self.VIDEO_EXTENSIONS

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否应该跳过."""
        name = file_path.name
        for pattern in self.skip_patterns:
            if pattern in name:
                return True
        return False

    def detect_encoding(self, file_path: Path) -> Optional[str]:
        """检测文件名编码（识别乱码）.

        Args:
            file_path: 文件路径

        Returns:
            编码名称，如果无法检测则返回 None
        """
        try:
            filename_bytes = file_path.name.encode("utf-8")
            result = chardet.detect(filename_bytes)
            return result.get("encoding")
        except Exception:
            return None

    def is_garbled(self, file_path: Path) -> bool:
        """判断文件名是否乱码.

        Args:
            file_path: 文件路径

        Returns:
            是否乱码
        """
        name = file_path.stem  # 不含扩展名
        # 检测乱码特征：
        # 1. 包含大量非 ASCII 字符但不是常见 UTF-8
        # 2. 包含特殊字符序列
        try:
            name.encode("ascii")
            # 纯 ASCII，不算乱码
            return False
        except UnicodeEncodeError:
            # 包含非 ASCII
            # 检查是否有意义的中文/日文/韩文
            has_cjk = any("\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" or "\uac00" <= c <= "\ud7af" for c in name)
            if has_cjk:
                return False  # 有正常的 CJK 字符，不算乱码

            # 其他情况，检查是否有太多特殊字符
            special_count = sum(1 for c in name if not c.isalnum() and c not in " -_.")
            return special_count > len(name) * 0.3  # 超过30%特殊字符认为是乱码
