# AI Agent 协作准则

本文档专为 AI Agent 设计，定义开发协作规范、代码风格、技术约束。

## 🎯 项目目标

基于 Gemini 多模态的成人视频自动重命名工具。核心能力：目录扫描、智能分析、规范命名、安全回滚。

**四大核心需求**：
1. **单视频处理为主**：每次处理一个视频，展示完整流程和输出
2. **目录扫描器**：递归扫描，识别需处理视频和乱码文件名
3. **高并发工作流**：充分利用 GPT-Load 上万 key 和自动轮询
4. **迭代优化机制**：收集误命名样本，持续优化提示词

## ⚠️ 强制约束

1. **虚拟环境隔离**：所有开发/测试/运行必须在虚拟环境中执行
2. **安全第一**：`.env` 绝不提交，首次必用 `--dry-run`
3. **简洁专业**：文档语言简洁专业清晰，禁止浮夸语气
4. **及时更新**：代码变更必须同步更新文档
5. **文档组织原则**：
   - **README.md** 只作为项目入口和文档索引
   - **详细内容** 必须放在 `docs/` 或专门文档中
   - **禁止重复**：同一内容不得在多处重复，使用交叉引用

## 📁 项目结构

```
VideoRenamer/
├── src/vrenamer/          # 核心代码
│   ├── cli/              # CLI 工具
│   ├── llm/              # LLM 客户端
│   ├── workflows/        # 工作流调度（待实现）
│   └── webui/            # WebUI（开发中）
├── docs/                 # 所有文档集中
├── examples/             # 命名样例（Few-shot）
├── prompts/              # 提示词模块
│   ├── modules/          # 任务模块化提示词
│   ├── base.system.md    # 基础系统提示
│   └── preset.yaml       # 预设配置
├── tests/                # pytest 测试（待补充）
└── logs/                 # 运行日志（不入库）
```

**工作流**：
```
[Scanner] -> [Analyzer(Gemini)] -> [Renamer] -> [Audit]
                 ^                      |
                 |---- Iterate ---------|
```

## 💻 开发命令（虚拟环境内）

### 环境配置
```powershell
# 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装核心依赖（避免编译问题）
pip install httpx python-dotenv pydantic pydantic-settings typer rich

# 完整依赖（可选）
pip install -r requirements.txt
pip install -e .
```

### 运行测试
```powershell
# 单视频分析（dry-run）
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --n 5

# 执行改名
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\test.mp4" --rename

# 回滚
.\.venv\Scripts\python.exe -m vrenamer.cli.main rollback logs/rename_audit.jsonl
```

详细使用参考：[docs/cli.md](docs/cli.md)

## 🎨 代码规范

### Python 风格
- **PEP8** 标准
- 缩进：4 空格
- 命名：`snake_case`（函数/变量）、`PascalCase`（类）、`UPPER_SNAKE`（常量）
- Type hints：必须使用（Python 3.10+）

### 文件命名规范

**AI 创造性命名**，通过风格配置文件动态生成。

#### 风格配置
- 配置文件：`examples/naming_styles.yaml`
- 内置 6 种风格：中文描述性、场景角色、P站风格等
- 支持用户自定义风格

#### 命名示例
```
温泉旅馆的诱惑.mp4                    # 中文描述性
温泉旅馆_美丽人妻.mp4                  # 场景+角色
Hot MILF seduced in hotel.mp4        # P站风格
温泉诱惑.mp4                          # 简洁标题
```

#### 命名规则
- 非法字符替换为 `_`：`< > : " / \ | ? *`
- 空白压缩为单个空格或 `_`
- 长度限制：≤80 字符（可配置）
- 演员名可选（未识别时省略）

详细风格配置参考：`examples/naming_styles.yaml`

## 🔧 配置管理

### 环境变量（`.env`）
```env
# GPT-Load 基础配置
GEMINI_BASE_URL=http://localhost:3001/proxy/free
GEMINI_API_KEY=在此填写你的GPT-Load密钥

# 接口类型
LLM_TRANSPORT=openai_compat  # openai_compat 或 gemini_native

# 模型配置
MODEL_FLASH=gemini-2.0-flash-exp
MODEL_PRO=gemini-2.0-flash-thinking-exp

# 并发与超时
MAX_CONCURRENCY=32
REQUEST_TIMEOUT=30
RETRY=3
```

**接口说明**：
- `openai_compat`：使用 OpenAI 兼容接口（推荐）
  - 端点：`{BASE_URL}/v1beta/openai/chat/completions`
- `gemini_native`：使用 Gemini 原生接口
  - 端点：`{BASE_URL}/v1beta/models/{model}:generateContent`

详细对比：[docs/gptload-api.md](docs/gptload-api.md)

## 🧪 测试规范

### 测试结构
- 文件：`tests/test_*.py`
- 覆盖率：关键路径 ≥80%
- 外部 API：必须 mock
- 样本视频：控制在 5-30s

### 关键测试路径
1. 目录扫描（包括乱码识别）
2. 视频分析（多模态）
3. 命名生成（幂等性）
4. 改名回滚（可逆性）
5. 失败重试（指数退避）

## 📝 文档组织规范

### 文档分层
1. **README.md**（根目录）
   - 项目简介（1-2 句话）
   - 快速开始（最小化命令）
   - 文档导航表格（索引）
   - 禁止：详细教程、配置说明、开发状态

2. **核心需求.md**（根目录）
   - 项目背景和技术约束
   - 四大核心需求详解
   - 命名规范和开发原则

3. **AGENTS.md**（根目录）
   - AI Agent 协作准则
   - 代码规范和开发流程
   - 不包含：用户教程、详细配置

4. **docs/**（详细文档）
   - `setup.md`：环境搭建完整指南
   - `cli.md`：CLI 使用详细说明
   - `gptload-api.md`：API 接口详细对比
   - `NEXT_STEPS.md`：开发路线图
   - `decisions.md`：技术决策记录
   - `README.md`：文档索引

### 避免重复原则
- ❌ **错误示例**：README 中写安装步骤，docs/setup.md 再写一遍
- ✅ **正确示例**：README 写 4 行快速命令 + 链接到 docs/setup.md

### 交叉引用格式
```markdown
详细配置参考：[docs/setup.md](docs/setup.md)
完整开发计划：[docs/NEXT_STEPS.md](docs/NEXT_STEPS.md)
```

## 📝 Prompt 协作

### Prompt 组织
- **基座**：`prompts/base.system.md`
- **模块**：`prompts/modules/*`（任务模块化）
- **预设**：`prompts/preset.yaml`（自定义配置）

### 修改 Prompt 必须
1. 说明变更动机与预期指标
2. 保持"仅输出 JSON"的约束
3. 记录回滚版本

## 🔄 开发流程

### 计划先行
- 写明步骤（5-7 词短语）
- 明确 `in_progress` 项（单项）
- 预估影响范围

### 渐进式开发
1. **最小可运行版本**：先跑通核心流程
2. **单元验证**：每个模块独立测试
3. **增量迭代**：逐步补充功能
4. **止损机制**：失败 3 次换路线，记录问题

### 代码审查
- 安全：无硬编码密钥、敏感信息
- 健壮：超时/重试/降级策略
- 可维护：清晰注释、模块化设计

## 🛡️ 安全规范

### 密钥管理
- ✅ 从 `.env` 读取
- ❌ 禁止硬编码
- ❌ 禁止提交真实 Key

### 外部调用
- 必配：超时、重试、速率限制
- 降级：失败不影响数据安全
- 日志：记录审计信息

### 文件操作
- 首次必用 `--dry-run`
- 所有改名写入 `logs/rename_audit.jsonl`
- 支持一键回滚

## 📋 提交规范

### Commit 格式
遵循 Conventional Commits：
```
<type>: <description>

<body>
```

**Type**：
- `feat`：新功能
- `fix`：修复 bug
- `docs`：文档更新
- `refactor`：重构
- `test`：测试
- `chore`：构建/工具

### 交接规范
每次交接更新：
- `docs/NEXT_STEPS.md`：当前状态
- `docs/decisions.md`：技术决策
- README 相关章节

## 📚 文档导航

- **[README.md](README.md)**：项目总览
- **[docs/setup.md](docs/setup.md)**：环境搭建
- **[docs/cli.md](docs/cli.md)**：CLI 使用
- **[docs/gptload-api.md](docs/gptload-api.md)**：API 说明
- **[docs/NEXT_STEPS.md](docs/NEXT_STEPS.md)**：开发路线
- **[docs/decisions.md](docs/decisions.md)**：技术决策

## 🎯 当前优先级

### P0 - 核心功能（进行中）
1. 单视频流程完善（错误处理、重试）
2. 目录扫描器（乱码识别）
3. 高并发工作流（asyncio + Semaphore）

### P1 - 质量提升
4. 迭代优化机制（样本管理）
5. 错误处理和日志

### P2 - 体验优化
6. WebUI 集成
7. 命名规则增强

详细计划：[docs/NEXT_STEPS.md](docs/NEXT_STEPS.md)
