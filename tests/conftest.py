"""pytest 配置和 fixtures."""

import pytest
from pathlib import Path
from vrenamer.core.config import AppConfig, LLMBackendConfig


@pytest.fixture
def mock_config():
    """Mock 配置."""
    config = AppConfig()
    # 使用测试配置
    config.llm_backend = "gemini"
    config.log_level = "DEBUG"
    return config


@pytest.fixture
def mock_llm_backend_config():
    """Mock LLM 后端配置."""
    return LLMBackendConfig(
        type="gemini",
        base_url="http://localhost:3001/proxy/free",
        api_key="test-key",
        transport="openai_compat",
    )


@pytest.fixture
def sample_video(tmp_path):
    """创建示例视频文件."""
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake video data")
    return video_path


@pytest.fixture
def sample_frames(tmp_path):
    """创建示例帧文件."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    frames = []
    for i in range(10):
        frame = frames_dir / f"frame_{i:05d}.jpg"
        frame.write_bytes(b"fake image data")
        frames.append(frame)

    return frames


@pytest.fixture
def sample_analysis_result():
    """示例分析结果."""
    return {
        "role_archetype": ["人妻"],
        "face_visibility": ["露脸"],
        "scene_type": ["办公室"],
        "positions": ["传教士"],
    }
