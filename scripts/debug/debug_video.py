"""视频处理模块调试脚本

用法：
    python scripts/debug/debug_video.py path/to/video.mp4
    
功能：
    - 测试视频抽帧
    - 验证 ffmpeg 可用性
    - 检查帧去重逻辑
    - 输出详细日志
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrenamer.core.logging import AppLogger
from vrenamer.services.video import VideoProcessor


async def main(video_path: Path):
    """主函数."""
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    processor = VideoProcessor(logger)

    print("=" * 60)
    print("视频处理模块调试")
    print("=" * 60)

    print(f"\n[1/3] 检查视频时长...")
    try:
        duration = processor.get_duration(video_path)
        print(f"  ✓ 时长: {duration:.2f} 秒")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return

    print(f"\n[2/3] 抽取视频帧...")
    try:
        result = await processor.sample_frames(video_path, target_frames=96)
        print(f"  ✓ 抽取帧数: {len(result.frames)}")
        print(f"  ✓ 保存目录: {result.directory}")
        print(f"  ✓ 抽帧帧率: {result.fps:.4f} fps")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return

    print(f"\n[3/3] 验证帧文件...")
    for i, frame in enumerate(result.frames[:5], 1):
        size_kb = frame.stat().st_size / 1024
        print(f"  {i}. {frame.name} ({size_kb:.2f} KB)")

    if len(result.frames) > 5:
        print(f"  ... 还有 {len(result.frames) - 5} 个帧文件")

    print(f"\n✅ 视频处理模块测试完成")
    print(f"总帧数: {len(result.frames)}")
    print(f"帧目录: {result.directory}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_video.py <video_path>")
        print("示例: python debug_video.py test.mp4")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"错误: 文件不存在: {video_path}")
        sys.exit(1)

    asyncio.run(main(video_path))
