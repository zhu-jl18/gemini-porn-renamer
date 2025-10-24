"""文件扫描服务 - 扫描目录中的视频文件."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set

import chardet


class ScannerService:
    """文件扫描服务."""

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}

    def __init__(self, logger: logging.Logger, min_size_mb: float = 10.0):
        """初始化扫描服务.

        Args:
            logger: 日志器
            min_size_mb: 最小文件大小（MB）
        """
        self.logger = logger
        self.min_size_bytes = int(min_size_mb * 1024 * 1024)

    def scan_directory(
        self,
        root_dir: Path,
        recursive: bool = True,
        skip_processed: bool = False,
    ) -> Iterator[Path]:
        """扫描目录中的视频文件.

        Args:
            root_dir: 根目录
            recursive: 是否递归扫描子目录
            skip_processed: 是否跳过已处理的文件

        Yields:
            视频文件路径
        """
        self.logger.info(f"开始扫描目录: {root_dir}")

        if recursive:
            for root, dirs, files in os.walk(root_dir):
                # 跳过特殊目录
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".") and d not in ["logs", "temp", "tmp", "frames"]
                ]

                for file in files:
                    file_path = Path(root) / file
                    if self._should_include(file_path, skip_processed):
                        yield file_path
        else:
            for file_path in root_dir.iterdir():
                if file_path.is_file() and self._should_include(file_path, skip_processed):
                    yield file_path

    def _should_include(self, file_path: Path, skip_processed: bool) -> bool:
        """判断是否应该包含该文件.

        Args:
            file_path: 文件路径
            skip_processed: 是否跳过已处理的文件

        Returns:
            是否包含
        """
        # 检查扩展名
        if not self.is_video_file(file_path):
            return False

        # 检查文件大小
        try:
            if file_path.stat().st_size < self.min_size_bytes:
                return False
        except Exception:
            return False

        # TODO: 检查是否已处理（通过审计日志）
        if skip_processed:
            # 这里可以添加检查审计日志的逻辑
            pass

        return True

    def is_video_file(self, path: Path) -> bool:
        """判断是否为视频文件.

        Args:
            path: 文件路径

        Returns:
            是否为视频文件
        """
        return path.suffix.lower() in self.VIDEO_EXTENSIONS

    def is_garbled_filename(self, path: Path) -> bool:
        """判断文件名是否乱码.

        Args:
            path: 文件路径

        Returns:
            是否乱码
        """
        name = path.stem  # 不含扩展名

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
            has_cjk = any(
                "\u4e00" <= c <= "\u9fff"
                or "\u3040" <= c <= "\u30ff"
                or "\uac00" <= c <= "\ud7af"
                for c in name
            )
            if has_cjk:
                return False  # 有正常的 CJK 字符，不算乱码

            # 其他情况，检查是否有太多特殊字符
            special_count = sum(1 for c in name if not c.isalnum() and c not in " -_.")
            return special_count > len(name) * 0.3  # 超过30%特殊字符认为是乱码

    def get_scan_summary(self, files: List[Path]) -> Dict[str, Any]:
        """生成扫描摘要.

        Args:
            files: 文件列表

        Returns:
            摘要字典
        """
        total = len(files)
        garbled = sum(1 for f in files if self.is_garbled_filename(f))
        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

        return {"total": total, "garbled": garbled, "total_size_mb": total_size_mb}
