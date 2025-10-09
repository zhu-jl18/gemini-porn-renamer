# 环境搭建指南

本项目**强制要求使用虚拟环境**，所有开发、测试、运行操作必须在虚拟环境中执行。

## 前置要求

- Python 3.10+（建议 3.10 或 3.11，避免编译问题）
- ffmpeg（视频帧抽取）
- Git
- Windows PowerShell（Windows） 或 Bash（Linux/macOS）

## 快速开始（Windows）

### 1. 克隆仓库
```powershell
git clone <repository-url>
cd VideoRenamer
```

### 2. 创建虚拟环境
```powershell
# 使用 Python 3.10/3.11
python -m venv .venv
```

### 3. 激活虚拟环境
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# 如果遇到执行策略错误，运行：
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

激活成功后，命令行前缀会显示 `(.venv)`。

### 4. 安装核心依赖
```powershell
# 在虚拟环境内
pip install --upgrade pip
pip install httpx python-dotenv pydantic pydantic-settings typer rich

# （可选）如果需要完整功能，安装全部依赖
# 注意：av 包需要 C++ 编译环境
pip install -r requirements.txt
pip install -e .
```

### 5. 配置环境变量
```powershell
copy .env.example .env
notepad .env  # 编辑填入实际配置
```

必填项说明：
- `GEMINI_BASE_URL`：GPT-Load 代理地址（固定为 `http://localhost:3001/proxy/free`）
- `GEMINI_API_KEY`：GPT-Load 管理的鉴权 key
- `LLM_TRANSPORT`：接口类型
  - **`openai_compat`**（推荐）：OpenAI 兼容接口，自动拼接 `/v1beta/openai`
  - **`gemini_native`**：Gemini 原生接口，使用 `/v1beta/models/{model}:generateContent`
- `MODEL_FLASH`、`MODEL_PRO`：使用的模型名称

**GPT-Load 接口详细说明**：参考 [docs/gptload-api.md](./gptload-api.md)

### 6. 验证安装
```powershell
# 测试 GPT-Load 连接
.\.venv\Scripts\python.exe test_gptload.py

# 查看 CLI 帮助
.\.venv\Scripts\python.exe -m vrenamer.cli.main --help
```

## 常用命令速查

### 每次开发前激活环境
```powershell
.\.venv\Scripts\Activate.ps1
```

### 单视频测试（dry-run）
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --n 5 --dry-run
```

### 执行改名
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --rename
```

### 回滚改名
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main rollback logs/rename_audit.jsonl
```

## 依赖问题排查

### av 包安装失败
`av` 包（PyAV）需要 C++ 编译环境。如果安装失败：

**方案1：安装 Visual C++ Build Tools**
- 下载：https://visualstudio.microsoft.com/visual-cpp-build-tools/
- 安装时勾选"C++ 生成工具"

**方案2：使用预编译 wheel**
- 访问：https://www.lfd.uci.edu/~gohlke/pythonlibs/#av
- 下载对应 Python 版本的 `.whl` 文件
- 安装：`pip install av-xxx.whl`

**方案3：跳过 av 依赖**
- 当前核心功能不依赖 av，可以先跳过
- 仅安装：`pip install httpx python-dotenv pydantic pydantic-settings typer rich`

### faster-whisper 安装慢
如果下载慢或失败：
```powershell
pip install faster-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 退出虚拟环境
```powershell
deactivate
```

## 注意事项

1. **每次开发前必须激活虚拟环境**，否则会污染全局 Python
2. `.venv/` 已加入 `.gitignore`，不会提交到仓库
3. `.env` 文件包含敏感信息，**禁止提交到 Git**
4. 首次运行必须使用 `--dry-run` 模式验证
5. 定期更新依赖：`pip install --upgrade -r requirements.txt`
