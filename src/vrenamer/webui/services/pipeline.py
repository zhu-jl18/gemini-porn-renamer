from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Sequence

from vrenamer.webui.settings import Settings
from vrenamer.webui.services.prompting import compose_task_prompts, compose_name_prompt
from vrenamer.llm.client import GeminiClient
from vrenamer.llm.json_utils import parse_json_loose
from vrenamer.naming import NamingGenerator, NamingStyleConfig


@dataclass
class FrameSampleResult:
    """视频抽帧结果."""

    directory: Path
    frames: List[Path]


async def run_single(video_path: Path, user_prompt: str, n_candidates: int, settings: Settings) -> Dict[str, Any]:
    frame_result = await sample_frames(video_path)
    transcript = extract_transcript(settings, video_path)
    task_prompts = compose_task_prompts(
        frame_result.directory,
        transcript,
        user_prompt,
        frames=frame_result.frames,
    )
    tags, batches = await analyze_tasks(frame_result, task_prompts, settings)
    name_prompt = compose_name_prompt(tags, user_prompt, n_candidates)
    candidates = await generate_names(name_prompt, settings, int(n_candidates))
    return {
        "frames": [p.name for p in frame_result.frames[:12]],
        "transcript": transcript[:8000],
        "task_prompts": task_prompts,
        "name_prompt": name_prompt,
        "candidates": candidates,
        "frame_batches": {k: [p.name for p in v] for k, v in batches.items()},
    }


async def sample_frames(video_path: Path) -> FrameSampleResult:
    """抽帧并返回代表性帧列表."""

    frames_root = video_path.parent / "frames"
    frames_dir = frames_root / video_path.stem
    frames_dir.mkdir(parents=True, exist_ok=True)

    for existing in frames_dir.glob("*.jpg"):
        try:
            existing.unlink()
        except Exception:
            continue

    duration = _probe_duration(video_path)
    fps = _decide_sampling_fps(duration)
    target_max = 96

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
        str(frames_dir / "frame_%05d.jpg"),
    ]

    try:
        subprocess.run(cmd, check=True)
    except Exception:
        pass

    frames = sorted(frames_dir.glob("*.jpg"))
    frames = _deduplicate_frames(frames)
    frames = _limit_frames(frames, target_max)

    return FrameSampleResult(directory=frames_dir, frames=frames)


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


async def analyze_tasks(
    frame_result: FrameSampleResult,
    task_prompts: Dict[str, str],
    settings: Settings,
) -> tuple[Dict[str, Any], Dict[str, List[Path]]]:
    client = GeminiClient(
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        transport=settings.llm_transport,
        timeout=settings.request_timeout,
    )
    frames = frame_result.frames
    batches = _build_frame_batches(frames, list(task_prompts.keys()))

    semaphore = asyncio.Semaphore(settings.max_concurrency or 1)

    async def _one(key: str, prompt: str, batch: List[Path]) -> tuple[str, Any]:
        payload = batch if batch else frames[:8]
        if len(payload) < 3 and frames:
            payload = _evenly_sample(frames, 3)

        async with semaphore:
            raw = await client.classify_json(
                model=settings.model_flash,
                system_prompt="严格输出JSON，不得多余文本。",
                user_text=prompt,
                images=payload,
                response_json=True,
                temperature=0.1,
                extra={"max_output_tokens": 512},
            )
        data = parse_json_loose(raw)
        safe = data or {"labels": ["未知"], "confidence": 0.0}
        return key, safe

    tasks = [_one(key, prompt, batches.get(key, [])) for key, prompt in task_prompts.items()]
    results_pairs = await asyncio.gather(*tasks)
    results: Dict[str, Any] = {key: value for key, value in results_pairs}

    tags = {k: (results[k].get("labels") or ["未知"]) for k in results}
    return tags, batches


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


def _probe_duration(video_path: Path) -> float:
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
        return max(1.0, float(result.stdout.strip()))
    except Exception:
        return 180.0


def _decide_sampling_fps(duration: float) -> float:
    if duration <= 120:
        target = 48
    elif duration <= 300:
        target = 64
    elif duration <= 900:
        target = 80
    else:
        target = 96
    fps = target / duration
    return max(0.1, min(6.0, fps))


def _deduplicate_frames(frames: Sequence[Path]) -> List[Path]:
    seen: Dict[str, Path] = {}
    unique: List[Path] = []
    for frame in frames:
        try:
            digest = hashlib.md5(frame.read_bytes()).hexdigest()
        except Exception:
            continue
        if digest in seen:
            try:
                frame.unlink()
            except Exception:
                pass
            continue
        seen[digest] = frame
        unique.append(frame)
    return unique


def _limit_frames(frames: Sequence[Path], limit: int) -> List[Path]:
    if len(frames) <= limit:
        return list(frames)
    return _evenly_sample(list(frames), limit)


def _evenly_sample(items: Sequence[Path], target: int) -> List[Path]:
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
    seen: set[Path] = set()
    ordered: List[Path] = []
    for item in selected:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _build_frame_batches(frames: Sequence[Path], keys: Sequence[str], min_batch: int = 3, max_batch: int = 8) -> Dict[str, List[Path]]:
    frames = list(frames)
    if not frames or not keys:
        return {k: [] for k in keys}

    batches: Dict[str, List[Path]] = {k: [] for k in keys}
    num_batches = len(keys)

    # 初始轮转分配，保证覆盖时间轴
    for idx, frame in enumerate(frames):
        target_key = keys[idx % num_batches]
        batches[target_key].append(frame)

    total_frames = len(frames)
    base = max(min_batch, min(max_batch, total_frames // num_batches or min_batch))
    leftover = max(0, total_frames - base * num_batches)

    for idx, key in enumerate(keys):
        desired = base + (1 if idx < leftover and base < max_batch else 0)
        desired = max(min_batch, min(max_batch, desired))
        batches[key] = _evenly_sample(batches[key], desired)

    return batches
