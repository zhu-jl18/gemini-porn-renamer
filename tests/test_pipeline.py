from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from vrenamer.webui.services import pipeline


def test_generate_names_with_styles_uses_adapter(monkeypatch):
    class DummyClient:
        calls = 0

        def __init__(self, *args, **kwargs):
            pass

        async def classify_json(
            self,
            model,
            system_prompt,
            user_text,
            images,
            response_json=True,
            temperature=0.0,
            extra=None,
        ):
            return '{"labels": [], "confidence": 0.0}'

        async def name_candidates(
            self,
            model,
            system_prompt,
            user_text,
            temperature=0.0,
            json_array=True,
        ):
            DummyClient.calls += 1
            return '{"names": ["测试<>文件", "次选"]}'

    monkeypatch.setattr(pipeline, "GeminiClient", DummyClient)

    class DummySettings:
        gemini_base_url = ""
        gemini_api_key = ""
        llm_transport = "openai_compat"
        request_timeout = 5
        model_flash = "flash"
        model_pro = "pro"
        naming_styles = "chinese_descriptive"
        naming_style_config = "examples/naming_styles.yaml"
        candidates_per_style = 2

        def get_style_ids(self):
            return ["chinese_descriptive"]

        def get_style_config_path(self) -> Path:
            return Path(self.naming_style_config)

    tags = {
        "category": "剧情",
        "scene": "温泉",
        "description": "示例描述",
        "actors": ["演员A"],
    }

    result = asyncio.run(pipeline.generate_names_with_styles(tags, DummySettings()))

    assert DummyClient.calls == 1
    assert result
    assert "测试__文件" == result[0]["filename"]
    assert all(item["filename"] for item in result)


def test_analyze_tasks_respects_batches(tmp_path, monkeypatch):
    frames = []
    for i in range(12):
        frame = tmp_path / f"frame_{i:05d}.jpg"
        frame.write_bytes(b"x")
        frames.append(frame)

    class DummyClient:
        calls = []

        def __init__(self, *args, **kwargs):
            pass

        async def classify_json(
            self,
            model,
            system_prompt,
            user_text,
            images,
            response_json=True,
            temperature=0.0,
            extra=None,
        ):
            DummyClient.calls.append(len(images))
            return '{"labels": ["标签"], "confidence": 0.9}'

        async def name_candidates(
            self,
            model,
            system_prompt,
            user_text,
            temperature=0.0,
            json_array=True,
        ):
            return '{"names": []}'

    monkeypatch.setattr(pipeline, "GeminiClient", DummyClient)

    settings = SimpleNamespace(
        gemini_base_url="",
        gemini_api_key="",
        llm_transport="openai_compat",
        request_timeout=5,
        model_flash="flash",
        model_pro="pro",
        max_concurrency=4,
        analysis_batch_size=20,  # 新增：从配置读取的批次大小
    )

    frame_result = pipeline.FrameSampleResult(directory=tmp_path, frames=frames)
    task_prompts = {"role": "p1", "scene": "p2"}

    tags, batches = asyncio.run(pipeline.analyze_tasks(frame_result, task_prompts, settings))

    assert all(tags[key][0] == "标签" for key in task_prompts)
    assert DummyClient.calls
    # 批次大小从 5 改为 20，但测试只有 12 帧，所以每个任务只有 1 批次（6 帧）
    assert max(DummyClient.calls) <= 20  # 更新：batch_size 现在是 20
    assert sum(DummyClient.calls) == sum(len(batch) for batch in batches.values())


def test_generate_names_json_fallback(monkeypatch):
    payload = (
        '{"choices":[{"message":{"content":"noise {\\"names\\": [\\"Alpha\\", \\"Beta\\", \\"Gamma\\"]} tail"}}]}'
    )

    class DummyResponse:
        status = 200
        headers = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        async def read(self):
            return payload.encode("utf-8")

    class DummySession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr("vrenamer.llm.client.aiohttp.ClientSession", DummySession)

    settings = SimpleNamespace(
        gemini_base_url="http://example.com",
        gemini_api_key="key",
        llm_transport="openai_compat",
        request_timeout=5,
        model_pro="model",
    )

    result = asyncio.run(pipeline.generate_names("prompt", settings, 2))

    assert result == ["Alpha", "Beta"]
