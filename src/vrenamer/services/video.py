"""视频处理服务 - 封装 ffmpeg 操作."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence

from vrenamer.core.exceptions import VideoProcessingError
from vrenamer.core.types import FrameSampleResult


class VideoProcessor:
    """视频处理服务."""

    def __init__(self, logger: logging.Logger):
        """初始化视频处理器.

        Args:
            logger: 日志器
        """
        self.logger = logger
        self._check_dependencies()

    def _check_dependencies(self):
        """检查 ffmpeg 和 ffprobe 是否可用."""
        if not shutil.which("ffmpeg"):
            raise VideoProcessingError(
                "未找到 ffmpeg 命令！\n\n"
                "请安装 ffmpeg：\n"
                "  Windows: 从 https://ffmpeg.org/download.html 下载，或使用 chocolatey: choco install ffmpeg\n"
                "  或使用 scoop: scoop install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg  或  sudo yum install ffmpeg\n"
                "  macOS: brew install ffmpeg\n\n"
                "安装后请确保 ffmpeg 在 PATH 环境变量中。"
            )

        if not shutil.which("ffprobe"):
            raise VideoProcessingError(
                "未找到 ffprobe 命令！\n\n"
                "ffprobe 通常随 ffmpeg 一起安装。\n"
                "请参考 ffmpeg 的安装说明。"
            )

    async def sample_frames(
        self,
        video_path: Path,
        target_frames: int = 96,
        output_dir: Optional[Path] = None,
    ) -> FrameSampleResult:
        """抽取视频帧.

        Args:
            video_path: 视频文件路径
            target_frames: 目标帧数
            output_dir: 输出目录（可选，默认为视频同目录下的 frames 子目录）

        Returns:
            抽帧结果

        Raises:
            VideoProcessingError: 抽帧失败
        """
        self.logger.info(f"开始抽帧: {video_path}")

        # 确定输出目录
        if output_dir is None:
            frames_root = video_path.parent / "frames"
            output_dir = frames_root / video_path.stem

        output_dir.mkdir(parents=True, exist_ok=True)

        # 清理旧帧
        for existing in output_dir.glob("*.jpg"):
            try:
                existing.unlink()
            except Exception as e:
                self.logger.warning(f"无法删除旧帧 {existing}: {e}")

        # 获取视频时长
        duration = self.get_duration(video_path)
        self.logger.info(f"视频时长: {duration:.2f} 秒")

        # 计算抽帧帧率
        fps = self._decide_sampling_fps(duration, target_frames)
        self.logger.info(f"抽帧帧率: {fps:.4f} fps")

        # 构建 ffmpeg 命令
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps:.4f},scale=640:-1",
            "-vsync",
            "vfr",
            str(output_dir / "frame_%05d.jpg"),
        ]

        # 执行抽帧命令
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.debug("ffmpeg 执行成功")
            if result.stderr:
                self.logger.debug(f"ffmpeg stderr: {result.stderr[:200]}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"ffmpeg 执行失败: {e.stderr}")
            raise VideoProcessingError(f"视频抽帧失败: {e.stderr}") from e

        # 收集生成的帧
        frames = sorted(output_dir.glob("*.jpg"))
        self.logger.info(f"原始帧数: {len(frames)}")

        if not frames:
            raise VideoProcessingError(f"抽帧失败：未生成任何帧文件。目录: {output_dir}")

        # 去重
        frames = self._deduplicate_frames(frames)
        self.logger.info(f"去重后: {len(frames)} 帧")

        # 限制帧数
        frames = self._limit_frames(frames, target_frames)
        self.logger.info(f"最终采样: {len(frames)} 帧 (最大 {target_frames})")

        return FrameSampleResult(
            directory=output_dir, frames=frames, duration=duration, fps=fps
        )

    def get_duration(self, video_path: Path) -> float:
        """获取视频时长（秒）.

        Args:
            video_path: 视频文件路径

        Returns:
            视频时长（秒）

        Raises:
            VideoProcessingError: 获取时长失败
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            duration = float(result.stdout.strip())
            return max(1.0, duration)
        except Exception as e:
            self.logger.warning(f"无法获取视频时长: {e}，使用默认值 180 秒")
            return 180.0

    def _decide_sampling_fps(self, duration: float, target_frames: int) -> float:
        """决定抽帧帧率.

        Args:
            duration: 视频时长（秒）
            target_frames: 目标帧数

        Returns:
            抽帧帧率
        """
        fps = target_frames / duration
        return max(0.1, min(6.0, fps))

    def _deduplicate_frames(self, frames: Sequence[Path]) -> List[Path]:
        """去重：MD5 完全相同 + pHash 内容相似.

        Args:
            frames: 帧文件路径列表

        Returns:
            去重后的帧列表
        """
        try:
            import imagehash
            from PIL import Image

            use_phash = True
            self.logger.debug("使用 MD5 + pHash 去重")
        except ImportError:
            use_phash = False
            self.logger.warning("imagehash 未安装，仅使用 MD5 去重")

        seen_md5 = {}
        seen_phash = {}
        unique = []
        removed_count = 0

        for frame in frames:
            try:
                # 1. MD5 完全去重
                digest = hashlib.md5(frame.read_bytes()).hexdigest()
                if digest in seen_md5:
                    try:
                        frame.unlink()
                        removed_count += 1
                    except Exception:
                        pass
                    continue

                # 2. pHash 相似度去重（可选）
                if use_phash:
                    try:
                        img = Image.open(frame)
                        phash = imagehash.phash(img)

                        # 检查是否有相似帧
                        is_similar = False
                        for existing_hash in seen_phash.keys():
                            distance = imagehash.hex_to_hash(existing_hash) - phash
                            if distance <= 5:  # 汉明距离 ≤ 5 认为相似
                                is_similar = True
                                try:
                                    frame.unlink()
                                    removed_count += 1
                                except Exception:
                                    pass
                                break

                        if not is_similar:
                            seen_md5[digest] = frame
                            seen_phash[str(phash)] = frame
                            unique.append(frame)
                    except Exception as e:
                        # pHash 失败，仅用 MD5
                        self.logger.warning(f"pHash 计算失败 {frame.name}: {e}")
                        seen_md5[digest] = frame
                        unique.append(frame)
                else:
                    # 仅 MD5 去重
                    seen_md5[digest] = frame
                    unique.append(frame)

            except Exception as e:
                self.logger.warning(f"帧去重失败 {frame.name}: {e}")
                continue

        self.logger.info(
            f"去重结果: 原始 {len(frames)} 帧 → 保留 {len(unique)} 帧 (移除 {removed_count} 帧)"
        )
        return unique

    def _limit_frames(self, frames: Sequence[Path], limit: int) -> List[Path]:
        """限制帧数.

        Args:
            frames: 帧文件路径列表
            limit: 最大帧数

        Returns:
            限制后的帧列表
        """
        if len(frames) <= limit:
            return list(frames)
        return self._evenly_sample(list(frames), limit)

    def _evenly_sample(self, items: Sequence[Path], target: int) -> List[Path]:
        """均匀采样.

        Args:
            items: 项目列表
            target: 目标数量

        Returns:
            采样后的列表
        """
        if not items:
            return []
        if len(items) <= target:
            return list(items)

        step = (len(items) - 1) / (target - 1)
        selected = []
        for i in range(target):
            idx = int(round(i * step))
            selected.append(items[idx])

        # 去重保持顺序
        seen = set()
        ordered = []
        for item in selected:
            if item not in seen:
                ordered.append(item)
                seen.add(item)
        return ordered
