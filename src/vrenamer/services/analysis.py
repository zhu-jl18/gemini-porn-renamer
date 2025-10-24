"""分析服务 - AI 分析服务，实现两层并发策略."""

from __future__ import annotations

import asyncio
import logging
import random
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from vrenamer.core.config import AppConfig
from vrenamer.core.exceptions import APIError, ConfigError
from vrenamer.core.types import FrameSampleResult
from vrenamer.llm.base import BaseLLMClient
from vrenamer.llm.json_utils import parse_json_loose
from vrenamer.llm.prompts import PromptLoader


class AnalysisService:
    """AI 分析服务（两层并发）.

    两层并发策略：
    1. 第一层：多个子任务并发执行（如角色原型、脸部可见性、场景类型、姿势标签）
    2. 第二层：每个子任务内部的帧批次并发（如 80 帧分成 16 组，每组 5 帧）
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        config: AppConfig,
        logger: logging.Logger,
    ):
        """初始化分析服务.

        Args:
            llm_client: LLM 客户端
            config: 应用配置
            logger: 日志器
        """
        self.llm = llm_client
        self.config = config
        self.logger = logger

        # 第一层并发：控制子任务并发数
        self.task_semaphore = asyncio.Semaphore(config.concurrency.task_concurrency)

        # 第二层并发：控制每个子任务内的批次并发数
        self.batch_semaphore = asyncio.Semaphore(config.concurrency.batch_concurrency)

    async def analyze_video(
        self,
        frames: List[Path],
        transcript: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """分析视频内容（两层并发）.

        Args:
            frames: 视频帧列表
            transcript: 音频转录（可选）
            progress_callback: 进度回调函数

        Returns:
            分析结果字典，包含所有子任务的标签
        """
        self.logger.info(f"开始分析视频，共 {len(frames)} 帧")

        # 加载子任务配置
        tasks_config = self._load_tasks_config()
        self.logger.info(f"加载了 {len(tasks_config)} 个分析任务")

        # 第一层并发：并发执行所有子任务
        task_results = await self._execute_tasks_concurrent(
            frames=frames, tasks_config=tasks_config, progress_callback=progress_callback
        )

        # 汇总结果
        final_result = self._aggregate_task_results(task_results)

        # 添加音频转录（如有）
        if transcript:
            final_result["transcript"] = transcript

        self.logger.info("视频分析完成")
        return final_result

    async def _execute_tasks_concurrent(
        self,
        frames: List[Path],
        tasks_config: Dict[str, Any],
        progress_callback: Optional[Callable],
    ) -> Dict[str, Any]:
        """第一层并发：并发执行所有子任务."""

        async def _execute_one_task(task_id: str, task_cfg: Dict[str, Any]):
            async with self.task_semaphore:
                return await self._execute_single_task(
                    task_id=task_id,
                    task_cfg=task_cfg,
                    frames=frames,
                    progress_callback=progress_callback,
                )

        # 创建所有子任务
        tasks = [
            _execute_one_task(task_id, task_cfg)
            for task_id, task_cfg in tasks_config.items()
            if task_cfg.get("enabled", True)
        ]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 组装结果
        task_ids = [
            task_id
            for task_id, task_cfg in tasks_config.items()
            if task_cfg.get("enabled", True)
        ]

        return {
            task_id: result
            for task_id, result in zip(task_ids, results)
            if not isinstance(result, Exception)
        }

    async def _execute_single_task(
        self,
        task_id: str,
        task_cfg: Dict[str, Any],
        frames: List[Path],
        progress_callback: Optional[Callable],
    ) -> Dict[str, Any]:
        """执行单个子任务（第二层并发）.

        Args:
            task_id: 任务 ID（如 "role_archetype"）
            task_cfg: 任务配置
            frames: 所有可用帧
            progress_callback: 进度回调

        Returns:
            该任务的分析结果
        """
        self.logger.info(f"开始执行任务: {task_id}")

        # 随机打乱帧顺序（每个子任务独立打乱）
        shuffled_frames = frames.copy()
        random.shuffle(shuffled_frames)

        # 分批：每批 batch_size 帧（默认 5 帧，Gemini 限制）
        batch_size = task_cfg.get("batch_size", self.config.analysis.batch_size)
        batches = [
            shuffled_frames[i : i + batch_size]
            for i in range(0, len(shuffled_frames), batch_size)
        ]

        self.logger.info(
            f"任务 {task_id}: {len(frames)} 帧 → {len(batches)} 批次 (每批 {batch_size} 帧)"
        )

        # 第二层并发：并发执行所有批次
        batch_results = await self._execute_batches_concurrent(
            task_id=task_id,
            task_cfg=task_cfg,
            batches=batches,
            progress_callback=progress_callback,
        )

        # 汇总批次结果
        final_labels = self._aggregate_batch_results(batch_results)

        self.logger.info(f"任务 {task_id} 完成: {final_labels}")

        return {
            "labels": final_labels,
            "num_batches": len(batches),
            "num_frames": len(frames),
        }

    async def _execute_batches_concurrent(
        self,
        task_id: str,
        task_cfg: Dict[str, Any],
        batches: List[List[Path]],
        progress_callback: Optional[Callable],
    ) -> List[Dict[str, Any]]:
        """第二层并发：并发执行一个子任务的所有批次."""

        async def _execute_one_batch(batch_idx: int, batch_frames: List[Path]):
            async with self.batch_semaphore:
                try:
                    # 加载提示词
                    prompt = self._load_prompt(task_id, task_cfg)

                    # 调用 LLM
                    response = await self.llm.classify(
                        prompt=prompt, images=batch_frames, response_format="json"
                    )

                    # 解析结果
                    parsed = parse_json_loose(response)
                    if not parsed:
                        self.logger.warning(
                            f"任务 {task_id} 批次 {batch_idx} 解析失败，返回空结果"
                        )
                        return {"labels": [], "confidence": 0.0}

                    # 提取标签
                    if isinstance(parsed, dict):
                        labels = parsed.get("labels", [])
                        confidence = parsed.get("confidence", 0.0)
                    else:
                        labels = []
                        confidence = 0.0

                    if progress_callback:
                        progress_callback(
                            task_id,
                            "batch_done",
                            {
                                "batch_idx": batch_idx,
                                "total_batches": len(batches),
                                "labels": labels,
                            },
                        )

                    return {"labels": labels, "confidence": confidence}

                except Exception as e:
                    self.logger.error(f"批次 {batch_idx} of task {task_id} 失败: {e}")
                    if progress_callback:
                        progress_callback(
                            task_id,
                            "error",
                            {"batch_idx": batch_idx, "error": str(e)},
                        )
                    return {"labels": [], "confidence": 0.0, "error": str(e)}

        # 并发执行所有批次
        results = await asyncio.gather(
            *[_execute_one_batch(i, batch) for i, batch in enumerate(batches)],
            return_exceptions=False,
        )

        return results

    def _aggregate_batch_results(self, batch_results: List[Dict[str, Any]]) -> List[str]:
        """汇总批次结果：统计标签频率，取前 3 个最常见的.

        Args:
            batch_results: 批次结果列表

        Returns:
            最终标签列表
        """
        all_labels = []
        for result in batch_results:
            labels = result.get("labels", [])
            all_labels.extend(labels)

        if not all_labels:
            return ["未知"]

        # 统计频率，取前 3
        label_counts = Counter(all_labels)
        top_labels = [label for label, _ in label_counts.most_common(3)]

        return top_labels

    def _aggregate_task_results(self, task_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """汇总所有子任务的结果.

        Args:
            task_results: 子任务结果字典

        Returns:
            最终结果字典
        """
        return {
            task_id: result.get("labels", ["未知"])
            for task_id, result in task_results.items()
        }

    def _load_tasks_config(self) -> Dict[str, Any]:
        """从配置文件加载子任务定义.

        Returns:
            任务配置字典

        Raises:
            ConfigError: 配置文件不存在或格式错误
        """
        config_path = self.config.analysis.tasks_config_path

        if not config_path.exists():
            raise ConfigError(f"Analysis tasks config not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict) or "tasks" not in config:
                raise ConfigError(f"Invalid tasks config format in {config_path}")

            return config["tasks"]
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML in {config_path}: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load tasks config from {config_path}: {e}")

    def _load_prompt(self, task_id: str, task_cfg: Dict[str, Any]) -> str:
        """从配置文件加载提示词.

        Args:
            task_id: 任务 ID
            task_cfg: 任务配置

        Returns:
            提示词字符串

        Raises:
            ConfigError: 提示词文件不存在或格式错误
        """
        prompt_file = task_cfg.get("prompt_file")
        if not prompt_file:
            raise ConfigError(f"Task {task_id} missing prompt_file in config")

        prompt_path = self.config.analysis.prompts_dir / prompt_file

        # 加载提示词配置
        prompt_config = PromptLoader.load_prompt_config(prompt_path)

        # 构建提示词
        prompt = PromptLoader.build_prompt(prompt_config)

        return prompt
