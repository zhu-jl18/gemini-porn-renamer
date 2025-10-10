"""命名候选生成器."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from vrenamer.llm.client import GeminiClient
from vrenamer.naming.styles import NamingStyleConfig, StyleDefinition


class VideoAnalysis(BaseModel):
    """视频分析结果（简化版）."""

    category: str
    scene: str
    actors: Optional[List[str]] = None
    mood: Optional[str] = None
    description: Optional[str] = None


class NameCandidate(BaseModel):
    """单个命名候选."""

    style_id: str
    style_name: str
    filename: str
    language: str
    score: Optional[float] = None


class NamingGenerator:
    """命名候选生成器."""

    def __init__(
        self,
        llm_client: GeminiClient,
        style_config: NamingStyleConfig,
        model: str,
    ):
        """初始化生成器.

        Args:
            llm_client: LLM 客户端
            style_config: 风格配置
            model: 使用的模型名称（从 Settings.model_pro 传入）
        """
        self.llm = llm_client
        self.config = style_config
        self.model = model

    async def generate_candidates(
        self,
        analysis: Dict[str, Any],
        style_ids: Optional[List[str]] = None,
        n_per_style: Optional[int] = None,
    ) -> List[NameCandidate]:
        """生成命名候选.

        Args:
            analysis: 视频分析结果字典
            style_ids: 要使用的风格 ID 列表（None 则用默认）
            n_per_style: 每个风格生成的候选数（None 则用配置默认值）

        Returns:
            命名候选列表
        """
        # 使用默认风格或验证提供的风格
        if style_ids is None:
            style_ids = self.config.default.selected_styles
        else:
            style_ids = self.config.validate_styles(style_ids)

        if not style_ids:
            raise ValueError("No valid styles provided")

        # 使用配置的候选数
        if n_per_style is None:
            n_per_style = self.config.default.candidates_per_style

        # 为每个风格生成候选
        all_candidates: List[NameCandidate] = []
        for style_id in style_ids:
            style_def = self.config.get_style(style_id)
            if not style_def:
                continue

            candidates = await self._generate_for_style(
                analysis=analysis, style_id=style_id, style_def=style_def, n_candidates=n_per_style
            )
            all_candidates.extend(candidates)

        # 限制总候选数
        max_total = self.config.default.total_candidates
        if len(all_candidates) > max_total:
            all_candidates = all_candidates[:max_total]

        return all_candidates

    async def _generate_for_style(
        self,
        analysis: Dict[str, Any],
        style_id: str,
        style_def: StyleDefinition,
        n_candidates: int,
    ) -> List[NameCandidate]:
        """为单个风格生成候选.

        Args:
            analysis: 视频分析结果
            style_id: 风格 ID
            style_def: 风格定义
            n_candidates: 候选数量

        Returns:
            该风格的候选列表
        """
        # 构建提示词
        system_prompt = self._build_system_prompt(style_def, n_candidates)
        user_prompt = self._build_user_prompt(analysis, style_def)

        # 打印调用信息（可选：通过日志系统）
        print(f"  → 调用 {self.model} 生成 [{style_def.name}] 风格...")
        print(f"    提示词长度: {len(system_prompt) + len(user_prompt)} 字符")

        # 调用 LLM
        response = await self.llm.name_candidates(
            model=self.model,
            system_prompt=system_prompt,
            user_text=user_prompt,
            temperature=0.7,
            json_array=True,
        )

        print(f"    响应长度: {len(response)} 字符")
        print(f"    原始响应: {response[:150]}..." if len(response) > 150 else f"    原始响应: {response}")

        # 解析响应
        names = self._parse_response(response, n_candidates)
        print(f"    ✓ 解析出 {len(names)} 个候选")

        # 构建候选对象
        candidates = []
        for name in names:
            sanitized = self.config.sanitize_filename(name)
            if sanitized:
                candidates.append(
                    NameCandidate(
                        style_id=style_id,
                        style_name=style_def.name,
                        filename=sanitized,
                        language=style_def.language,
                    )
                )

        return candidates

    def _build_system_prompt(self, style_def: StyleDefinition, n: int) -> str:
        """构建系统提示词.

        Args:
            style_def: 风格定义
            n: 需要生成的候选数

        Returns:
            系统提示词
        """
        return f"""你是一个专业的视频命名助手。

**任务**：根据视频分析结果和指定的命名风格，生成 {n} 个文件名候选。

**风格要求**：
{style_def.prompt_template}

**示例**：
{chr(10).join(f"- {ex}" for ex in style_def.examples)}

**输出格式**：
仅输出一个 JSON 对象，格式如下：
{{
  "names": ["候选1", "候选2", ...]
}}

**重要约束**：
1. 只输出 JSON，不要其他文字
2. 严格遵循指定风格
3. 不要包含文件扩展名
4. 避免使用非法字符：< > : " / \\ | ? *
"""

    def _build_user_prompt(self, analysis: Dict[str, Any], style_def: StyleDefinition) -> str:
        """构建用户提示词.

        Args:
            analysis: 视频分析结果
            style_def: 风格定义

        Returns:
            用户提示词
        """
        # 提取关键信息
        category = analysis.get("category", "未知")
        scene = analysis.get("scene", "")
        actors = analysis.get("actors", [])
        mood = analysis.get("mood", "")
        description = analysis.get("description", "")

        # 演员信息
        actor_info = ""
        if actors:
            actor_info = f"\n演员：{', '.join(actors)}"
        elif not self.config.default.include_actor:
            actor_info = "\n演员：未识别（可省略）"

        return f"""**视频信息**：
类别：{category}
场景：{scene}
氛围：{mood}
描述：{description}{actor_info}

请根据以上信息和 {style_def.name} 风格，生成命名候选。
"""

    def _parse_response(self, response: str, n: int) -> List[str]:
        """解析 LLM 响应，提取命名列表.

        Args:
            response: LLM 原始响应
            n: 期望的候选数

        Returns:
            命名字符串列表
        """
        # 尝试直接解析 JSON
        try:
            data = json.loads(response.strip())
            if isinstance(data, dict) and "names" in data:
                names = data["names"]
                if isinstance(names, list):
                    return [str(name).strip() for name in names[:n] if name]
        except json.JSONDecodeError:
            pass

        # 回退：从文本中提取 JSON 块
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and "names" in data:
                    names = data["names"]
                    if isinstance(names, list):
                        return [str(name).strip() for name in names[:n] if name]
            except json.JSONDecodeError:
                pass

        # 回退：逐行解析（支持简单列表格式）
        lines = response.strip().split("\n")
        names = []
        for line in lines:
            line = line.strip()
            # 匹配列表项：- name 或 1. name
            match = re.match(r"^[-*\d]+[.)]?\s*(.+)$", line)
            if match:
                names.append(match.group(1).strip())
        if names:
            return names[:n]

        # 最后回退：直接返回非空行
        return [line.strip() for line in lines if line.strip()][:n]
