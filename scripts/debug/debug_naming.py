"""命名模块调试脚本

用法：
    python scripts/debug/debug_naming.py --tags '{"role_archetype": ["人妻"], "scene_type": ["办公室"]}'
    python scripts/debug/debug_naming.py --tags '{"role_archetype": ["人妻"]}' --styles chinese_descriptive,scene_role
    
功能：
    - 测试命名风格加载
    - 测试提示词构建
    - 测试候选生成
    - 验证文件名清理
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.services.naming import NamingService


async def main(tags: dict, styles: list = None):
    """主函数."""
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()

    print("=" * 60)
    print("命名模块调试")
    print("=" * 60)

    print(f"\n输入标签: {json.dumps(tags, ensure_ascii=False, indent=2)}")
    print(f"使用风格: {styles or config.naming.styles}")

    # 创建服务
    llm_client = LLMClientFactory.create(config, logger)
    service = NamingService(llm_client, config, logger)

    print("\n生成候选名称...")
    try:
        candidates = await service.generate_candidates(
            analysis=tags, style_ids=styles
        )

        print(f"\n生成 {len(candidates)} 个候选：")
        print("=" * 60)
        for i, c in enumerate(candidates, 1):
            print(f"{i}. [{c['style_name']}] {c['filename']} ({c['language']})")

        print(f"\n✅ 命名模块测试完成")

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="命名模块调试脚本")
    parser.add_argument("--tags", required=True, help="分析标签 JSON")
    parser.add_argument("--styles", help="命名风格（逗号分隔）")
    args = parser.parse_args()

    try:
        tags = json.loads(args.tags)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的 JSON 格式: {e}")
        print("示例: --tags '{\"role_archetype\": [\"人妻\"], \"scene_type\": [\"办公室\"]}'")
        sys.exit(1)

    styles = args.styles.split(",") if args.styles else None

    asyncio.run(main(tags, styles))
