"""测试命名风格配置加载."""

from pathlib import Path

import pytest

from vrenamer.naming.styles import NamingStyleConfig


def test_load_default_config():
    """测试加载默认配置文件."""
    config_path = Path("examples/naming_styles.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")

    config = NamingStyleConfig.from_yaml(config_path)

    # 验证结构
    assert config.styles is not None
    assert len(config.styles) > 0
    assert config.default is not None

    # 验证内置风格
    assert "chinese_descriptive" in config.styles
    assert "scene_role" in config.styles
    assert "pornhub_style" in config.styles

    # 验证默认配置
    assert len(config.default.selected_styles) > 0
    assert config.default.max_length == 80


def test_get_style():
    """测试获取风格定义."""
    config_path = Path("examples/naming_styles.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")

    config = NamingStyleConfig.from_yaml(config_path)

    # 获取存在的风格
    style = config.get_style("chinese_descriptive")
    assert style is not None
    assert style.name == "中文描述性"
    assert style.language == "zh"
    assert len(style.examples) > 0

    # 获取不存在的风格
    style = config.get_style("nonexistent")
    assert style is None


def test_validate_styles():
    """测试风格验证."""
    config_path = Path("examples/naming_styles.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")

    config = NamingStyleConfig.from_yaml(config_path)

    # 验证有效风格
    valid = config.validate_styles(["chinese_descriptive", "scene_role"])
    assert len(valid) == 2
    assert "chinese_descriptive" in valid
    assert "scene_role" in valid

    # 过滤无效风格
    valid = config.validate_styles(["chinese_descriptive", "invalid", "scene_role"])
    assert len(valid) == 2
    assert "invalid" not in valid


def test_sanitize_filename():
    """测试文件名清理."""
    config_path = Path("examples/naming_styles.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")

    config = NamingStyleConfig.from_yaml(config_path)

    # 测试非法字符替换
    name = config.sanitize_filename('温泉旅馆的诱惑<>:"/\\|?*')
    assert "<" not in name
    assert ">" not in name
    assert ":" not in name
    assert '"' not in name
    assert "/" not in name
    assert "\\" not in name
    assert "|" not in name
    assert "?" not in name
    assert "*" not in name

    # 测试空白压缩
    name = config.sanitize_filename("温泉   旅馆   的   诱惑")
    assert "   " not in name

    # 测试长度限制
    long_name = "A" * 100
    name = config.sanitize_filename(long_name)
    assert len(name) <= config.default.max_length


def test_list_available_styles():
    """测试列出可用风格."""
    config_path = Path("examples/naming_styles.yaml")
    if not config_path.exists():
        pytest.skip("Config file not found")

    config = NamingStyleConfig.from_yaml(config_path)

    styles = config.list_available_styles()
    assert len(styles) > 0
    assert "chinese_descriptive" in styles
    assert "scene_role" in styles
