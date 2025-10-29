# 维护守则（Maintenance）

本守则用于指导日常运维、参数调整、问题排查与文档同步更新。

## 一、提示词（Prompts）
- 位置：config/prompts/**
- 修改流程：
  1) 在分支上修改并注明动机与预期指标；
  2) 本地使用单视频 dry-run 验证；
  3) 在 docs/decisions.md 记录变更与效果；
  4) 合并后更新 presets/引用与版本号（如有）。
- 头部注入/替换：通过配置开关（预留），支持 prepend/append/override。

## 二、分析任务（Analysis）

### 2.1 新增任务
在 `config/analysis_tasks.yaml` 增加条目：
- `enabled`: 是否启用任务
- `prompt_file`: 提示词文件名（位于 `config/prompts/analysis/`）
- `batch_size`: 每批次帧数（默认 20，上限 50）

### 2.2 并发与批次参数调优

**子任务并发（task_concurrency）**：
- 默认值：4（同时执行 4 个分析子任务）
- 调整建议：根据 GPT-Load Key 数量和网络带宽调整（4-8）
- 配置位置：`src/vrenamer/core/config.py` → `ConcurrencyConfig.task_concurrency`

**批次并发（batch_concurrency）**：
- 默认值：16（每个子任务内同时执行 16 个批次）
- 调整建议：Free Tier 建议保守设置（16-32），避免触发速率限制
- 配置位置：`src/vrenamer/core/config.py` → `ConcurrencyConfig.batch_concurrency`

**批次大小（batch_size）**：
- **Free Tier 实测结果**（2025-10-29）：
  - 默认值：20（保守策略，避开 25 张异常区）
  - 上限值：50（实测可用）
  - 配置位置：
    - `src/vrenamer/core/config.py` → `AnalysisConfig.batch_size`
    - `config/analysis_tasks.yaml` → 各任务的 `batch_size`
    - `src/vrenamer/webui/settings.py` → `analysis_batch_size`
- **付费版升级后**：
  - 可提升至 100-200/请求（官方上限 3,000-3,600）
  - 需根据网络带宽和延迟要求调整

**调优流程**：
1. 修改配置文件中的参数
2. 使用测试视频验证（`--dry-run`）
3. 观察日志中的批次数量和处理时间
4. 根据实际情况微调参数
5. 记录调优结果到 `docs/decisions.md`

## 三、命名风格（Naming）
- 风格文件：examples/naming_styles.yaml
- 生成候选：保持 JSON-only 输出，命名清理（非法字符→"_"）需保留；
- 新增风格：提交前进行少量样本对比测试。

## 四、字幕/音频转写（Transcript）

### 4.1 当前状态（预留功能）
- **功能状态**：占位接口已创建，实际转写功能待实现
- **默认行为**：使用 `DummyTranscriptExtractor`，返回空字符串
- **配置开关**：`transcript.enabled = false`（默认禁用）

### 4.2 配置参数
- **transcript.enabled**：是否启用音频转写（默认 `false`）
- **transcript.backend**：后端类型（`dummy` | `gemini`，默认 `dummy`）
- **transcript.timeout**：音频转写超时时间（默认 60 秒）

### 4.3 实现计划
**待实现功能**：
1. 使用 ffmpeg 提取音频为 16kHz mono WAV
2. 调用 Gemini 2.5 Flash Audio API 进行转写
3. 处理 gzip 压缩响应（参考 `src/vrenamer/llm/client.py`）
4. 实现重试和错误处理

**参考资源**：
- 测试脚本：`scripts/debug/test_audio_transcription.py`（gzip 解压问题待修复）
- 占位接口：`src/vrenamer/services/transcript.py`
- 测试结果：`docs/decisions.md` "Free Tier 音频转写测试"

### 4.4 故障回退策略
- 提取失败时不阻断主流程
- 记录错误日志到 `logs/transcript_errors.log`
- 返回空字符串，继续后续处理

## 五、常见问题排查

### 5.1 API 相关问题
**API 限流/429 错误**：
- 降低并发参数（`task_concurrency` 或 `batch_concurrency`）
- 增加重试退避时间（`BACKOFF_BASE`）
- 检查 GPT-Load 状态和 Key 轮询情况
- 查看日志中的重试记录

**超时错误**：
- 提高 `REQUEST_TIMEOUT`（默认 30 秒）
- 减少 `batch_size`（降低单次请求负载）
- 检查网络连接和 GPT-Load 响应时间

**空 content 响应**（如 25 张图片失败）：
- 可能原因：内容过滤、安全检查、Key 轮询瞬时问题
- 解决方案：将空 content 视为可重试错误，自动重试
- 参考：`docs/decisions.md` "图片输入限制测试结果"

### 5.2 解析和处理问题
**JSON 解析失败**：
- 使用宽松 JSON 解析（`parse_json_loose`）
- 必要时保存原始响应到 `logs/raw_responses/`
- 检查提示词是否明确要求 JSON-only 输出

**ffmpeg/ffprobe 缺失**：
- 安装 ffmpeg 并确保在 PATH 中可访问
- Windows: 下载 ffmpeg.exe 并添加到系统 PATH
- 验证：`ffmpeg -version` 和 `ffprobe -version`

**生成文件名异常**：
- 检查非法字符替换逻辑（`< > : " / \ | ? *` → `_`）
- 检查长度限制（默认 ≤80 字符）
- 查看 `logs/rename_audit.jsonl` 中的命名记录

### 5.3 性能问题
**处理速度慢**：
- 检查 `batch_size` 是否过小（建议 20-50）
- 检查并发参数是否过低
- 查看日志中的批次数量和处理时间
- 考虑升级到付费版（batch_size 可提升至 100-200）

**内存占用高**：
- 减少 `batch_concurrency`（降低同时处理的批次数）
- 检查帧去重逻辑是否正常工作
- 清理临时目录中的旧帧文件


### 5.4 测试自动化（非交互模式）
- 单视频 CLI（vrenamer.cli.main run）支持 `--non-interactive`，自动选择候选 1，无需人工输入
- 可与 `--dry-run` 组合用于 CI 快速验证；真实调用请去掉 `--dry-run`
- 交互式 CLI 仍为人工操作优先，自动化建议使用单视频 CLI

## 六、配置修改与验证
- 所有变更应通过 .env 或 YAML；严禁硬编码；
- 修改后执行：
  - 单元测试：.\.venv\Scripts\python.exe -m pytest -q
  - Free Tier 图片上限验证：.\.venv\Scripts\python.exe test_free_tier_limits.py --video "X:\\Gallery\\sample.mp4"
  - 音频转写验证：.\.venv\Scripts\python.exe test_audio_transcription.py --video "X:\\Gallery\\sample.mp4"
- 验证结果同步记录到 docs/decisions.md。

## 七、文档同步
- 任何影响行为、接口或运维的变更，必须同步更新：
  - docs/decisions.md（技术决策）
  - docs/maintenance.md（本守则）
  - 如涉及 API/配置，更新 docs/gptload-api.md 与 docs/configuration.md

