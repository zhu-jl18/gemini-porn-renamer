"""JSON 解析工具 - 宽松的 JSON 解析，支持多种格式."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


def parse_json_loose(text: str) -> Optional[Any]:
    """宽松的 JSON 解析 - 尝试多种策略提取 JSON.

    策略：
    1. 尝试直接解析整个文本
    2. 提取第一个 JSON 数组 [...]
    3. 提取第一个 JSON 对象 {...}

    Args:
        text: 待解析的文本

    Returns:
        解析后的 Python 对象（dict/list/等），如果无法解析则返回 None

    Examples:
        >>> parse_json_loose('{"key": "value"}')
        {'key': 'value'}
        >>> parse_json_loose('Some text [1, 2, 3] more text')
        [1, 2, 3]
        >>> parse_json_loose('Invalid text')
        None
    """
    text = text.strip()
    if not text:
        return None

    # 尝试多种候选
    candidates = [
        text,  # 完整文本
        _extract_json_block(text, kind="array"),  # 提取数组
        _extract_json_block(text, kind="object"),  # 提取对象
    ]

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def _extract_json_block(s: str, kind: str) -> Optional[str]:
    """从文本中提取 JSON 块.

    Args:
        s: 源文本
        kind: JSON 类型（"array" 或 "object"）

    Returns:
        提取的 JSON 字符串，如果未找到则返回 None
    """
    if kind == "array":
        pattern = r"\[.*?\]"
    else:
        pattern = r"\{.*?\}"

    match = re.search(pattern, s, flags=re.DOTALL)
    return match.group(0) if match else None

