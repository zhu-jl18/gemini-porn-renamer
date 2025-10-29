# 设计/实现决策记录（滚动）

- 2025-10-08: 单视频优先，默认管线使用“抽帧+本地转录→文本送 Flash”，原因：代理音频能力不确定；可切换至直传音频后再评估。
- 2025-10-08: LLM 传输优先走 GPT‑Load 的 OpenAI 兼容端点（/v1beta/openai/chat/completions），因多模态图片拼接更简单；保留 gemini_native 作为备选。



---

## 2025-01-10: 命名风格系统设计

### 背景
初始设计采用固定格式 {Studio}_{Series}_{Title}_{Year}_{Actors}_{Resolution}_{Source}_{Lang}_{Hash8}.ext，用户反馈过于刚性，希望 AI 能创造性命名，支持多种风格（如优雅中文、Pornhub 风格等）。

### 决策
1. **配置驱动**：采用 YAML 配置文件 (examples/naming_styles.yaml) 定义风格
2. **内置 6 种风格**：
   - chinese_descriptive（优雅中文）
   - scene_role（场景+角色）
   - role_scene_action（详细描述）
   - pornhub_style（英文直接）
   - concise（简洁标题）
   - with_actor（带演员名）
3. **架构**：
   - NamingStyleConfig (Pydantic)：配置加载和验证
   - NamingGenerator：多风格并行生成候选
   - Settings 集成：从 .env 读取默认风格
4. **CLI 接口**：
   - --use-styles：启用风格系统
   - --styles：指定风格（逗号分隔）
5. **响应解析**：支持 JSON 和文本回退，智能提取命名列表

### 影响
- 兼容现有流程：保留旧的 generate_names，新增 generate_names_with_styles
- 用户体验提升：多风格候选供用户选择，表格显示风格信息
- 扩展性：用户可在 YAML 中添加自定义风格

### 测试
- 单元测试：	ests/test_naming_styles.py（5 个测试全部通过）
- 覆盖：配置加载、风格验证、文件名清理、风格获取

---

## 2025-10-24: Pipeline 异步化与 LLM 适配器

### 背景
原先 `sample_frames` 在异步函数中直接调用 `subprocess.run`，阻塞事件循环；`generate_names_with_styles` 也直接把 `GeminiClient` 传入 `NamingGenerator`，导致缺少 `BaseLLMClient.generate` 实现并在 `--use-styles` 时抛出异常。

### 决策
1. **异步外部命令**：使用 `asyncio.create_subprocess_exec` 获取时长，`asyncio.to_thread` 执行 ffmpeg，并缓存 `ffmpeg/ffprobe` 路径。
2. **LLM 适配器**：新增 `GeminiLLMAdapter`，实现 `BaseLLMClient` 接口并封装 `classify_json` / `name_candidates`。
3. **帧分配策略**：`_build_frame_batches` 引入最小/最大批次与小样本轮询，避免每个任务重复全量抽帧。

### 影响
- CLI dry-run 响应更流畅，可同时执行多个视频不互相阻塞。
- 风格命名在开启 `--use-styles` 时稳定运行，支持非法字符清理与 JSON 回退。
- 日志新增帧利用率指标，便于观测并发效果。

### 测试
- `pytest -q` 全绿，新增 `tests/test_pipeline.py` 覆盖适配器与批次逻辑。


---

## 2025-10-29: Free Tier 限制与测试计划（P0）

### 背景
Google AI Studio Free Tier 的多模态图片与音频能力可能低于 Vertex/付费版规格；社区存在“仅 ~10 张图片/请求”的说法，需以自测校准架构参数。

### 决策
1) 以脚本实测为准，避免直接套用付费版规格；
2) 若 Free Tier ≤10 张/请求，则将 images_per_call 默认值设为 8（保留冗余），上限 10；文档标注升级后的预期收益；
3) 音频转写分别测试 openai_compat 与 gemini_native 两种协议，视结果决定默认后端与回退策略。

### 执行
- 图片上限：test_free_tier_limits.py（5/10/20/50 张）
- 音频转写：test_audio_transcription.py（两种传输协议各一次）
- 均从 .env 读取参数，媒体文件不复制入仓库（临时目录抽取/转码）；
- 结论回写至 docs/configuration.md 与本页。

### 测试结果（2025-10-29 实测完成）

**图片输入限制测试**：
- 测试环境：Google AI Studio Free Tier，视频 `#DDR JK王冬儿...mp4`，抽帧 1278 张
- 测试结果：5/10/15/20/30/40/50 张 ✓ 成功，25 张 ✗ 失败（空 content，非 429）
- **关键发现**：Free Tier 支持 50 张图片/请求，远超社区传言的 10 张限制
- **异常分析**：25 张失败但 30/40/50 成功，疑似特定帧内容触发安全过滤或 Key 轮询瞬时问题
- **架构参数建议**：
  - images_per_call 默认值：**20**（保守，避开 25 张异常区）
  - images_per_call 上限：**50**（实测可用，留冗余）
  - 付费版升级预期：可提升至 100-200/请求（官方上限 3,000）

**音频转写测试**：
- 测试状态：进行中，遇到 gzip 解压问题导致脚本挂起
- 已知问题：GPT-Load 返回 gzip 压缩响应，`auto_decompress=False` 导致 UTF-8 解码失败
- 待办事项：修复解压逻辑后重新测试 openai_compat 和 gemini_native 两种协议

---

## 2025-10-29: 架构重构 - 参数化 batch_size（P1）

### 背景
基于 Free Tier 实测结果（50 张图片/请求可用，建议默认 20），需要将所有硬编码的 `batch_size = 5` 改为从配置读取，并调整默认值。

### 决策

**1. 配置参数调整**：
- `src/vrenamer/core/config.py`:
  - `AnalysisConfig.batch_size`: 5 → 20
  - 新增 `AnalysisConfig.batch_size_max`: 50
  - 新增验证器：确保 `batch_size <= batch_size_max`
- `config/analysis_tasks.yaml`:
  - 所有任务的 `batch_size`: 5 → 20
  - 添加注释说明 Free Tier 限制和付费版升级预期
- `src/vrenamer/webui/settings.py`:
  - 新增 `analysis_batch_size = 20`
  - 新增 `analysis_batch_size_max = 50`

**2. 移除硬编码**：
- `src/vrenamer/webui/services/pipeline.py`:
  - 移除 `IMAGES_PER_CALL = 5` 硬编码
  - 改为从 `settings.analysis_batch_size` 读取

**3. 字幕/音频转写占位接口**：
- 创建 `src/vrenamer/services/transcript.py`:
  - 抽象基类 `TranscriptExtractor`
  - 占位实现 `DummyTranscriptExtractor`（返回空字符串）
  - 预留实现 `GeminiTranscriptExtractor`（待开发）
- 配置支持：
  - `TranscriptConfig.enabled = false`（默认禁用）
  - `TranscriptConfig.backend = "dummy"`
  - `TranscriptConfig.timeout = 60`

### 理由
1. **消除硬编码**：所有参数从配置读取，便于调优和升级
2. **基于实测数据**：默认值 20 是保守策略，避开 25 张异常区
3. **预留扩展空间**：上限 50 为 Free Tier 实测可用值，付费版可提升至 100-200
4. **功能预留**：字幕转写接口占位，不阻塞核心功能开发

### 影响范围
- **配置文件**：3 个文件修改（config.py, analysis_tasks.yaml, settings.py）
- **代码文件**：4 个文件修改
  - `src/vrenamer/webui/services/pipeline.py`：移除硬编码，集成 transcript 接口
  - `src/vrenamer/services/transcript.py`：新增占位接口
  - `src/vrenamer/cli/interactive.py`：修复 await 调用
  - `src/vrenamer/cli/main.py`：修复 await 调用
- **测试文件**：1 个文件修复（test_pipeline.py）
- **文档文件**：4 个文件更新（configuration.md, maintenance.md, gptload-api.md, decisions.md）

### 验收标准
- ✅ 所有硬编码的 `batch_size = 5` 已移除
- ✅ 配置文件反映 Free Tier 测试结果（默认 20，上限 50）
- ✅ transcript 接口已创建并集成到 pipeline
- ✅ transcript 默认禁用（使用 DummyTranscriptExtractor）
- ✅ 所有相关文档已同步更新
- ✅ 所有测试通过（8/8），功能未受影响
- ✅ 无 IDE 诊断问题

### 实施完成时间
2025-10-29（阶段 1-4 全部完成）


---

## 2025-10-29: 修复 Gemini 调用可观测性 + CLI 非交互模式（P0）

### 背景
用户反馈：GPT-Load 后台无任何调用记录、CLI 仅输出占位名称。排查发现单视频旧 CLI 默认 `--dry-run` 开启，导致未发起真实请求；同时缺少请求日志，排障困难。

### 决策与变更
1. 单视频 CLI 默认关闭 dry-run（仍保留 `--dry-run` 开关）
2. 新增 `--non-interactive` 选项，测试时自动选择候选 1，无需人工输入
3. 增强 LLM 客户端请求日志（URL/Headers/Body 验证，自动脱敏 base64 与 Token）
   - 文件：`src/vrenamer/llm/client.py`、`src/vrenamer/llm/gemini.py`
   - 端点：`/v1beta/openai/chat/completions` 与 `/v1beta/models/{model}:generateContent`

### 验收标准
- GPT-Load 后台可见每次请求记录（即使失败）
- 真实候选名称成功返回（不再是占位符）
- 测试脚本可在 CI 环境无交互运行

### 文档同步
- `docs/cli.md`：更新默认行为与 `--non-interactive`
- `docs/maintenance.md`：新增“测试自动化（非交互模式）”
