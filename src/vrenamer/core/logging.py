"""日志系统 - 结构化日志，支持控制台和文件输出."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


class AppLogger:
    """应用日志管理器."""

    _loggers: dict[str, logging.Logger] = {}

    @staticmethod
    def setup(
        log_dir: Path,
        level: str = "INFO",
        console: bool = True,
        file: bool = True,
        name: str = "vrenamer",
    ) -> logging.Logger:
        """配置日志系统.

        Args:
            log_dir: 日志目录
            level: 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
            console: 是否输出到控制台
            file: 是否输出到文件
            name: 日志器名称

        Returns:
            配置好的日志器
        """
        # 如果已经配置过，直接返回
        if name in AppLogger._loggers:
            return AppLogger._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        # 清除已有的处理器
        logger.handlers.clear()

        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件处理器
        if file:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f"{name}.log", encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # 防止日志传播到根日志器
        logger.propagate = False

        # 缓存日志器
        AppLogger._loggers[name] = logger

        return logger

    @staticmethod
    def get_logger(name: str = "vrenamer") -> logging.Logger:
        """获取日志器.

        Args:
            name: 日志器名称

        Returns:
            日志器实例
        """
        if name in AppLogger._loggers:
            return AppLogger._loggers[name]

        # 如果没有配置过，使用默认配置
        return AppLogger.setup(
            log_dir=Path("logs"), level="INFO", console=True, file=True, name=name
        )
