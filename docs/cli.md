# CLI 使用说明

## 前置准备

**必须在虚拟环境中运行所有命令！**

### 1. 环境配置
```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（每次使用前必须执行）
.\.venv\Scripts\Activate.ps1

# 安装核心依赖（避免编译问题）
pip install httpx python-dotenv pydantic pydantic-settings typer rich

# （可选）完整依赖
pip install -r requirements.txt
pip install -e .

# 配置环境变量
copy .env.example .env
notepad .env  # 填入实际配置
```

详细配置参考 [docs/setup.md](./setup.md)

## 命令速查

### 交互式 CLI（推荐）
```powershell
# 扫描目录并逐个处理视频
.\.venv\Scripts\vrenamer.exe "X:\Videos"

# 或者使用 Python 运行
.\.venv\Scripts\python.exe -m vrenamer.cli.interactive "X:\Videos"
```

功能特点：
- 自动递归扫描所有视频文件
- 检测乱码文件名并提示处理
- 逐个展示视频信息
- 提供交互菜单：跳过、手动输入、AI 生成、退出
- AI 生成时使用配置的命名风格
- 处理完成后显示统计摘要

### 单视频分析（dry-run 默认开启）
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --n 5
```

参数说明：
- `--n`：候选名称数量（1-10，默认 5）
- `--dry-run`：模拟模式，不调用真实 LLM（默认 True）
- `--custom-prompt`：自定义提示词前缀

### 执行改名
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --rename
```

改名前会：
1. 展示候选文件名列表
2. 等待用户选择（输入序号）
3. 确认后执行改名
4. 记录到 `logs/rename_audit.jsonl`

### 回滚改名
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main rollback logs/rename_audit.jsonl
```

读取审计日志，将已改名文件恢复原名。

## 工作流程

```
1. 异步获取时长     → _probe_duration 调用 ffprobe 并缓存可执行路径
2. 自适应抽帧       → ffmpeg 动态 fps，最多 96 帧
3. 去重与采样       → MD5 + pHash 去重，均匀抽取代表帧
4. 任务提示词       → compose_task_prompts 生成分类任务
5. 标签分析         → analyze_tasks 复用帧批次，单批 5 帧并遵守并发上限
6. 命名生成         → NamingGenerator + GeminiLLMAdapter，多风格候选 + JSON 回退
7. 用户交互         → 终端选择风格候选，可保留审计记录
8. 执行改名         → 可选，需 --rename，生成 rename_audit.jsonl
```

## 进度可视化

每个步骤都有 Rich 进度条显示：
- 抽帧：Spinner + 耗时
- 转录：Spinner + 耗时
- LLM 标签：Spinner + 耗时
- 生成候选名：Spinner + 耗时

## 环境变量

`.env` 配置项（不得提交到 Git）：
```env
# GPT-Load 基础配置
GEMINI_BASE_URL=http://localhost:3001/proxy/free
GEMINI_API_KEY=sk-xxx

# 接口类型（推荐 openai_compat）
LLM_TRANSPORT=openai_compat

# 模型配置
MODEL_FLASH=gemini-2.5-flash
MODEL_PRO=gemini-2.5-pro

# 并发与超时
MAX_CONCURRENCY=32
REQUEST_TIMEOUT=30
```

**GPT-Load 接口说明**：
- `LLM_TRANSPORT=openai_compat`：使用 OpenAI 兼容接口（端点自动拼接 `/v1beta/openai/chat/completions`）
- `LLM_TRANSPORT=gemini_native`：使用 Gemini 原生接口（端点使用 `/v1beta/models/{model}:generateContent`）
- 详细对比参考：[gptload-api.md](./gptload-api.md)

## 故障排查

### 虚拟环境未激活
错误：`ModuleNotFoundError: No module named 'vrenamer'`

解决：
```powershell
.\.venv\Scripts\Activate.ps1
```

### GPT-Load 连接失败
错误：`Connection refused`

检查：
1. GPT-Load 是否运行：`http://localhost:3001`
2. 端口是否正确
3. API Key 是否有效

测试连接：
```powershell
.\.venv\Scripts\python.exe test_gptload.py
```

### ffmpeg 未安装
错误：`FileNotFoundError: 'ffmpeg'`

解决：
- Windows：下载 https://ffmpeg.org/download.html 并添加到 PATH
- 或使用 Chocolatey：`choco install ffmpeg`
- Pipeline 会缓存第一次探测到的路径，若更换安装位置请重启终端或进程
