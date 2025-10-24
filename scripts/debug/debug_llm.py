"""LLM 客户端调试脚本

用法：
    python scripts/debug/debug_llm.py --backend gemini --test generate
    python scripts/debug/debug_llm.py --backend openai --test classify
    
功能：
    - 测试不同 LLM 后端
    - 验证 API 连接
    - 测试响应解析
    - 对比不同后端的输出
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger
from vrenamer.llm.factory import LLMClientFactory


async def test_generate(client):
    """测试生成任务."""
    print("\n[测试] 生成任务...")
    print("-" * 60)

    prompt = """请生成 3 个创意文件名，输出 JSON 格式：
{"names": ["文件名1", "文件名2", "文件名3"]}

要求：
- 文件名应该简洁、有创意
- 不要包含文件扩展名
"""

    try:
        response = await client.generate(prompt=prompt, response_format="json")
        print(f"响应长度: {len(response)} 字符")
        print(f"响应内容:\n{response}")
        print("\n✓ 生成任务测试成功")
    except Exception as e:
        print(f"\n✗ 生成任务测试失败: {e}")
        import traceback

        traceback.print_exc()


async def test_classify(client, test_images: list):
    """测试分类任务."""
    print("\n[测试] 分类任务（多模态）...")
    print("-" * 60)

    if not test_images:
        print("警告: 没有提供测试图片，跳过分类测试")
        print("请在 tests/fixtures 目录下放置测试图片")
        return

    prompt = """请识别图片中的物体，输出 JSON 格式：
{"labels": ["物体1", "物体2", ...], "confidence": 0.95}

要求：
- labels 数组包含 1-3 个最相关的标签
- confidence 为 0-1 之间的浮点数
"""

    try:
        response = await client.classify(
            prompt=prompt, images=test_images[:3], response_format="json"
        )
        print(f"使用图片数: {len(test_images[:3])}")
        print(f"响应长度: {len(response)} 字符")
        print(f"响应内容:\n{response}")
        print("\n✓ 分类任务测试成功")
    except Exception as e:
        print(f"\n✗ 分类任务测试失败: {e}")
        import traceback

        traceback.print_exc()


async def main(backend: str, test_type: str):
    """主函数."""
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()

    print("=" * 60)
    print("LLM 客户端调试")
    print("=" * 60)

    # 设置后端
    config.llm_backend = backend
    print(f"\n使用后端: {backend}")

    try:
        client = LLMClientFactory.create(config, logger)
        print(f"✓ 客户端创建成功: {type(client).__name__}")
    except Exception as e:
        print(f"✗ 客户端创建失败: {e}")
        return

    # 执行测试
    if test_type == "generate":
        await test_generate(client)
    elif test_type == "classify":
        # 查找测试图片
        test_images = list(Path("tests/fixtures").glob("*.jpg"))
        if not test_images:
            # 尝试从 frames 目录查找
            frames_dirs = list(Path(".").glob("frames/*/"))
            if frames_dirs:
                test_images = list(frames_dirs[0].glob("*.jpg"))

        await test_classify(client, test_images)
    elif test_type == "both":
        await test_generate(client)
        test_images = list(Path("tests/fixtures").glob("*.jpg"))
        await test_classify(client, test_images)
    else:
        print(f"未知测试类型: {test_type}")

    print("\n" + "=" * 60)
    print("✅ LLM 客户端测试完成")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM 客户端调试脚本")
    parser.add_argument(
        "--backend", default="gemini", choices=["gemini", "openai"], help="LLM 后端"
    )
    parser.add_argument(
        "--test",
        default="generate",
        choices=["generate", "classify", "both"],
        help="测试类型",
    )
    args = parser.parse_args()

    asyncio.run(main(args.backend, args.test))
