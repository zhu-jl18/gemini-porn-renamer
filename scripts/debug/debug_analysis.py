"""分析模块调试脚本

用法：
    python scripts/debug/debug_analysis.py path/to/frames_dir [--mock]
    
功能：
    - 测试两层并发策略
    - 验证子任务配置加载
    - 测试提示词加载
    - 模拟或真实 LLM 调用
    - 输出详细并发日志
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.services.analysis import AnalysisService


class MockLLMClient:
    """Mock LLM 客户端（用于测试）."""

    async def classify(self, prompt, images, **kwargs):
        """模拟分类响应."""
        import random

        await asyncio.sleep(0.1)  # 模拟网络延迟
        labels = ["标签A", "标签B", "标签C"]
        return f'{{"labels": ["{random.choice(labels)}"], "confidence": 0.95}}'

    async def generate(self, prompt, **kwargs):
        """模拟生成响应."""
        await asyncio.sleep(0.1)
        return '{"names": ["候选1", "候选2", "候选3"]}'


async def main(frames_dir: Path, use_mock: bool = False):
    """主函数."""
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()

    print("=" * 60)
    print("分析模块调试（两层并发）")
    print("=" * 60)

    # 创建 LLM 客户端
    if use_mock:
        print("\n使用 Mock LLM 客户端（无需真实 API）")
        llm_client = MockLLMClient()
    else:
        print("\n使用真实 LLM 客户端")
        llm_client = LLMClientFactory.create(config, logger)

    # 创建分析服务
    service = AnalysisService(llm_client, config, logger)

    # 加载帧
    frames = sorted(frames_dir.glob("*.jpg"))
    print(f"加载 {len(frames)} 个帧文件")

    if not frames:
        print(f"错误: 目录中没有 .jpg 文件: {frames_dir}")
        return

    # 进度回调
    def progress_callback(task_id, status, data):
        if status == "batch_done":
            print(
                f"  [{task_id}] 批次 {data['batch_idx']+1}/{data['total_batches']} 完成: {data.get('labels', [])}"
            )
        elif status == "error":
            print(f"  [{task_id}] 错误: {data.get('error')}")

    # 执行分析
    print("\n开始分析（两层并发）...")
    print(f"  第一层并发: {config.concurrency.task_concurrency} 个子任务")
    print(f"  第二层并发: {config.concurrency.batch_concurrency} 个批次")
    print()

    try:
        result = await service.analyze_video(
            frames=frames, progress_callback=progress_callback
        )

        # 输出结果
        print("\n" + "=" * 60)
        print("分析结果：")
        print("=" * 60)
        for task_id, labels in result.items():
            print(f"  {task_id}: {labels}")

        print(f"\n✅ 分析模块测试完成")

    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_analysis.py <frames_dir> [--mock]")
        print("示例: python debug_analysis.py frames/video_name")
        print("      python debug_analysis.py frames/video_name --mock")
        sys.exit(1)

    frames_dir = Path(sys.argv[1])
    if not frames_dir.exists():
        print(f"错误: 目录不存在: {frames_dir}")
        sys.exit(1)

    use_mock = "--mock" in sys.argv

    asyncio.run(main(frames_dir, use_mock))
