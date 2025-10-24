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
