from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Sequence

from asyncio.subprocess import PIPE, create_subprocess_exec

from vrenamer.webui.settings import Settings
from vrenamer.webui.services.prompting import compose_task_prompts, compose_name_prompt
from vrenamer.llm.adapter import GeminiLLMAdapter
from vrenamer.llm.client import GeminiClient
from vrenamer.llm.json_utils import parse_json_loose
from vrenamer.naming import NamingGenerator, NamingStyleConfig


_FFMPEG_PATH: Optional[str] = None
_FFPROBE_PATH: Optional[str] = None
_FFMPEG_LOCK = asyncio.Lock()
_FFPROBE_LOCK = asyncio.Lock()


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


async def _check_ffmpeg() -> str:
    """检查 ffmpeg 是否可用，返回可执行文件路径."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH:
        return _FFMPEG_PATH
    async with _FFMPEG_LOCK:
        if _FFMPEG_PATH:
            return _FFMPEG_PATH
        ffmpeg_path = await asyncio.to_thread(shutil.which, "ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError(
                "未找到 ffmpeg 命令！\n\n"
                "请安装 ffmpeg：\n"
                "  Windows: 从 https://ffmpeg.org/download.html 下载，或使用 chocolatey: choco install ffmpeg\n"
                "  或使用 scoop: scoop install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg  或  sudo yum install ffmpeg\n"
                "  macOS: brew install ffmpeg\n\n"
                "安装后请确保 ffmpeg 在 PATH 环境变量中。"
            )
        _FFMPEG_PATH = ffmpeg_path
        return ffmpeg_path


async def _check_ffprobe() -> str:
    """检查 ffprobe 是否可用，返回可执行文件路径."""
    global _FFPROBE_PATH
    if _FFPROBE_PATH:
        return _FFPROBE_PATH
    async with _FFPROBE_LOCK:
        if _FFPROBE_PATH:
            return _FFPROBE_PATH
        ffprobe_path = await asyncio.to_thread(shutil.which, "ffprobe")
        if not ffprobe_path:
            raise RuntimeError(
                "未找到 ffprobe 命令！\n\n"
                "ffprobe 通常随 ffmpeg 一起安装。\n"
                "请参考 ffmpeg 的安装说明。"
            )
        _FFPROBE_PATH = ffprobe_path
        return ffprobe_path


async def sample_frames(video_path: Path) -> FrameSampleResult:
    """抽帧并返回代表性帧列表."""

    # 检查 ffmpeg 是否可用
    ffmpeg_cmd = await _check_ffmpeg()

    frames_root = video_path.parent / "frames"
    frames_dir = frames_root / video_path.stem
    frames_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧帧
    for existing in frames_dir.glob("*.jpg"):
        try:
            existing.unlink()
        except Exception:
            continue

    # 获取视频时长
    duration = await _probe_duration(video_path)
    fps = _decide_sampling_fps(duration)
    target_max = 96

    # 构建 ffmpeg 命令
    cmd = [
        ffmpeg_cmd,
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

    print(f"  → 执行命令: {' '.join(cmd)}")

    # 执行抽帧命令
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✓ ffmpeg 执行成功")
        if result.stderr:
            print(f"  [dim]stderr: {result.stderr[:200]}[/]")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ ffmpeg 执行失败:")
        print(f"    返回码: {e.returncode}")
        print(f"    stderr: {e.stderr}")
        raise RuntimeError(f"视频抽帧失败: {e.stderr}") from e
    except Exception as e:
        print(f"  ✗ 未知错误: {e}")
        raise

    # 收集生成的帧
    frames = sorted(frames_dir.glob("*.jpg"))
    print(f"  → 原始帧数: {len(frames)}")

    if not frames:
        raise RuntimeError(f"抽帧失败：未生成任何帧文件。目录: {frames_dir}")

    # 去重和限制
    frames = _deduplicate_frames(frames)
    print(f"  → 去重后: {len(frames)} 帧")

    frames = _limit_frames(frames, target_max)
    print(f"  → 最终采样: {len(frames)} 帧 (最大 {target_max})")

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
    progress_callback=None,
) -> tuple[Dict[str, Any], Dict[str, List[Path]]]:
    """分析视频任务.

    Args:
        frame_result: 帧采样结果
        task_prompts: 任务提示词字典
        settings: 设置
        progress_callback: 进度回调函数，接收 (task_key, status, result) 参数

    Returns:
        (标签字典, 帧批次字典)
    """
    client = GeminiClient(
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key,
        transport=settings.llm_transport,
        timeout=settings.request_timeout,
    )
    frames = frame_result.frames
    frame_assignments = _build_frame_batches(frames, list(task_prompts.keys()))

    semaphore = asyncio.Semaphore(settings.max_concurrency or 1)
    completed_count = 0
    total_count = len(task_prompts)

    async def _one(key: str, prompt: str, batch: List[Path]) -> tuple[str, Any]:
        nonlocal completed_count

        # 使用预分配的帧；若为空则回退为全量
        available_frames = list(batch) if batch else list(frames)
        print(f"    [INFO] {key}: 使用 {len(available_frames)} 帧进行分批分析")

        # 通知开始
        if progress_callback:
            progress_callback(key, "start", {"frames": len(available_frames)})

        # 打乱帧顺序（每个子任务独立打乱，增加多样性）
        import random
        shuffled_frames = available_frames.copy()
        random.shuffle(shuffled_frames)

        # 计算批次：每批5帧（Gemini限制）
        IMAGES_PER_CALL = 5
        frame_chunks = [
            shuffled_frames[i : i + IMAGES_PER_CALL]
            for i in range(0, len(shuffled_frames), IMAGES_PER_CALL)
        ]
        num_calls = len(frame_chunks)
        frames_used = sum(len(chunk) for chunk in frame_chunks)

        print(f"    [INFO] {key}: 打乱后分成 {num_calls} 批，每批 ≤ {IMAGES_PER_CALL} 帧")
        print(f"    [INFO] {key}: 总计将使用 {frames_used} 帧（覆盖率 {frames_used}/{len(available_frames)}）")

        # 定义单批次调用函数
        async def _call_one_batch(batch_idx: int, frame_batch: List[Path]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    print(f"      [DEBUG] {key} 批次{batch_idx+1}/{num_calls}: 调用模型 ({len(frame_batch)} 帧)")

                    raw = await client.classify_json(
                        model=settings.model_flash,
                        system_prompt="严格输出JSON，不得多余文本。",
                        user_text=prompt,
                        images=frame_batch,
                        response_json=True,
                        temperature=0.1,
                        extra={"max_output_tokens": 512},
                    )
                    data = parse_json_loose(raw)
                    result = data or {"labels": [], "confidence": 0.0}
                    print(f"      [SUCCESS] {key} 批次{batch_idx+1}: 返回 {len(result.get('labels', []))} 个标签")
                    return result
                except Exception as e:
                    print(f"      [ERROR] {key} 批次{batch_idx+1} 失败: {e}")
                    return {"labels": [], "confidence": 0.0, "error": str(e)}

        # 并发执行所有批次调用
        try:
            sub_results = await asyncio.gather(
                *[_call_one_batch(idx, chunk) for idx, chunk in enumerate(frame_chunks)],
                return_exceptions=False
            )

            # 汇总结果：收集所有labels并统计频率
            from collections import Counter
            all_labels = []
            all_confidences = []

            for result in sub_results:
                if result and isinstance(result, dict):
                    labels = result.get("labels", [])
                    if labels:
                        all_labels.extend(labels)
                    conf = result.get("confidence", 0.0)
                    if conf > 0:
                        all_confidences.append(conf)

            # 标签去重并按出现频率排序（取前3个最常见的）
            if all_labels:
                label_counts = Counter(all_labels)
                final_labels = [label for label, count in label_counts.most_common(3)]
            else:
                final_labels = ["未知"]

            # 计算平均置信度
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            final_result = {
                "labels": final_labels,
                "confidence": avg_confidence,
                "total_calls": num_calls,
                "total_frames_available": len(available_frames),
                "total_frames_used": frames_used,
            }

            print(f"    [SUCCESS] {key}: 汇总 {num_calls} 次调用 → {final_labels} (置信度: {avg_confidence:.2f})")

            # 通知完成
            completed_count += 1
            if progress_callback:
                progress_callback(
                    key,
                    "done",
                    {
                        "parsed": final_result,
                        "progress": f"{completed_count}/{total_count}",
                    },
                )

            return key, final_result

        except Exception as e:
            print(f"    [ERROR] {key}: 随机抽样分析失败: {e}")
            completed_count += 1
            if progress_callback:
                progress_callback(
                    key,
                    "error",
                    {"error": str(e), "progress": f"{completed_count}/{total_count}"},
                )
            return key, {"labels": ["错误"], "confidence": 0.0, "error": str(e)}

    tasks = [_one(key, prompt, frame_assignments.get(key, [])) for key, prompt in task_prompts.items()]
    results_pairs = await asyncio.gather(*tasks)
    results: Dict[str, Any] = {key: value for key, value in results_pairs}

    tags = {k: (results[k].get("labels") or ["未知"]) for k in results}
    return tags, frame_assignments


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
    llm_adapter = GeminiLLMAdapter(client, model_flash=settings.model_flash, model_pro=settings.model_pro)

    # 创建生成器
    generator = NamingGenerator(
        llm_client=llm_adapter,
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


async def _probe_duration(video_path: Path) -> float:
    """获取视频时长（秒）."""
    ffprobe_cmd = await _check_ffprobe()
    
    try:
        proc = await create_subprocess_exec(
            ffprobe_cmd,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"ffprobe exit {proc.returncode}: {err_text}")
        return max(1.0, float(stdout.decode("utf-8").strip()))
    except Exception as e:
        print(f"  [警告] 无法获取视频时长: {e}，使用默认值 180 秒")
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
    """去重：MD5 完全相同 + pHash 内容相似."""
    try:
        import imagehash
        from PIL import Image

        use_phash = True
        print(f"  [INFO] 去重算法: MD5 + pHash (汉明距离阈值 ≤ 5)")
    except ImportError:
        use_phash = False
        print(f"  [WARNING] imagehash 未安装，仅使用 MD5 去重")

    seen_md5: Dict[str, Path] = {}
    seen_phash: Dict[str, Path] = {}
    unique: List[Path] = []
    removed_count = 0

    for frame in frames:
        try:
            # 1. MD5 完全去重
            digest = hashlib.md5(frame.read_bytes()).hexdigest()
            if digest in seen_md5:
                try:
                    frame.unlink()
                    removed_count += 1
                except Exception:
                    pass
                continue

            # 2. pHash 相似度去重（可选）
            if use_phash:
                try:
                    img = Image.open(frame)
                    phash = imagehash.phash(img)

                    # 检查是否有相似帧
                    is_similar = False
                    for existing_hash in seen_phash.keys():
                        distance = imagehash.hex_to_hash(existing_hash) - phash
                        if distance <= 5:  # 汉明距离 ≤ 5 认为相似
                            is_similar = True
                            try:
                                frame.unlink()
                                removed_count += 1
                            except Exception:
                                pass
                            break

                    if not is_similar:
                        seen_md5[digest] = frame
                        seen_phash[str(phash)] = frame
                        unique.append(frame)
                except Exception as e:
                    # pHash 失败，仅用 MD5
                    print(f"  [WARNING] pHash 计算失败 {frame.name}: {e}")
                    seen_md5[digest] = frame
                    unique.append(frame)
            else:
                # 仅 MD5 去重
                seen_md5[digest] = frame
                unique.append(frame)

        except Exception as e:
            print(f"  [WARNING] 帧去重失败 {frame.name}: {e}")
            continue

    print(f"  [INFO] 去重结果: 原始 {len(frames)} 帧 → 保留 {len(unique)} 帧 (移除 {removed_count} 帧)")
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


def _build_frame_batches(
    frames: Sequence[Path],
    keys: Sequence[str],
    min_batch: int = 15,  # 提升：旧值 3
    max_batch: int = 20,  # 提升：旧值 8
) -> Dict[str, List[Path]]:
    """构建帧批次，大幅提升利用率到 70%+."""
    import random

    frames = list(frames)
    num_tasks = len(keys)

    print(f"\n  [INFO] ========== 帧分配策略 ==========")
    print(f"  [INFO] 总帧数: {len(frames)}, 任务数: {num_tasks}")
    print(f"  [INFO] 目标范围: 每任务 {min_batch}-{max_batch} 帧")

    if not frames or not keys:
        print(f"  [WARNING] 帧或任务为空，返回空批次")
        return {k: [] for k in keys}

    batches: Dict[str, List[Path]] = {k: [] for k in keys}

    # 策略1: 保留首尾帧（时间轴覆盖）
    if len(frames) >= 2:
        first_frame = frames[0]
        last_frame = frames[-1]
        middle_frames = frames[1:-1]
        print(f"  [INFO] 时间轴覆盖: 保留首帧 [{first_frame.name}] 和尾帧 [{last_frame.name}]")
    else:
        first_frame = frames[0] if frames else None
        last_frame = None
        middle_frames = []

    # 策略2: 随机打乱中间帧（增加多样性）
    random.shuffle(middle_frames)
    print(f"  [INFO] 随机打乱: {len(middle_frames)} 个中间帧")

    # 策略3: 重新组合帧序列
    if first_frame and last_frame:
        shuffled = [first_frame] + middle_frames + [last_frame]
    elif first_frame:
        shuffled = [first_frame] + middle_frames
    else:
        shuffled = middle_frames

    # 策略4: 计算每个任务的目标帧数
    total_frames = len(shuffled)

    # 小样本回退：总帧数不足以满足最小批次需求时按轮询平均分配
    if total_frames and total_frames < min_batch * num_tasks:
        print(f"  [INFO] 小样本回退：总帧数 {total_frames} < 需求 {min_batch * num_tasks}，采用轮询分配")
        idx = 0
        for frame in shuffled:
            key = keys[idx % num_tasks]
            batches[key].append(frame)
            idx += 1
        return batches

    target_per_task = total_frames // num_tasks  # 平均分配

    # 确保在范围内
    target_per_task = max(min_batch, min(max_batch, target_per_task))
    print(f"  [INFO] 每任务目标: {target_per_task} 帧")

    # 策略5: 分配帧到各任务
    for idx, key in enumerate(keys):
        start_idx = idx * target_per_task
        end_idx = min(start_idx + target_per_task, total_frames)

        batch = shuffled[start_idx:end_idx]

        # 确保至少有 min_batch 帧
        if len(batch) < min_batch and len(shuffled) >= min_batch:
            print(f"  [WARNING] 任务 {key} 只有 {len(batch)} 帧，补充到 {min_batch} 帧")
            batch = _evenly_sample(shuffled, min_batch)

        batches[key] = batch
        print(f"  [INFO]   ✓ {key}: {len(batch)} 帧")

    # 策略6: 计算并显示利用率
    total_used = sum(len(b) for b in batches.values())
    utilization = (total_used / total_frames) * 100 if total_frames else 0

    print(f"\n  [INFO] ========== 利用率统计 ==========")
    print(f"  [INFO] 总帧数: {total_frames}")
    print(f"  [INFO] 已使用: {total_used}")
    print(f"  [INFO] 利用率: {utilization:.1f}%")

    if utilization < 70:
        print(f"  [WARNING] 利用率低于目标 70%，考虑增加 max_batch 参数")
    else:
        print(f"  [SUCCESS] 利用率达标！")

    print(f"  [INFO] ===================================\n")

    return batches
