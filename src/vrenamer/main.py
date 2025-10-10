#!/usr/bin/env python
"""VideoRenamer 主入口.

使用方法：
    # 交互式扫描目录（默认）
    python -m vrenamer.main "X:\\Videos"
    
    # 指定子命令
    python -m vrenamer.main scan "X:\\Videos"      # 交互式扫描
    python -m vrenamer.main single "video.mp4"     # 单视频处理
    python -m vrenamer.main rollback "audit.json"  # 回滚改名
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# 导入各个功能模块
from vrenamer.cli.interactive import InteractiveCLI
from vrenamer.cli.main import run_cli, rollback
from vrenamer.webui.settings import Settings

app = typer.Typer(
    name="vrenamer",
    help="🎬 视频智能重命名工具",
    add_completion=False,
    no_args_is_help=False,  # 允许无参数运行
)
console = Console()


@app.command("scan", help="交互式扫描目录（默认模式）")
def scan_command(
    directory: Path = typer.Argument(
        Path.cwd(),
        help="要扫描的目录路径",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    )
):
    """交互式扫描目录并处理视频."""
    try:
        settings = Settings()
        cli = InteractiveCLI(directory, settings)
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)


@app.command("single", help="处理单个视频文件")
def single_command(
    video: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="视频文件路径"),
    n: int = typer.Option(5, "--n", min=1, max=10, help="候选数量"),
    dry_run: bool = typer.Option(False, "--dry-run", help="模拟运行，不调用真实 LLM"),
    rename: bool = typer.Option(False, "--rename", help="选择后立即改名"),
    custom_prompt: str = typer.Option("", "--custom-prompt", help="自定义提示词"),
    use_styles: bool = typer.Option(True, "--use-styles/--no-styles", help="使用命名风格系统"),
    styles: str = typer.Option("", "--styles", help="指定风格（逗号分隔）"),
):
    """处理单个视频文件."""
    run_cli(
        video=video,
        n=n,
        dry_run=dry_run,
        rename=rename,
        custom_prompt=custom_prompt,
        use_styles=use_styles,
        styles=styles,
    )


@app.command("rollback", help="回滚之前的改名操作")
def rollback_command(
    audit_file: Path = typer.Argument(
        "logs/rename_audit.jsonl",
        help="审计日志文件路径",
        exists=True,
        dir_okay=False,
        readable=True,
    )
):
    """回滚之前的改名操作."""
    rollback(audit_file)


def main():
    """主入口函数."""
    # 特殊处理：如果第一个参数是目录路径，直接进入扫描模式
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        
        # 检查是否是选项或子命令
        if not first_arg.startswith("-") and first_arg not in ["scan", "single", "rollback"]:
            # 尝试作为目录处理
            try:
                directory = Path(first_arg).resolve()
                if directory.exists() and directory.is_dir():
                    # 重写参数，插入 scan 子命令
                    sys.argv.insert(1, "scan")
            except:
                pass
    
    # 使用 typer 处理命令
    app()


if __name__ == "__main__":
    main()
