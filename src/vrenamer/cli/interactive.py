"""交互式 CLI 主程序."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from vrenamer.scanner import VideoScanner
from vrenamer.webui.settings import Settings
from vrenamer.webui.services import pipeline
from vrenamer.naming import NamingGenerator, NamingStyleConfig
from vrenamer.llm.client import GeminiClient


console = Console()


class InteractiveCLI:
    """交互式命名助手."""

    def __init__(self, scan_dir: Path, settings: Settings):
        """初始化.

        Args:
            scan_dir: 扫描目录
            settings: 配置
        """
        self.scan_dir = scan_dir
        self.settings = settings
        self.scanner = VideoScanner(scan_dir)
        self.processed_count = 0
        self.skipped_count = 0

    def run(self):
        """运行交互式流程."""
        console.print(
            Panel.fit(
                f"[bold cyan]🎬 视频智能重命名助手[/]\n\n扫描目录：{self.scan_dir}",
                border_style="cyan",
            )
        )

        console.print("\n[yellow]开始扫描视频文件...[/]")
        video_files = list(self.scanner.scan(recursive=True))

        if not video_files:
            console.print("[red]未找到视频文件[/]")
            return

        console.print(f"[green]找到 {len(video_files)} 个视频文件[/]\n")

        for idx, video_path in enumerate(video_files, start=1):
            console.print(f"\n{'='*60}")
            console.print(f"[bold]进度：{idx}/{len(video_files)}[/]")

            # 显示当前文件信息
            self._display_video_info(video_path)

            # 显示操作菜单
            action = self._show_menu()

            if action == "skip":
                console.print("[yellow]⏭️  跳过[/]")
                self.skipped_count += 1
            elif action == "manual":
                self._manual_rename(video_path)
            elif action == "ai":
                asyncio.run(self._ai_rename(video_path))
            elif action == "quit":
                console.print("\n[cyan]👋 退出程序[/]")
                break

        # 显示统计
        self._display_summary()

    def _display_video_info(self, video_path: Path):
        """显示视频文件信息."""
        table = Table(show_header=False, box=None)
        table.add_column("项目", style="cyan")
        table.add_column("值", style="white")

        table.add_row("📁 路径", str(video_path.parent))
        table.add_row("📄 当前文件名", video_path.name)

        # 文件大小
        size_mb = video_path.stat().st_size / (1024 * 1024)
        table.add_row("📦 大小", f"{size_mb:.1f} MB")

        # 检测乱码
        if self.scanner.is_garbled(video_path):
            table.add_row("⚠️  状态", "[red]检测到乱码文件名[/]")

        console.print(table)

    def _show_menu(self) -> str:
        """显示操作菜单并获取用户选择."""
        console.print("\n[bold cyan]请选择操作：[/]")
        console.print("  1. 跳过           (输入 1 或 s)")
        console.print("  2. 手动输入新名称 (输入 2 或 r)")
        console.print("  3. AI 生成名称    (输入 3 或 a)")
        console.print("  q. 退出           (输入 q)")

        while True:
            choice = Prompt.ask("\n选择", default="1").lower()

            if choice in ["1", "s", "skip"]:
                return "skip"
            elif choice in ["2", "r", "rename", "manual"]:
                return "manual"
            elif choice in ["3", "a", "ai"]:
                return "ai"
            elif choice in ["q", "quit", "exit"]:
                return "quit"
            else:
                console.print("[red]无效选择，请重新输入[/]")

    def _manual_rename(self, video_path: Path):
        """手动重命名."""
        new_name = Prompt.ask("\n请输入新文件名（不含扩展名）")
        if not new_name.strip():
            console.print("[red]文件名不能为空，已取消[/]")
            return

        # 清理文件名
        new_name = self._sanitize_filename(new_name.strip())
        new_path = video_path.with_name(new_name + video_path.suffix)

        # 确认
        console.print(f"\n[yellow]预览：[/]{video_path.name} -> {new_path.name}")
        confirm = Prompt.ask("确认重命名？", choices=["y", "n"], default="y")

        if confirm == "y":
            try:
                os.rename(video_path, new_path)
                console.print("[green]✅ 重命名成功[/]")
                self.processed_count += 1
            except Exception as e:
                console.print(f"[red]❌ 重命名失败：{e}[/]")
        else:
            console.print("[yellow]已取消[/]")

    async def _ai_rename(self, video_path: Path):
        """AI 重命名."""
        console.print("\n[cyan]🤖 启动 AI 分析...[/]")

        try:
            # 抽帧
            console.print("\n[bold yellow]━━━ 步骤 1/4: 视频抽帧 ━━━[/]")
            frame_result = await pipeline.sample_frames(video_path)
            console.print(f"  ✓ 抽取帧数: [green]{len(frame_result.frames)}[/] 帧")
            console.print(f"  ✓ 保存位置: [dim]{frame_result.directory}[/]")

            # 显示部分帧文件名
            if frame_result.frames:
                sample_frames = frame_result.frames[:3]
                console.print(f"  ✓ 示例帧: [dim]{', '.join(f.name for f in sample_frames)}...[/]")

            # 转录（如果需要）
            console.print("\n[bold yellow]━━━ 步骤 2/4: 音频转录 (跳过) ━━━[/]")
            transcript = pipeline.extract_transcript(self.settings, video_path)
            if transcript:
                console.print(f"  ✓ 转录长度: {len(transcript)} 字符")
            else:
                console.print("  ⊘ 未启用音频转录")

            # AI 分析标签
            console.print("\n[bold yellow]━━━ 步骤 3/4: AI 多模态分析 ━━━[/]")
            console.print(f"  → 使用模型: [cyan]{self.settings.model_flash}[/]")
            console.print(f"  → 并发数: [cyan]{self.settings.max_concurrency}[/]")

            # 生成任务提示词
            from vrenamer.webui.services.prompting import compose_task_prompts
            task_prompts = compose_task_prompts(
                frame_result.directory,
                transcript,
                "",  # user_prompt
                frames=frame_result.frames,
            )
            console.print(f"  → 分析任务数: [cyan]{len(task_prompts)}[/]")

            # 显示任务列表
            for idx, task_key in enumerate(task_prompts.keys(), 1):
                console.print(f"    {idx}. {task_key}")

            # 定义进度回调
            def progress_callback(task_key: str, status: str, result: dict):
                if status == "start":
                    console.print(f"    ▶ [cyan]{task_key}[/]: 开始处理 ({result['frames']} 帧)...")
                elif status == "done":
                    labels = result['parsed'].get('labels', ['未知'])
                    console.print(f"    ✓ [green]{task_key}[/]: {', '.join(labels)} [{result['progress']}]")
                    console.print(f"      [dim]原始响应: {result['raw_response']}[/]")
                elif status == "error":
                    console.print(f"    ✗ [red]{task_key}[/]: 错误 - {result['error']} [{result['progress']}]")

            # 调用真实 API
            console.print("\n  [cyan]正在调用 Gemini Flash API（并发处理）...[/]")
            tags, batches = await pipeline.analyze_tasks(frame_result, task_prompts, self.settings, progress_callback)

            # 显示最终汇总
            console.print("\n  [green]✓ 所有任务完成，最终结果：[/]")
            for task_key, labels in tags.items():
                console.print(f"    • {task_key}: [yellow]{', '.join(labels)}[/]")

            # 生成候选名称
            console.print("\n[bold yellow]━━━ 步骤 4/4: 生成命名候选 ━━━[/]")
            console.print(f"  → 使用模型: [cyan]{self.settings.model_pro}[/]")
            console.print(f"  → 命名风格: [cyan]{', '.join(self.settings.get_style_ids())}[/]")

            console.print("\n  [cyan]正在生成候选名称...[/]")
            console.print(f"  → 输入标签: [dim]{tags}[/]")
            candidates = await self._generate_candidates(tags)
            console.print(f"  [green]✓ 生成 {len(candidates)} 个候选名称[/]")

            # 显示每个风格的生成详情
            console.print("\n  [cyan]各风格生成详情：[/]")
            for c in candidates:
                console.print(f"    • [{c['style_name']}] {c['filename']}")

            if not candidates:
                console.print("[red]未能生成候选名称[/]")
                return

            # 显示候选
            self._display_candidates(candidates)

            # 用户选择
            choice = Prompt.ask(
                "\n选择一个候选或输入 0 取消",
                default="1",
            )

            try:
                idx = int(choice)
                if idx == 0:
                    console.print("[yellow]已取消[/]")
                    return
                elif 1 <= idx <= len(candidates):
                    selected = candidates[idx - 1]
                    self._apply_rename(video_path, selected["filename"])
                else:
                    console.print("[red]无效选择[/]")
            except ValueError:
                console.print("[red]无效输入[/]")

        except Exception as e:
            import traceback
            console.print(f"[red]❌ AI 处理失败：{e}[/]")
            console.print(f"[dim]错误类型: {type(e).__name__}[/]")
            console.print("[dim]详细堆栈:[/]")
            console.print(f"[dim]{traceback.format_exc()}[/]")

    async def _generate_candidates(self, tags: dict) -> list:
        """生成命名候选."""
        # 加载风格配置
        config_path = self.settings.get_style_config_path()
        style_config = NamingStyleConfig.from_yaml(config_path)

        # 创建生成器
        client = GeminiClient(
            base_url=self.settings.gemini_base_url,
            api_key=self.settings.gemini_api_key,
            transport=self.settings.llm_transport,
            timeout=self.settings.request_timeout,
        )

        generator = NamingGenerator(
            llm_client=client,
            style_config=style_config,
            model=self.settings.model_pro,
        )

        # 生成
        style_ids = self.settings.get_style_ids()
        candidates_obj = await generator.generate_candidates(
            analysis=tags,
            style_ids=style_ids,
            n_per_style=1,
        )

        return [
            {
                "style_id": c.style_id,
                "style_name": c.style_name,
                "filename": c.filename,
                "language": c.language,
            }
            for c in candidates_obj
        ]

    def _display_candidates(self, candidates: list):
        """显示候选名称."""
        table = Table(title="🎯 AI 生成的候选名称", show_header=True)
        table.add_column("序号", justify="center", style="cyan")
        table.add_column("风格", style="yellow")
        table.add_column("文件名", style="green")
        table.add_column("语言", justify="center", style="magenta")

        for idx, c in enumerate(candidates, start=1):
            table.add_row(str(idx), c["style_name"], c["filename"], c["language"])

        console.print(table)

    def _apply_rename(self, video_path: Path, new_name: str):
        """应用重命名."""
        new_path = video_path.with_name(new_name + video_path.suffix)

        # 避免冲突
        if new_path.exists():
            console.print("[yellow]⚠️  目标文件已存在，添加序号[/]")
            counter = 1
            while new_path.exists():
                new_path = video_path.with_name(f"{new_name}_{counter}{video_path.suffix}")
                counter += 1

        try:
            os.rename(video_path, new_path)
            console.print(f"[green]✅ 重命名成功：{new_path.name}[/]")
            self.processed_count += 1
        except Exception as e:
            console.print(f"[red]❌ 重命名失败：{e}[/]")

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名."""
        # 替换非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            name = name.replace(char, "_")
        return name.strip()

    def _display_summary(self):
        """显示统计摘要."""
        console.print(f"\n{'='*60}")
        console.print(Panel.fit(
            f"[bold green]✅ 完成[/]\n\n"
            f"处理：{self.processed_count} 个\n"
            f"跳过：{self.skipped_count} 个",
            border_style="green",
        ))


app = typer.Typer(help="交互式视频重命名助手")


@app.command()
def start(
    scan_dir: Path = typer.Argument(
        Path.cwd(),
        help="扫描目录（默认当前目录）",
        exists=True,
        file_okay=False,
        dir_okay=True,
    )
):
    """启动交互式命名助手."""
    settings = Settings()
    cli = InteractiveCLI(scan_dir, settings)
    cli.run()


def main():
    app()


if __name__ == "__main__":
    main()
