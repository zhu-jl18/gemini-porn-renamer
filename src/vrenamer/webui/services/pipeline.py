from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from vrenamer.webui.settings import Settings
from vrenamer.webui.services.prompting import compose_task_prompts, compose_name_prompt
from vrenamer.llm.client import GeminiClient
from vrenamer.llm.json_utils import parse_json_loose
from vrenamer.naming import NamingGenerator, NamingStyleConfig


async def run_single(video_path: Path, user_prompt: str, n_candidates: int, settings: Settings) -> Dict[str, Any]:
    frames_dir = await sample_frames(video_path)
    transcript = extract_transcript(settings, video_path)
    task_prompts = compose_task_prompts(frames_dir, transcript, user_prompt)
    tags = await analyze_tasks(frames_dir, task_prompts, settings)
    name_prompt = compose_name_prompt(tags, user_prompt, n_candidates)
    candidates = await generate_names(name_prompt, settings, int(n_candidates))
    return {
        "frames": sorted([p.name for p in frames_dir.glob("*.jpg")])[:12],
        "transcript": transcript[:8000],
        "task_prompts": task_prompts,
        "name_prompt": name_prompt,
        "candidates": candidates,
    }


async def sample_frames(video_path: Path) -> Path:
    frames_dir = video_path.parent / "frames"
    frames_dir.mkdir(exist_ok=True)
    # Every 5 seconds one frame; keep at most 24 frames
    # ffmpeg -i input -vf fps=1/5,scale=640:-1 -frames:v 24 out_%03d.jpg
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        "fps=1/5,scale=640:-1",
        "-frames:v",
        "24",
        str(frames_dir / "frame_%03d.jpg"),
    ]
    try:
        subprocess.run(cmd, check=True)
    except Exception:
        # best-effort; ignore if ffmpeg not installed
        pass
    return frames_dir


def extract_transcript(settings: Settings, video_path: Path) -> str:
    # Minimal placeholder; in real impl, call faster-whisper on extracted audio
    # ffmpeg -i input -vn -ac 1 -ar 16000 -f wav audio.wav
    return ""


async def analyze_tasks_stub() -> Dict[str, Any]:
    # 占位：返回伪标签，便于前后端打通
    return {
        "role_archetype": ["人妻"],
        "face_visibility": ["露脸"],
        "scene_type": ["做爱"],
        "positions": ["传教士", "后入"],
    }


async def analyze_tasks(frames_dir: Path, task_prompts: Dict[str, str], settings: Settings) -> Dict[str, Any]:
    client = GeminiClient(
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        transport=settings.llm_transport,
        timeout=settings.request_timeout,
    )
    # Use up to 8 frames for latency
    frames = sorted(frames_dir.glob("*.jpg"))[:8]

    async def _one(key: str, prompt: str) -> Any:
        raw = await client.classify_json(
            model=settings.model_flash,
            system_prompt="严格输出JSON，不得多余文本。",
            user_text=prompt,
            images=frames,
            response_json=True,
            temperature=0.1,
            extra={"max_output_tokens": 512},
        )
        data = parse_json_loose(raw)
        return data or {"labels": ["未知"], "confidence": 0.0}

    results: Dict[str, Any] = {}
    for k, v in task_prompts.items():
        results[k] = await _one(k, v)

    # Normalize to tag lists
    tags = {k: (results[k].get("labels") or ["未知"]) for k in results}
    return tags


async def generate_names(name_prompt: str, settings: Settings, n: int) -> list:
    client = GeminiClient(
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        transport=settings.llm_transport,
        timeout=settings.request_timeout,
    )
    raw = await client.name_candidates(
        model=settings.model_pro,
        system_prompt="仅输出JSON数组，元素为字符串。",
        user_text=name_prompt,
        temperature=0.3,
        json_array=True,
    )
    data = parse_json_loose(raw)
    if isinstance(data, list):
        return [str(x) for x in data][:n]
    if isinstance(data, dict) and isinstance(data.get("names"), list):
        return [str(x) for x in data["names"]][:n]
    # Fallback
    return [f"候选_{i+1}" for i in range(n)]


async def generate_names_with_styles(
    tags: Dict[str, Any],
    settings: Settings,
    style_ids: Optional[List[str]] = None,
    n_per_style: Optional[int] = None,
) -> List[Dict[str, str]]:
    """使用命名风格系统生成候选名称.

    Args:
        tags: 视频分析标签
        settings: 配置
        style_ids: 指定的风格 ID 列表（None 则用配置默认值）
        n_per_style: 每个风格的候选数（None 则用配置默认值）

    Returns:
        候选名称列表，每个元素包含 {style_id, style_name, filename, language}
    """
    # 加载风格配置
    config_path = settings.get_style_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Style config not found: {config_path}")

    style_config = NamingStyleConfig.from_yaml(config_path)

    # 创建 LLM 客户端
    client = GeminiClient(
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        transport=settings.llm_transport,
        timeout=settings.request_timeout,
    )

    # 创建生成器
    generator = NamingGenerator(
        llm_client=client,
        style_config=style_config,
        model=settings.model_pro,
    )

    # 使用设置的风格或默认值
    if style_ids is None:
        style_ids = settings.get_style_ids()

    if n_per_style is None:
        n_per_style = settings.candidates_per_style

    # 生成候选
    candidates = await generator.generate_candidates(
        analysis=tags,
        style_ids=style_ids,
        n_per_style=n_per_style,
    )

    # 转换为字典列表
    return [
        {
            "style_id": c.style_id,
            "style_name": c.style_name,
            "filename": c.filename,
            "language": c.language,
        }
        for c in candidates
    ]


async def store_feedback(selected_name: str, context: str) -> None:
    out = Path("logs")
    out.mkdir(exist_ok=True)
    with open(out / "feedback.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"name": selected_name, "context": context}, ensure_ascii=False) + "\n")
