# 设计文档

## 概述

本设计文档描述 VideoRenamer 项目的重构方案。重构目标是解决当前代码臃肿混乱、缺少自动化测试、使用不便的问题，同时保持 Python 环境隔离，建立清晰的模块结构，完善测试覆盖，并提供更友好的用户体验。

**核心定位**：VideoRenamer 是一个**单视频分析工具**，专注于对单个视频文件进行深度 AI 分析和智能命名。批量处理功能是对单视频处理的简单循环调用，不是核心关注点。

**设计原则**：
1. **模块独立性**：每个模块可独立调试，提供独立的调试脚本和文档
2. **配置驱动**：避免硬编码，所有参数（包括 System Prompt）通过配置文件管理
3. **可扩展性**：支持多种 LLM 后端（Gemini、OpenAI），易于扩展新后端
4. **并发优化**：两层并发策略充分利用 GPT-Load 的 key 轮询能力

重构采用渐进式策略，保持核心功能不变，逐步优化架构和代码质量。

## 架构设计

### 分层架构

采用经典的三层架构，清晰分离关注点：

```
┌─────────────────────────────────────────┐
│         接口层 (Interface Layer)         │
│  - CLI (typer + rich)                   │
│  - WebUI (FastAPI, 未来扩展)            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         服务层 (Service Layer)           │
│  - VideoProcessor (视频处理)            │
│  - AnalysisService (AI 分析)            │
│  - NamingService (命名生成)             │
│  - ScannerService (文件扫描)            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         核心层 (Core Layer)              │
│  - LLMClient (API 调用)                 │
│  - ConfigManager (配置管理)             │
│  - Logger (日志)                        │
│  - Exceptions (异常定义)                │
└─────────────────────────────────────────┘
```

### 目录结构

```
src/vrenamer/
├── __init__.py
├── __main__.py              # 入口点：python -m vrenamer
│
├── core/                    # 核心层
│   ├── __init__.py
│   ├── config.py           # 配置管理（pydantic-settings）
│   ├── logging.py          # 日志配置
│   ├── exceptions.py       # 自定义异常
│   └── types.py            # 共享类型定义
│
├── llm/                     # LLM 客户端（支持多后端）
│   ├── __init__.py
│   ├── base.py             # 抽象基类
│   ├── gemini.py           # Gemini 客户端
│   ├── openai.py           # OpenAI 客户端
│   ├── factory.py          # 客户端工厂
│   ├── json_utils.py       # JSON 解析工具
│   └── prompts.py          # 提示词加载器（从配置文件）
│
├── services/                # 服务层
│   ├── __init__.py
│   ├── video.py            # VideoProcessor（视频处理）
│   ├── analysis.py         # AnalysisService（AI 分析，两层并发）
│   ├── naming.py           # NamingService（命名生成）
│   └── scanner.py          # ScannerService（文件扫描）
│
├── naming/                  # 命名风格系统
│   ├── __init__.py
│   ├── styles.py           # 风格配置加载
│   └── generator.py        # 命名生成器
│
├── cli/                     # CLI 接口
│   ├── __init__.py
│   ├── app.py              # Typer 应用主入口
│   ├── commands/           # 子命令
│   │   ├── __init__.py
│   │   ├── run.py          # 单视频处理（核心命令）
│   │   ├── scan.py         # 目录扫描
│   │   ├── batch.py        # 批量处理（循环调用 run）
│   │   └── rollback.py     # 回滚操作
│   └── ui.py               # Rich UI 组件
│
└── utils/                   # 工具函数
    ├── __init__.py
    ├── file.py             # 文件操作工具
    └── text.py             # 文本处理工具

tests/                       # 测试目录
├── __init__.py
├── conftest.py             # pytest 配置和 fixtures
├── unit/                   # 单元测试
│   ├── test_config.py
│   ├── test_llm_client.py
│   ├── test_naming.py
│   ├── test_video.py
│   └── test_analysis.py
├── integration/            # 集成测试
│   ├── test_video_pipeline.py
│   └── test_cli.py
└── fixtures/               # 测试数据
    ├── sample_video.mp4
    └── mock_responses.json

config/                      # 配置文件
├── naming_styles.yaml      # 命名风格配置
├── analysis_tasks.yaml     # 分析任务配置（子任务定义）
├── prompts/                # 提示词配置
│   ├── analysis/           # 分析任务提示词
│   │   ├── role_archetype.yaml
│   │   ├── face_visibility.yaml
│   │   ├── scene_type.yaml
│   │   └── positions.yaml
│   └── naming/             # 命名生成提示词
│       └── system.yaml
└── llm_backends.yaml       # LLM 后端配置

scripts/                     # 脚本
├── setup.ps1               # Windows 安装脚本
├── setup.sh                # Linux/macOS 安装脚本
└── debug/                  # 调试脚本
    ├── debug_video.py      # 调试视频处理模块
    ├── debug_analysis.py   # 调试分析模块
    ├── debug_naming.py     # 调试命名模块
    ├── debug_llm.py        # 调试 LLM 客户端
    └── README.md           # 调试脚本使用文档

docs/                        # 文档
├── modules/                # 模块文档
│   ├── video.md           # 视频处理模块
│   ├── analysis.md        # 分析模块（含并发策略详解）
│   ├── naming.md          # 命名模块
│   └── llm.md             # LLM 客户端
└── debugging.md            # 调试指南
```

## 组件和接口

### LLM 客户端抽象

#### 基础接口

所有 LLM 客户端实现统一的抽象接口：

```python
# llm/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""
    
    @abstractmethod
    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512
    ) -> str:
        """分类任务（多模态）
        
        Args:
            prompt: 提示词
            images: 图片路径列表
            response_format: 响应格式（json/text）
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 响应文本
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """生成任务（纯文本）
        
        Args:
            prompt: 提示词
            response_format: 响应格式（json/text）
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            LLM 响应文本
        """
        pass
```

#### Gemini 客户端实现

```python
# llm/gemini.py
import aiohttp
import base64
from pathlib import Path
from typing import List

class GeminiClient(BaseLLMClient):
    """Gemini 客户端（支持两种传输格式）"""
    
    def __init__(self, config: LLMBackendConfig):
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.transport = config.transport  # openai_compat | gemini_native
        self.timeout = config.timeout
    
    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512
    ) -> str:
        if self.transport == "openai_compat":
            return await self._classify_openai_format(
                prompt, images, response_format, temperature, max_tokens
            )
        else:
            return await self._classify_gemini_format(
                prompt, images, response_format, temperature, max_tokens
            )
    
    async def _classify_openai_format(self, prompt, images, response_format, temperature, max_tokens):
        """OpenAI 兼容格式"""
        url = f"{self.base_url}/v1beta/openai/chat/completions"
        
        # 构建消息
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
            })
        
        body = {
            "model": "gemini-flash-latest",
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format == "json":
            body["response_format"] = {"type": "json_object"}
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    async def _classify_gemini_format(self, prompt, images, response_format, temperature, max_tokens):
        """Gemini 原生格式"""
        url = f"{self.base_url}/v1beta/models/gemini-flash-latest:generateContent"
        
        # 构建 parts
        parts = [{"text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_data
                }
            })
        
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generation_config": {
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        }
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                parts = data["candidates"][0]["content"]["parts"]
                return "\n".join(p.get("text", "") for p in parts)
    
    async def generate(self, prompt, response_format="json", temperature=0.7, max_tokens=2048):
        """生成任务（纯文本）"""
        if self.transport == "openai_compat":
            url = f"{self.base_url}/v1beta/openai/chat/completions"
            body = {
                "model": "gemini-2.5-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if response_format == "json":
                body["response_format"] = {"type": "json_object"}
        else:
            url = f"{self.base_url}/v1beta/models/gemini-2.5-pro:generateContent"
            body = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generation_config": {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                if self.transport == "openai_compat":
                    return data["choices"][0]["message"]["content"]
                else:
                    parts = data["candidates"][0]["content"]["parts"]
                    return "\n".join(p.get("text", "") for p in parts)
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
```

#### OpenAI 客户端实现

```python
# llm/openai.py
import aiohttp
import base64
from pathlib import Path
from typing import List

class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""
    
    def __init__(self, config: LLMBackendConfig):
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.organization = config.organization
        self.timeout = config.timeout
    
    async def classify(
        self,
        prompt: str,
        images: List[Path],
        response_format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 512
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        
        # 构建消息
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            img_data = base64.b64encode(img_path.read_bytes()).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
            })
        
        body = {
            "model": "gpt-4-vision-preview",
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format == "json":
            body["response_format"] = {"type": "json_object"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    async def generate(self, prompt, response_format="json", temperature=0.7, max_tokens=2048):
        url = f"{self.base_url}/chat/completions"
        
        body = {
            "model": "gpt-4-turbo-preview",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format == "json":
            body["response_format"] = {"type": "json_object"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    def _headers(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers
```

#### 客户端工厂

```python
# llm/factory.py
from vrenamer.core.config import AppConfig
from vrenamer.llm.base import BaseLLMClient
from vrenamer.llm.gemini import GeminiClient
from vrenamer.llm.openai import OpenAIClient

class LLMClientFactory:
    """LLM 客户端工厂"""
    
    @staticmethod
    def create(config: AppConfig) -> BaseLLMClient:
        """根据配置创建 LLM 客户端
        
        Args:
            config: 应用配置
            
        Returns:
            LLM 客户端实例
            
        Raises:
            ValueError: 不支持的后端类型
        """
        backend_config = config.get_llm_backend()
        
        if backend_config.type == "gemini":
            return GeminiClient(backend_config)
        elif backend_config.type == "openai":
            return OpenAIClient(backend_config)
        else:
            raise ValueError(
                f"Unsupported LLM backend: {backend_config.type}. "
                f"Supported: gemini, openai"
            )
```

### 核心层组件

#### ConfigManager

统一的配置管理，使用 pydantic-settings，支持多 LLM 后端：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Dict, Any, Literal

class LLMBackendConfig(BaseSettings):
    """LLM 后端配置"""
    type: Literal["gemini", "openai"] = "gemini"
    base_url: str
    api_key: str
    timeout: int = 30
    retry: int = 3
    # Gemini 特有配置
    transport: str = "openai_compat"  # gemini_native | openai_compat
    # OpenAI 特有配置
    organization: str = ""

class ModelConfig(BaseSettings):
    """模型配置"""
    flash: str = "gemini-flash-latest"  # 用于分析任务
    pro: str = "gemini-2.5-pro"         # 用于命名生成

class ConcurrencyConfig(BaseSettings):
    """并发配置（两层并发）"""
    # 第一层：子任务并发数
    task_concurrency: int = 4  # 同时执行的子任务数
    # 第二层：每个子任务内的批次并发数
    batch_concurrency: int = 16  # 每个子任务内同时执行的批次数

class AnalysisConfig(BaseSettings):
    """分析配置"""
    tasks_config_path: Path = Path("config/analysis_tasks.yaml")
    prompts_dir: Path = Path("config/prompts/analysis")
    batch_size: int = 5  # 每批次的帧数（Gemini 限制）

class NamingConfig(BaseSettings):
    """命名配置"""
    styles: List[str] = ["chinese_descriptive", "scene_role"]
    style_config_path: Path = Path("config/naming_styles.yaml")
    prompts_dir: Path = Path("config/prompts/naming")
    candidates_per_style: int = 1
    total_candidates: int = 5

class AppConfig(BaseSettings):
    """应用配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__"
    )
    
    # LLM 后端配置
    llm_backend: str = "gemini"  # 默认使用 Gemini
    llm_backends: Dict[str, LLMBackendConfig] = {}
    
    # 模型配置
    model: ModelConfig = ModelConfig()
    
    # 并发配置
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    
    # 分析配置
    analysis: AnalysisConfig = AnalysisConfig()
    
    # 命名配置
    naming: NamingConfig = NamingConfig()
    
    # 日志配置
    log_dir: Path = Path("logs")
    log_level: str = "INFO"
    
    def get_llm_backend(self) -> LLMBackendConfig:
        """获取当前 LLM 后端配置"""
        if self.llm_backend not in self.llm_backends:
            raise ConfigError(f"LLM backend '{self.llm_backend}' not configured")
        return self.llm_backends[self.llm_backend]
```

#### Logger

结构化日志，支持文件和控制台输出：

```python
import logging
from pathlib import Path
from typing import Optional

class AppLogger:
    """应用日志管理器"""
    
    @staticmethod
    def setup(
        log_dir: Path,
        level: str = "INFO",
        console: bool = True,
        file: bool = True
    ) -> logging.Logger:
        """配置日志系统"""
        logger = logging.getLogger("vrenamer")
        logger.setLevel(getattr(logging, level.upper()))
        
        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 文件处理器
        if file:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / "vrenamer.log",
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
```

#### Exceptions

自定义异常层次结构：

```python
class VRenamerError(Exception):
    """基础异常类"""
    pass

class ConfigError(VRenamerError):
    """配置错误"""
    pass

class APIError(VRenamerError):
    """API 调用错误"""
    pass

class VideoProcessingError(VRenamerError):
    """视频处理错误"""
    pass

class FileOperationError(VRenamerError):
    """文件操作错误"""
    pass
```

### 服务层组件

#### VideoProcessor

视频处理服务，封装 ffmpeg 操作：

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List
import subprocess

@dataclass
class FrameSampleResult:
    """抽帧结果"""
    directory: Path
    frames: List[Path]
    duration: float
    fps: float

class VideoProcessor:
    """视频处理服务"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查 ffmpeg 和 ffprobe 是否可用"""
        # 实现略
    
    async def sample_frames(
        self,
        video_path: Path,
        target_frames: int = 96,
        output_dir: Optional[Path] = None
    ) -> FrameSampleResult:
        """抽取视频帧"""
        # 实现略
    
    def get_duration(self, video_path: Path) -> float:
        """获取视频时长"""
        # 实现略
    
    def extract_audio(
        self,
        video_path: Path,
        output_path: Path
    ) -> Path:
        """提取音频"""
        # 实现略
```

#### AnalysisService

AI 分析服务，实现两层并发策略：

**两层并发策略说明**：

1. **第一层并发**：多个子任务并发执行
   - 子任务包括：角色原型、脸部可见性、场景类型、姿势标签等
   - 每个子任务独立并发执行，互不阻塞

2. **第二层并发**：每个子任务内部的帧批次并发
   - 假设有 80 帧，随机分成 16 组（每组 5 帧）
   - 这 16 组并发调用 LLM API
   - 汇总 16 个结果，得到该子任务的最终输出

3. **结果汇聚**：
   - 汇聚所有子任务的结果
   - 结合音频转录（如有）
   - 传递给 Gemini 2.5 Pro 生成最终文件名

```python
from typing import Dict, Any, List, Callable, Optional
from collections import Counter
import asyncio
import random

class AnalysisService:
    """AI 分析服务（两层并发）"""
    
    def __init__(
        self,
        llm_client: BaseLLMClient,
        config: AppConfig,
        logger: logging.Logger
    ):
        self.llm = llm_client
        self.config = config
        self.logger = logger
        # 第一层并发：控制子任务并发数
        self.task_semaphore = asyncio.Semaphore(
            config.concurrency.task_concurrency
        )
        # 第二层并发：控制每个子任务内的批次并发数
        self.batch_semaphore = asyncio.Semaphore(
            config.concurrency.batch_concurrency
        )
    
    async def analyze_video(
        self,
        frames: List[Path],
        transcript: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """分析视频内容（两层并发）
        
        Args:
            frames: 视频帧列表
            transcript: 音频转录（可选）
            progress_callback: 进度回调
            
        Returns:
            分析结果字典，包含所有子任务的标签
        """
        # 加载子任务配置
        tasks_config = self._load_tasks_config()
        
        # 第一层并发：并发执行所有子任务
        task_results = await self._execute_tasks_concurrent(
            frames=frames,
            tasks_config=tasks_config,
            progress_callback=progress_callback
        )
        
        # 汇总结果
        final_result = self._aggregate_task_results(task_results)
        
        # 添加音频转录（如有）
        if transcript:
            final_result["transcript"] = transcript
        
        return final_result
    
    async def _execute_tasks_concurrent(
        self,
        frames: List[Path],
        tasks_config: Dict[str, Any],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """第一层并发：并发执行所有子任务"""
        async def _execute_one_task(task_id: str, task_cfg: Dict[str, Any]):
            async with self.task_semaphore:
                return await self._execute_single_task(
                    task_id=task_id,
                    task_cfg=task_cfg,
                    frames=frames,
                    progress_callback=progress_callback
                )
        
        # 创建所有子任务
        tasks = [
            _execute_one_task(task_id, task_cfg)
            for task_id, task_cfg in tasks_config.items()
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组装结果
        return {
            task_id: result
            for task_id, result in zip(tasks_config.keys(), results)
            if not isinstance(result, Exception)
        }
    
    async def _execute_single_task(
        self,
        task_id: str,
        task_cfg: Dict[str, Any],
        frames: List[Path],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """执行单个子任务（第二层并发）
        
        Args:
            task_id: 任务 ID（如 "role_archetype"）
            task_cfg: 任务配置（包含 prompt 等）
            frames: 所有可用帧
            progress_callback: 进度回调
            
        Returns:
            该任务的分析结果
        """
        # 随机打乱帧顺序
        shuffled_frames = frames.copy()
        random.shuffle(shuffled_frames)
        
        # 分批：每批 5 帧（Gemini 限制）
        batch_size = task_cfg.get("batch_size", 5)
        batches = [
            shuffled_frames[i:i+batch_size]
            for i in range(0, len(shuffled_frames), batch_size)
        ]
        
        self.logger.info(
            f"Task {task_id}: {len(frames)} frames → {len(batches)} batches"
        )
        
        # 第二层并发：并发执行所有批次
        batch_results = await self._execute_batches_concurrent(
            task_id=task_id,
            task_cfg=task_cfg,
            batches=batches,
            progress_callback=progress_callback
        )
        
        # 汇总批次结果
        final_labels = self._aggregate_batch_results(batch_results)
        
        return {
            "labels": final_labels,
            "num_batches": len(batches),
            "num_frames": len(frames)
        }
    
    async def _execute_batches_concurrent(
        self,
        task_id: str,
        task_cfg: Dict[str, Any],
        batches: List[List[Path]],
        progress_callback: Optional[Callable]
    ) -> List[Dict[str, Any]]:
        """第二层并发：并发执行一个子任务的所有批次"""
        async def _execute_one_batch(batch_idx: int, batch_frames: List[Path]):
            async with self.batch_semaphore:
                try:
                    # 加载提示词
                    prompt = self._load_prompt(task_id, task_cfg)
                    
                    # 调用 LLM
                    response = await self.llm.classify(
                        prompt=prompt,
                        images=batch_frames,
                        response_format="json"
                    )
                    
                    # 解析结果
                    parsed = self._parse_response(response)
                    
                    if progress_callback:
                        progress_callback(
                            task_id,
                            "batch_done",
                            {
                                "batch_idx": batch_idx,
                                "total_batches": len(batches),
                                "labels": parsed.get("labels", [])
                            }
                        )
                    
                    return parsed
                    
                except Exception as e:
                    self.logger.error(
                        f"Batch {batch_idx} of task {task_id} failed: {e}"
                    )
                    return {"labels": [], "error": str(e)}
        
        # 并发执行所有批次
        results = await asyncio.gather(
            *[_execute_one_batch(i, batch) for i, batch in enumerate(batches)],
            return_exceptions=False
        )
        
        return results
    
    def _aggregate_batch_results(
        self,
        batch_results: List[Dict[str, Any]]
    ) -> List[str]:
        """汇总批次结果：统计标签频率，取前 3 个最常见的"""
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
    
    def _aggregate_task_results(
        self,
        task_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """汇总所有子任务的结果"""
        return {
            task_id: result.get("labels", ["未知"])
            for task_id, result in task_results.items()
        }
    
    def _load_tasks_config(self) -> Dict[str, Any]:
        """从配置文件加载子任务定义"""
        # 从 config/analysis_tasks.yaml 加载
        # 实现略
        pass
    
    def _load_prompt(self, task_id: str, task_cfg: Dict[str, Any]) -> str:
        """从配置文件加载提示词"""
        # 从 config/prompts/analysis/{task_id}.yaml 加载
        # 实现略
        pass
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        # 使用 json_utils.parse_json_loose
        # 实现略
        pass
```

#### NamingService

命名生成服务：

```python
from vrenamer.naming import NamingGenerator, NamingStyleConfig

class NamingService:
    """命名生成服务"""
    
    def __init__(
        self,
        llm_client: GeminiClient,
        config: AppConfig,
        logger: logging.Logger
    ):
        self.llm = llm_client
        self.config = config
        self.logger = logger
        
        # 加载风格配置
        self.style_config = NamingStyleConfig.from_yaml(
            config.naming.style_config_path
        )
        
        # 创建生成器
        self.generator = NamingGenerator(
            llm_client=llm_client,
            style_config=self.style_config,
            model=config.model.pro
        )
    
    async def generate_candidates(
        self,
        analysis: Dict[str, Any],
        style_ids: Optional[List[str]] = None,
        n_per_style: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """生成命名候选"""
        candidates = await self.generator.generate_candidates(
            analysis=analysis,
            style_ids=style_ids or self.config.naming.styles,
            n_per_style=n_per_style or self.config.naming.candidates_per_style
        )
        
        return [
            {
                "style_id": c.style_id,
                "style_name": c.style_name,
                "filename": c.filename,
                "language": c.language
            }
            for c in candidates
        ]
```

#### ScannerService

文件扫描服务：

```python
from typing import Iterator, List, Optional
from pathlib import Path

class ScannerService:
    """文件扫描服务"""
    
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv"}
    
    def __init__(
        self,
        logger: logging.Logger,
        min_size_mb: float = 10.0
    ):
        self.logger = logger
        self.min_size_bytes = int(min_size_mb * 1024 * 1024)
    
    def scan_directory(
        self,
        root_dir: Path,
        recursive: bool = True,
        skip_processed: bool = True
    ) -> Iterator[Path]:
        """扫描目录中的视频文件"""
        # 实现略
    
    def is_video_file(self, path: Path) -> bool:
        """判断是否为视频文件"""
        return path.suffix.lower() in self.VIDEO_EXTENSIONS
    
    def is_garbled_filename(self, path: Path) -> bool:
        """判断文件名是否乱码"""
        # 实现略
    
    def get_scan_summary(
        self,
        files: List[Path]
    ) -> Dict[str, Any]:
        """生成扫描摘要"""
        return {
            "total": len(files),
            "garbled": sum(1 for f in files if self.is_garbled_filename(f)),
            "total_size_mb": sum(f.stat().st_size for f in files) / (1024 * 1024)
        }
```

### CLI 接口

#### 主应用

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="vrenamer",
    help="基于 Gemini 的视频智能重命名工具",
    add_completion=False
)

console = Console()

# 注册子命令
from vrenamer.cli.commands import run, scan, batch, rollback

app.command("run")(run.command)
app.command("scan")(scan.command)
app.command("batch")(batch.command)
app.command("rollback")(rollback.command)

def main():
    app()
```

#### 子命令示例

```python
# cli/commands/run.py
import typer
from pathlib import Path
from rich.console import Console

console = Console()

def command(
    video: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        help="视频文件路径"
    ),
    n: int = typer.Option(
        5,
        "--candidates", "-n",
        min=1, max=10,
        help="候选数量"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="预览模式，不实际改名"
    ),
    styles: Optional[str] = typer.Option(
        None,
        "--styles",
        help="命名风格（逗号分隔）"
    )
):
    """处理单个视频文件"""
    # 实现略
```

## 数据模型

### 核心数据类型

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class VideoInfo:
    """视频信息"""
    path: Path
    duration: float
    size_bytes: int
    format: str

@dataclass
class AnalysisResult:
    """分析结果"""
    tags: Dict[str, List[str]]
    confidence: Dict[str, float]
    metadata: Dict[str, Any]
    timestamp: datetime

@dataclass
class NameCandidate:
    """命名候选"""
    filename: str
    style_id: str
    style_name: str
    language: str
    score: Optional[float] = None

@dataclass
class RenameOperation:
    """重命名操作记录"""
    source: Path
    target: Path
    analysis: AnalysisResult
    selected_candidate: NameCandidate
    timestamp: datetime
    dry_run: bool
```

## 错误处理

### 错误处理策略

1. **分层错误处理**：
   - 核心层：抛出具体异常
   - 服务层：捕获并转换异常，添加上下文
   - 接口层：捕获所有异常，提供友好提示

2. **重试机制**：
   - API 调用失败：指数退避重试（最多 3 次）
   - 网络超时：增加超时时间后重试
   - 速率限制：等待后重试

3. **降级策略**：
   - 多模态分析失败：降级到文本分析
   - 风格生成失败：使用默认风格
   - 部分任务失败：继续处理其他任务

### 错误日志

```python
class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_api_error(self, error: Exception, context: Dict[str, Any]):
        """处理 API 错误"""
        self.logger.error(
            "API call failed",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            }
        )
    
    def handle_video_error(self, error: Exception, video_path: Path):
        """处理视频处理错误"""
        self.logger.error(
            f"Video processing failed: {video_path}",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "video_path": str(video_path)
            }
        )
```

## 测试策略

### 测试层次

1. **单元测试**：
   - 测试单个函数和类
   - 使用 mock 隔离外部依赖
   - 覆盖率目标：80%+

2. **集成测试**：
   - 测试模块间协作
   - 使用真实配置和测试数据
   - 覆盖关键工作流

3. **端到端测试**（可选）：
   - 测试完整用户场景
   - 使用示例视频
   - 验证 CLI 输出

### 测试工具

- **pytest**：测试框架
- **pytest-asyncio**：异步测试支持
- **pytest-mock**：mock 工具
- **pytest-cov**：覆盖率报告
- **responses**：HTTP mock（用于 API 测试）

### Mock 策略

```python
# conftest.py
import pytest
from pathlib import Path
from vrenamer.core.config import AppConfig
from vrenamer.llm.client import GeminiClient

@pytest.fixture
def mock_config():
    """Mock 配置"""
    return AppConfig(
        api=APIConfig(api_key="test-key"),
        model=ModelConfig(),
        concurrency=ConcurrencyConfig(max_workers=2),
        naming=NamingConfig()
    )

@pytest.fixture
def mock_llm_client(mock_config):
    """Mock LLM 客户端"""
    client = GeminiClient(
        base_url=mock_config.api.base_url,
        api_key=mock_config.api.api_key
    )
    return client

@pytest.fixture
def sample_video(tmp_path):
    """创建示例视频文件"""
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake video data")
    return video_path
```

### 测试示例

```python
# tests/unit/test_naming.py
import pytest
from vrenamer.services.naming import NamingService

@pytest.mark.asyncio
async def test_generate_candidates(mock_llm_client, mock_config):
    """测试命名候选生成"""
    service = NamingService(
        llm_client=mock_llm_client,
        config=mock_config,
        logger=logging.getLogger("test")
    )
    
    analysis = {
        "category": "测试",
        "scene": "办公室",
        "actors": ["演员A"]
    }
    
    # Mock LLM 响应
    with patch.object(mock_llm_client, "name_candidates") as mock_call:
        mock_call.return_value = '{"names": ["候选1", "候选2"]}'
        
        candidates = await service.generate_candidates(analysis)
        
        assert len(candidates) > 0
        assert all("filename" in c for c in candidates)
```

## 配置管理

### 配置文件结构

**.env**：
```env
# API 配置
API__BASE_URL=http://localhost:3001/proxy/free
API__API_KEY=your-api-key-here
API__TRANSPORT=openai_compat
API__TIMEOUT=30
API__RETRY=3

# 模型配置
MODEL__FLASH=gemini-flash-latest
MODEL__PRO=gemini-2.5-pro

# 并发配置
CONCURRENCY__MAX_WORKERS=32
CONCURRENCY__SEMAPHORE_LIMIT=64

# 命名配置
NAMING__STYLES=chinese_descriptive,scene_role,pornhub_style
NAMING__STYLE_CONFIG_PATH=config/naming_styles.yaml
NAMING__CANDIDATES_PER_STYLE=1
NAMING__TOTAL_CANDIDATES=5

# 日志配置
LOG_DIR=logs
LOG_LEVEL=INFO
```

### 配置验证

```python
from pydantic import field_validator

class APIConfig(BaseSettings):
    api_key: str
    
    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or v == "your-api-key-here":
            raise ValueError(
                "API key not configured. "
                "Please set API__API_KEY in .env file"
            )
        return v
```

## 依赖管理

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "vrenamer"
version = "0.2.0"
description = "AI-powered video renaming tool with Gemini"
requires-python = ">=3.10"
readme = "README.md"
license = {text = "MIT"}

dependencies = [
    "httpx>=0.25.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "typer>=0.9.0",
    "rich>=13.7.0",
    "pyyaml>=6.0",
    "chardet>=5.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=4.1.0",
    "black>=23.12.0",
    "isort>=5.13.0",
    "mypy>=1.7.0",
    "ruff>=0.1.8",
]

image = [
    "pillow>=10.1.0",
    "imagehash>=4.3.1",
]

audio = [
    "faster-whisper>=0.10.0",
]

[project.scripts]
vrenamer = "vrenamer.__main__:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py310"]

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

## 开发工具链

### 代码格式化

```bash
# 格式化代码
black src/ tests/

# 排序导入
isort src/ tests/

# 一键格式化
black src/ tests/ && isort src/ tests/
```

### 代码检查

```bash
# 类型检查
mypy src/

# 代码检查
ruff check src/ tests/

# 修复可自动修复的问题
ruff check --fix src/ tests/
```

### 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 生成覆盖率报告
pytest --cov=vrenamer --cov-report=html

# 运行特定测试
pytest tests/unit/test_naming.py::test_generate_candidates
```

## 安装和部署

### 安装脚本

**setup.ps1** (Windows):
```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 升级 pip
python -m pip install --upgrade pip

# 安装项目（可编辑模式）
pip install -e ".[dev,image]"

# 复制配置模板
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "已创建 .env 文件，请编辑配置"
}

Write-Host "安装完成！运行 'vrenamer --help' 查看帮助"
```

### 快速开始

```bash
# 1. 克隆项目
git clone <repo-url>
cd vrenamer

# 2. 运行安装脚本
./scripts/setup.ps1  # Windows
# 或
./scripts/setup.sh   # Linux/macOS

# 3. 编辑配置
notepad .env  # Windows
# 或
nano .env     # Linux/macOS

# 4. 运行示例
vrenamer run path/to/video.mp4
```

## 项目清理和文档规范化

### 清理策略

重构过程中需要清理项目中的冗余文件和文档：

#### 需要删除的文件

1. **测试垃圾文件**：
   - `test_fixes.py`（临时测试脚本）
   - `.pytest_cache/`（pytest 缓存）
   - `__pycache__/`（Python 缓存，所有目录）
   - `*.pyc`（编译的 Python 文件）

2. **冗余文档**：
   - `docs/bugfix-plan-20250124.md`（临时 bugfix 计划）
   - `docs/progress-tracker.md`（进度追踪，应整合到主文档）
   - `docs/concurrent-strategy-explained.md`（并发策略说明，应整合到设计文档）
   - `意见/`（AI 生成的意见文档，评估后决定保留或删除）

3. **AI 生成的垃圾脚本**：
   - 评估 `prompts/modules/` 下的文件，删除无用的
   - 评估 `.serena/` 和 `.crush/` 目录（AI 工具缓存）

#### 需要保留和规范化的文档

1. **核心文档**（保留并规范化）：
   - `README.md`：项目概述和快速开始
   - `核心需求.md`：核心需求文档（可能需要英文化为 `REQUIREMENTS.md`）
   - `docs/setup.md`：安装指南
   - `docs/cli.md`：CLI 使用文档
   - `AGENTS.md`：AI 协作规范（如果仍然相关）

2. **技术文档**（整合和规范化）：
   - `docs/decisions.md`：技术决策记录（保留）
   - `docs/testing-guide.md`：测试指南（保留并更新）
   - `docs/gptload-api.md`：GPT-Load API 说明（保留）
   - `docs/naming-styles.md`：命名风格说明（新建）

3. **新增文档**（重构后创建）：
   - `docs/architecture.md`：架构设计文档
   - `docs/modules/`：各模块详细文档
   - `docs/debugging.md`：调试指南
   - `CONTRIBUTING.md`：贡献指南

#### 文档结构规范

重构后的文档结构：

```
docs/
├── README.md                    # 文档索引
├── setup.md                     # 安装指南
├── quickstart.md                # 快速开始
├── cli.md                       # CLI 使用文档
├── architecture.md              # 架构设计
├── testing-guide.md             # 测试指南
├── debugging.md                 # 调试指南
├── api/                         # API 文档
│   ├── gptload.md              # GPT-Load API
│   └── llm-backends.md         # LLM 后端配置
├── modules/                     # 模块文档
│   ├── video.md                # 视频处理模块
│   ├── analysis.md             # 分析模块（含并发策略）
│   ├── naming.md               # 命名模块
│   └── llm.md                  # LLM 客户端
└── decisions.md                 # 技术决策记录
```

### 配置文件规范化

#### LLM 后端配置

**config/llm_backends.yaml**：
```yaml
# LLM 后端配置
backends:
  gemini:
    type: gemini
    base_url: http://localhost:3001/proxy/free
    transport: openai_compat  # 或 gemini_native
    timeout: 30
    retry: 3
  
  openai:
    type: openai
    base_url: https://api.openai.com/v1
    timeout: 30
    retry: 3

# 默认后端
default: gemini
```

#### 分析任务配置

**config/analysis_tasks.yaml**：
```yaml
# 分析子任务配置
tasks:
  role_archetype:
    name: 角色原型
    description: 识别视频中的角色类型
    batch_size: 5
    prompt_file: role_archetype.yaml
    enabled: true
  
  face_visibility:
    name: 脸部可见性
    description: 判断脸部是否可见
    batch_size: 5
    prompt_file: face_visibility.yaml
    enabled: true
  
  scene_type:
    name: 场景类型
    description: 识别场景类型
    batch_size: 5
    prompt_file: scene_type.yaml
    enabled: true
  
  positions:
    name: 姿势标签
    description: 识别姿势和动作
    batch_size: 5
    prompt_file: positions.yaml
    enabled: true

# 任务执行顺序（可选，默认并发）
execution_order: concurrent  # concurrent | sequential
```

#### 提示词配置

**config/prompts/analysis/role_archetype.yaml**：
```yaml
# 角色原型识别提示词
system_prompt: |
  你是一个专业的视频内容分析助手。
  你的任务是识别视频中的角色原型。
  
  严格输出 JSON 格式：
  {
    "labels": ["标签1", "标签2", ...],
    "confidence": 0.95
  }

user_prompt_template: |
  请分析以下视频帧，识别其中的角色原型。
  
  可选标签：人妻、学生、护士、教师、OL、其他
  
  要求：
  1. 只输出 JSON，不要其他文字
  2. labels 数组包含 1-3 个最相关的标签
  3. confidence 为 0-1 之间的浮点数

# 响应格式
response_format: json

# 温度参数
temperature: 0.1

# 最大 token 数
max_tokens: 512
```

### 迁移指南

#### 配置迁移

旧版 `.env` 格式：
```env
GEMINI_BASE_URL=http://localhost:3001/proxy/free
GEMINI_API_KEY=your-key
MODEL_FLASH=gemini-flash-latest
MODEL_PRO=gemini-2.5-pro
```

新版 `.env` 格式：
```env
# LLM 后端
LLM_BACKEND=gemini

# Gemini 后端配置
LLM_BACKENDS__GEMINI__TYPE=gemini
LLM_BACKENDS__GEMINI__BASE_URL=http://localhost:3001/proxy/free
LLM_BACKENDS__GEMINI__API_KEY=your-key
LLM_BACKENDS__GEMINI__TRANSPORT=openai_compat

# 模型配置
MODEL__FLASH=gemini-flash-latest
MODEL__PRO=gemini-2.5-pro

# 并发配置（两层并发）
CONCURRENCY__TASK_CONCURRENCY=4
CONCURRENCY__BATCH_CONCURRENCY=16
```

提供迁移脚本 `scripts/migrate_config.py` 自动转换。

#### API 兼容性

重构后的 CLI 命令保持兼容：

```bash
# 旧命令（仍然支持）
vrenamer run video.mp4

# 新命令（推荐）
vrenamer run video.mp4 --styles chinese_descriptive,scene_role
```

#### 数据迁移

- 审计日志：保持 JSONL 格式，无需迁移
- 命名风格配置：保持 YAML 格式，无需迁移
- 缓存数据：清空重建（如有）

## 性能优化

### 并发优化

- 使用 asyncio 实现真正的异步并发
- Semaphore 控制并发数，避免资源耗尽
- 批量处理时复用 HTTP 连接

### 缓存策略

- 视频时长缓存（避免重复 probe）
- 帧去重缓存（MD5 + pHash）
- LLM 响应缓存（可选，用于开发测试）

### 资源管理

- 及时清理临时文件
- 限制内存占用（大文件流式处理）
- 优雅关闭（清理资源）

## 安全考虑

### 敏感信息保护

- API Key 仅从环境变量读取
- 不在日志中记录敏感信息
- .gitignore 排除 .env 文件

### 文件操作安全

- 验证文件路径（防止路径遍历）
- 检查文件权限
- 原子性重命名操作

### 输入验证

- 验证所有用户输入
- 清理文件名（防止注入）
- 限制文件大小和数量

## 模块调试支持

### 调试脚本设计

每个核心模块提供独立的调试脚本，便于开发和测试。

#### 视频处理模块调试

**scripts/debug/debug_video.py**：
```python
"""视频处理模块调试脚本

用法：
    python scripts/debug/debug_video.py path/to/video.mp4
    
功能：
    - 测试视频抽帧
    - 验证 ffmpeg 可用性
    - 检查帧去重逻辑
    - 输出详细日志
"""
import asyncio
from pathlib import Path
from vrenamer.services.video import VideoProcessor
from vrenamer.core.logging import AppLogger

async def main(video_path: Path):
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    processor = VideoProcessor(logger)
    
    print(f"[1/3] 检查视频时长...")
    duration = processor.get_duration(video_path)
    print(f"  ✓ 时长: {duration:.2f} 秒")
    
    print(f"\n[2/3] 抽取视频帧...")
    result = await processor.sample_frames(video_path, target_frames=96)
    print(f"  ✓ 抽取帧数: {len(result.frames)}")
    print(f"  ✓ 保存目录: {result.directory}")
    
    print(f"\n[3/3] 验证帧文件...")
    for i, frame in enumerate(result.frames[:5], 1):
        print(f"  {i}. {frame.name} ({frame.stat().st_size} bytes)")
    
    print(f"\n✅ 视频处理模块测试完成")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python debug_video.py <video_path>")
        sys.exit(1)
    asyncio.run(main(Path(sys.argv[1])))
```

#### 分析模块调试

**scripts/debug/debug_analysis.py**：
```python
"""分析模块调试脚本

用法：
    python scripts/debug/debug_analysis.py path/to/frames_dir
    
功能：
    - 测试两层并发策略
    - 验证子任务配置加载
    - 测试提示词加载
    - 模拟 LLM 调用（可选 mock）
    - 输出详细并发日志
"""
import asyncio
from pathlib import Path
from vrenamer.services.analysis import AnalysisService
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger

async def main(frames_dir: Path, use_mock: bool = False):
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()
    
    # 创建 LLM 客户端
    if use_mock:
        print("使用 Mock LLM 客户端")
        llm_client = MockLLMClient()
    else:
        llm_client = LLMClientFactory.create(config)
    
    # 创建分析服务
    service = AnalysisService(llm_client, config, logger)
    
    # 加载帧
    frames = sorted(frames_dir.glob("*.jpg"))
    print(f"加载 {len(frames)} 个帧文件")
    
    # 进度回调
    def progress_callback(task_id, status, data):
        if status == "batch_done":
            print(f"  [{task_id}] 批次 {data['batch_idx']+1}/{data['total_batches']} 完成")
    
    # 执行分析
    print("\n开始分析（两层并发）...")
    result = await service.analyze_video(
        frames=frames,
        progress_callback=progress_callback
    )
    
    # 输出结果
    print("\n分析结果：")
    for task_id, labels in result.items():
        print(f"  {task_id}: {labels}")
    
    print(f"\n✅ 分析模块测试完成")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python debug_analysis.py <frames_dir> [--mock]")
        sys.exit(1)
    
    frames_dir = Path(sys.argv[1])
    use_mock = "--mock" in sys.argv
    asyncio.run(main(frames_dir, use_mock))
```

#### 命名模块调试

**scripts/debug/debug_naming.py**：
```python
"""命名模块调试脚本

用法：
    python scripts/debug/debug_naming.py --tags '{"role": ["人妻"], "scene": ["办公室"]}'
    
功能：
    - 测试命名风格加载
    - 测试提示词构建
    - 测试候选生成
    - 验证文件名清理
"""
import asyncio
import json
from vrenamer.services.naming import NamingService
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger

async def main(tags: dict, styles: list = None):
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()
    
    llm_client = LLMClientFactory.create(config)
    service = NamingService(llm_client, config, logger)
    
    print(f"输入标签: {tags}")
    print(f"使用风格: {styles or config.naming.styles}")
    
    print("\n生成候选名称...")
    candidates = await service.generate_candidates(
        analysis=tags,
        style_ids=styles
    )
    
    print(f"\n生成 {len(candidates)} 个候选：")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. [{c['style_name']}] {c['filename']}")
    
    print(f"\n✅ 命名模块测试完成")

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", required=True, help="分析标签 JSON")
    parser.add_argument("--styles", help="命名风格（逗号分隔）")
    args = parser.parse_args()
    
    tags = json.loads(args.tags)
    styles = args.styles.split(",") if args.styles else None
    
    asyncio.run(main(tags, styles))
```

#### LLM 客户端调试

**scripts/debug/debug_llm.py**：
```python
"""LLM 客户端调试脚本

用法：
    python scripts/debug/debug_llm.py --backend gemini --test classify
    
功能：
    - 测试不同 LLM 后端
    - 验证 API 连接
    - 测试响应解析
    - 对比不同后端的输出
"""
import asyncio
from pathlib import Path
from vrenamer.llm.factory import LLMClientFactory
from vrenamer.core.config import AppConfig
from vrenamer.core.logging import AppLogger

async def test_classify(client, test_images: list):
    print("\n测试分类任务...")
    response = await client.classify(
        prompt="请识别图片中的物体，输出 JSON 格式：{\"labels\": [...]}",
        images=test_images,
        response_format="json"
    )
    print(f"响应: {response}")

async def test_generate(client):
    print("\n测试生成任务...")
    response = await client.generate(
        prompt="生成 3 个创意文件名，输出 JSON 格式：{\"names\": [...]}",
        response_format="json"
    )
    print(f"响应: {response}")

async def main(backend: str, test_type: str):
    logger = AppLogger.setup(Path("logs"), level="DEBUG", console=True)
    config = AppConfig()
    config.llm_backend = backend
    
    print(f"使用后端: {backend}")
    client = LLMClientFactory.create(config)
    
    if test_type == "classify":
        # 需要提供测试图片
        test_images = list(Path("tests/fixtures").glob("*.jpg"))[:3]
        await test_classify(client, test_images)
    elif test_type == "generate":
        await test_generate(client)
    else:
        print(f"未知测试类型: {test_type}")
    
    print(f"\n✅ LLM 客户端测试完成")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="gemini", help="LLM 后端")
    parser.add_argument("--test", default="classify", choices=["classify", "generate"])
    args = parser.parse_args()
    
    asyncio.run(main(args.backend, args.test))
```

### 调试文档

**scripts/debug/README.md**：
```markdown
# 调试脚本使用指南

## 概述

本目录包含各模块的独立调试脚本，用于开发和测试。

## 脚本列表

| 脚本 | 功能 | 用法 |
|------|------|------|
| `debug_video.py` | 视频处理模块 | `python debug_video.py video.mp4` |
| `debug_analysis.py` | 分析模块（两层并发） | `python debug_analysis.py frames_dir [--mock]` |
| `debug_naming.py` | 命名模块 | `python debug_naming.py --tags '{...}'` |
| `debug_llm.py` | LLM 客户端 | `python debug_llm.py --backend gemini` |

## 使用场景

### 1. 开发新功能

在开发新功能时，使用对应的调试脚本快速验证：

```bash
# 开发视频处理功能
python scripts/debug/debug_video.py test.mp4

# 开发分析功能（使用 mock 避免 API 调用）
python scripts/debug/debug_analysis.py frames/ --mock
```

### 2. 调试问题

遇到问题时，使用调试脚本定位：

```bash
# 视频抽帧失败？
python scripts/debug/debug_video.py problem.mp4

# 分析结果不准确？
python scripts/debug/debug_analysis.py frames/ > analysis.log
```

### 3. 测试配置

修改配置后，使用调试脚本验证：

```bash
# 测试新的 LLM 后端
python scripts/debug/debug_llm.py --backend openai --test classify

# 测试新的命名风格
python scripts/debug/debug_naming.py --tags '{"role":["人妻"]}' --styles new_style
```

## 日志输出

所有调试脚本都会输出详细日志到 `logs/` 目录，便于事后分析。

## Mock 模式

部分脚本支持 `--mock` 参数，使用 mock 数据避免真实 API 调用，适合：
- 快速测试逻辑
- 无网络环境
- 节省 API 配额
```

## 扩展性设计

### LLM 后端扩展

通过工厂模式支持多种 LLM 后端：

```python
# llm/factory.py
class LLMClientFactory:
    @staticmethod
    def create(config: AppConfig) -> BaseLLMClient:
        backend_config = config.get_llm_backend()
        
        if backend_config.type == "gemini":
            return GeminiClient(backend_config)
        elif backend_config.type == "openai":
            return OpenAIClient(backend_config)
        else:
            raise ValueError(f"Unsupported backend: {backend_config.type}")
```

添加新后端只需：
1. 实现 `BaseLLMClient` 接口
2. 在 `factory.py` 中注册
3. 在 `config/llm_backends.yaml` 中配置

### 命名风格扩展

用户可以在 `config/naming_styles.yaml` 中添加自定义风格：

```yaml
custom_styles:
  my_style:
    name: 我的风格
    description: 自定义命名风格
    language: zh
    format: "{场景}_{角色}_{日期}"
    examples:
      - "办公室_OL_20250124"
    prompt_template: |
      根据以下信息生成文件名...
```

### 分析任务扩展

用户可以在 `config/analysis_tasks.yaml` 中添加新的分析任务：

```yaml
tasks:
  custom_task:
    name: 自定义任务
    description: 识别特定内容
    batch_size: 5
    prompt_file: custom_task.yaml
    enabled: true
```

### WebUI（未来）

- FastAPI 后端
- Vue.js 前端
- WebSocket 实时进度

### 多语言支持

- i18n 国际化
- 支持中文、英文、日文
- 可扩展语言包
