"""CLI 主应用 - 使用 typer 构建命令行界面."""

from __future__ import annotations

import typer
from rich.console import Console

# 创建主应用
app = typer.Typer(
    name="vrenamer",
    help="基于 Gemini 的视频智能重命名工具",
    add_completion=False,
)

console = Console()

# 导入并注册子命令
from vrenamer.cli.commands import run, scan

app.command("run")(run.command)
app.command("scan")(scan.command)


def main():
    """主入口函数."""
    app()


if __name__ == "__main__":
    main()
