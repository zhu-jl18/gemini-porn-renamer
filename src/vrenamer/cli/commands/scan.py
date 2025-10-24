"""scan 命令 - 扫描目录中的视频文件."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger
from vrenamer.services.scanner import ScannerService

console = Console()


def command(
    directory: Path = typer.Argument(..., exists=True, file_okay=False, help="扫描目录"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="是否递归扫描"),
):
    """扫描目录中的视频文件."""
    # 加载配置
    config = AppConfig()
    logger = AppLogger.setup(config.log_dir, level=config.log_level)

    # 创建扫描服务
    scanner = ScannerService(logger)

    console.print(f"[cyan]扫描目录：{directory}[/]")
    console.print(f"递归扫描：{'是' if recursive else '否'}\n")

    # 扫描文件
    files = list(scanner.scan_directory(directory, recursive=recursive))

    if not files:
        console.print("[yellow]未找到视频文件[/]")
        return

    # 生成摘要
    summary = scanner.get_scan_summary(files)

    # 显示摘要
    console.print(f"[green]找到 {summary['total']} 个视频文件[/]")
    console.print(f"乱码文件：{summary['garbled']} 个")
    console.print(f"总大小：{summary['total_size_mb']:.2f} MB\n")

    # 显示文件列表（前 20 个）
    table = Table(title="视频文件列表（前 20 个）")
    table.add_column("序号", justify="right", style="cyan")
    table.add_column("文件名", style="white")
    table.add_column("大小 (MB)", justify="right", style="yellow")
    table.add_column("状态", style="magenta")

    for idx, file in enumerate(files[:20], start=1):
        size_mb = file.stat().st_size / (1024 * 1024)
        status = "🔴 乱码" if scanner.is_garbled_filename(file) else "✓"
        table.add_row(str(idx), file.name, f"{size_mb:.2f}", status)

    console.print(table)

    if len(files) > 20:
        console.print(f"\n[dim]... 还有 {len(files) - 20} 个文件未显示[/]")
