from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from vrenamer.webui.settings import Settings
from vrenamer.webui.services import pipeline
from vrenamer.webui.services.prompting import compose_name_prompt, compose_task_prompts


app = typer.Typer(add_completion=False, help="单视频命名 CLI，带可视化进度")
console = Console()


def _short_hash(p: Path) -> str:
    h = hashlib.sha256(str(p).encode("utf-8")).hexdigest()
    return h[:8]


@app.command("run", hidden=True)  # 隐藏，但保留兼容性
def run_cli(
    video: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="视频文件路径"),
    n: int = typer.Option(5, "--n", min=1, max=10, help="候选数量"),
    dry_run: bool = typer.Option(False, help="是否跳过真实 LLM 调用（默认关闭）"),
    rename: bool = typer.Option(False, help="选择后立即改名"),
    custom_prompt: str = typer.Option("", help="可选的自定义提示词"),
    use_styles: bool = typer.Option(False, "--use-styles", help="使用命名风格系统"),
    styles: str = typer.Option("", "--styles", help="指定风格（逗号分隔），为空则用配置默认值"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="测试模式：自动选择序号 1，无需交互"),
):
    """分析单个视频 -> 生成候选名 -> 用户选择 -> 可选改名。"""
    settings = Settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        t1 = progress.add_task("抽帧", total=None)
        frame_result = asyncio.run(pipeline.sample_frames(video))
        progress.update(t1, completed=1)
        progress.stop_task(t1)

        t2 = progress.add_task("转录(可选)", total=None)
        transcript = asyncio.run(pipeline.extract_transcript(settings, video))
        progress.update(t2, completed=1)
        progress.stop_task(t2)

        t3 = progress.add_task("合成任务提示词", total=None)
        task_prompts = compose_task_prompts(
            frame_result.directory,
            transcript,
            custom_prompt,
            frames=frame_result.frames,
        )
        progress.update(t3, completed=1)
        progress.stop_task(t3)

        t4 = progress.add_task("LLM解析标签", total=None)
        if dry_run:
            tags = asyncio.run(pipeline.analyze_tasks_stub())
        else:
            tags, _ = asyncio.run(pipeline.analyze_tasks(frame_result, task_prompts, settings))
        progress.update(t4, completed=1)
        progress.stop_task(t4)

        t5 = progress.add_task("生成候选名", total=None)
        if dry_run:
            candidates = [f"占位-{i+1}-{_short_hash(video)}" for i in range(n)]
            candidates_detail = None
        elif use_styles:
            # 使用命名风格系统
            style_ids = [s.strip() for s in styles.split(",") if s.strip()] if styles else None
            candidates_detail = asyncio.run(pipeline.generate_names_with_styles(tags, settings, style_ids))
            candidates = [c["filename"] for c in candidates_detail]
        else:
            # 使用旧的提示词方式
            name_prompt = compose_name_prompt(tags, custom_prompt, n)
            candidates = asyncio.run(pipeline.generate_names(name_prompt, settings, n))
            candidates_detail = None
        progress.update(t5, completed=1)
        progress.stop_task(t5)

    # 展示结果并交互选择
    table = Table(title="候选文件名")
    table.add_column("序号", justify="right")
    if use_styles and candidates_detail:
        table.add_column("风格")
        table.add_column("建议名")
        table.add_column("语言")
        for idx, (c, detail) in enumerate(zip(candidates, candidates_detail), start=1):
            table.add_row(str(idx), detail["style_name"], c, detail["language"])
    else:
        table.add_column("建议名")
        for idx, c in enumerate(candidates, start=1):
            table.add_row(str(idx), c)
    console.print(table)

    if non_interactive:
        ci = 1 if len(candidates) > 0 else 0
    else:
        choice = typer.prompt("选择一个序号(1-{}), 或 0 跳过".format(len(candidates)), default="1")
        try:
            ci = int(choice)
        except Exception:
            ci = 0
    if ci < 1 or ci > len(candidates):
        console.print("已跳过改名。")
        return

    new_name = candidates[ci - 1]
    target = video.with_name(new_name + video.suffix)
    console.print(f"拟改名: {video.name} -> {target.name}")

    if not rename:
        console.print("dry-run：未执行改名。使用 --rename 执行。")
        _write_audit(video, target, tags, transcript, dry_run=True)
        return

    if target.exists():
        target = video.with_name(f"{new_name}-{_short_hash(video)}{video.suffix}")
        console.print(f"存在同名，已去重: {target.name}")
    os.rename(video, target)
    _write_audit(video, target, tags, transcript, dry_run=False)
    console.print("改名完成。")


@app.command("rollback")
def rollback(audit: Path = typer.Argument(..., exists=True)):
    console.print("读取审计文件并尝试回滚…")
    lines = audit.read_text(encoding="utf-8").splitlines()
    done = 0
    for line in lines:
        try:
            obj = json.loads(line)
            src = Path(obj["src"]).resolve()
            dst = Path(obj["dst"]).resolve()
            if dst.exists() and not src.exists():
                os.rename(dst, src)
                done += 1
        except Exception:
            pass
    console.print(f"回滚完成：{done} 条。")


def _write_audit(src: Path, dst: Path, tags: dict, transcript: str, dry_run: bool):
    log_dir = Path("logs"); log_dir.mkdir(exist_ok=True)
    rec = {
        "src": str(src),
        "dst": str(dst),
        "tags": tags,
        "has_transcript": bool(transcript),
        "dry_run": dry_run,
    }
    with open(log_dir / "rename_audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    app()


if __name__ == "__main__":
    main()
