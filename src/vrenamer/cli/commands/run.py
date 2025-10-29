"""run 命令 - 处理单个视频文件."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.services.video import VideoProcessor
from vrenamer.services.analysis import AnalysisService
from vrenamer.services.naming import NamingService

console = Console()


def command(
    video: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="视频文件路径"
    ),
    n: int = typer.Option(5, "--candidates", "-n", min=1, max=10, help="候选数量"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览模式，不实际改名"),
    styles: Optional[str] = typer.Option(None, "--styles", help="命名风格（逗号分隔）"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="测试模式：自动选择序号 1，无需交互"),
):
    """处理单个视频文件 - 分析并生成命名候选."""
    asyncio.run(_run_async(video, n, dry_run, styles, non_interactive))


async def _run_async(
    video: Path, n: int, dry_run: bool, styles: Optional[str], non_interactive: bool
):
    """异步执行单视频处理."""
    # 加载配置
    config = AppConfig()
    logger = AppLogger.setup(config.log_dir, level=config.log_level)

    logger.info(f"开始处理视频: {video}")

    # 创建服务
    llm_client = LLMClientFactory.create(config, logger)
    video_processor = VideoProcessor(logger)
    analysis_service = AnalysisService(llm_client, config, logger)
    naming_service = NamingService(llm_client, config, logger)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # 1. 抽帧
        task1 = progress.add_task("抽帧中...", total=None)
        frame_result = await video_processor.sample_frames(video)
        progress.update(task1, completed=1)
        console.print(f"✓ 抽取了 {len(frame_result.frames)} 帧")

        # 2. 分析
        task2 = progress.add_task("AI 分析中...", total=None)

        def progress_callback(task_id, status, data):
            if status == "batch_done":
                console.print(
                    f"  [{task_id}] 批次 {data['batch_idx']+1}/{data['total_batches']} 完成"
                )

        tags = await analysis_service.analyze_video(
            frames=frame_result.frames, progress_callback=progress_callback
        )
        progress.update(task2, completed=1)
        console.print(f"✓ 分析完成")

        # 显示分析结果
        console.print("\n[bold cyan]分析结果：[/]")
        for task_id, labels in tags.items():
            console.print(f"  {task_id}: {', '.join(labels)}")

        # 3. 生成候选名称
        task3 = progress.add_task("生成候选名称...", total=None)

        # 解析风格
        style_ids = None
        if styles:
            style_ids = [s.strip() for s in styles.split(",") if s.strip()]

        candidates = await naming_service.generate_candidates(
            analysis=tags, style_ids=style_ids
        )
        progress.update(task3, completed=1)
        console.print(f"✓ 生成了 {len(candidates)} 个候选")

    # 显示候选名称
    table = Table(title="\n候选文件名")
    table.add_column("序号", justify="right", style="cyan")
    table.add_column("风格", style="yellow")
    table.add_column("文件名", style="green")
    table.add_column("语言", justify="center", style="magenta")

    for idx, c in enumerate(candidates, start=1):
        table.add_row(
            str(idx), c["style_name"], c["filename"], c["language"]
        )

    console.print(table)

    # 用户选择
    if non_interactive:
        ci = 1 if len(candidates) > 0 else 0
    else:
        choice = typer.prompt(
            f"\n选择一个序号 (1-{len(candidates)})，或 0 跳过", default="0"
        )
        try:
            ci = int(choice)
        except ValueError:
            ci = 0

    if ci < 1 or ci > len(candidates):
        console.print("[yellow]已跳过改名[/]")
        return

    selected = candidates[ci - 1]
    new_name = selected["filename"]
    target = video.with_name(new_name + video.suffix)

    console.print(f"\n[bold]拟改名：[/]{video.name} -> {target.name}")

    if dry_run:
        console.print("[yellow]dry-run 模式：未执行改名[/]")
        return

    # 执行改名
    if target.exists():
        console.print("[yellow]目标文件已存在，添加序号[/]")
        counter = 1
        while target.exists():
            target = video.with_name(f"{new_name}_{counter}{video.suffix}")
            counter += 1

    try:
        video.rename(target)
        console.print(f"[green]✅ 重命名成功：{target.name}[/]")
        logger.info(f"重命名成功: {video} -> {target}")
    except Exception as e:
        console.print(f"[red]❌ 重命名失败：{e}[/]")
        logger.error(f"重命名失败: {e}")
