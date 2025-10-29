# 配置说明（Configuration）

本文件说明 .env 与 YAML 配置项及推荐取值。所有参数均应可配置，严禁硬编码。

## 一、环境变量（.env）
- GEMINI_BASE_URL：GPT-Load 基础地址（free 通道：http://localhost:3001/proxy/free）
- GEMINI_API_KEY：GPT-Load 管理密钥
- LLM_TRANSPORT：openai_compat | gemini_native
- MODEL_FLASH：如 gemini-2.5-flash（分析）
- MODEL_PRO：如 gemini-2.5-pro（命名/汇总）
- MAX_CONCURRENCY：并发上限（建议 8–32）
- REQUEST_TIMEOUT：默认 30 秒
- RETRY：默认 3

## 二、YAML 配置
- config/analysis_tasks.yaml：任务开关、提示词文件、批次策略（后续将引入 images_per_call）
- config/llm_backends.yaml：后端与路由配置（free/pro 通道）
- config/naming_styles.yaml：命名风格
- config/aggregation.yaml：聚合策略（即将新增，默认 strategy: frequency）

## 三、关键参数建议（基于 Free Tier 实测）

### 3.1 并发参数
- **task_concurrency**（子任务并发）：4–8（默认 4）
  - 控制同时执行的分析子任务数（角色、脸部、场景、姿势）
  - 建议根据 GPT-Load Key 数量和网络带宽调整

- **batch_concurrency**（批次并发）：16–32（默认 16）
  - 控制每个子任务内同时执行的批次数
  - Free Tier 建议保守设置，避免触发速率限制

### 3.2 批次大小参数（重要）

**batch_size**（每批次帧数）：
- **Free Tier 实测结果**（2025-10-29）：
  - ✓ 成功：5/10/15/20/30/40/50 张图片/请求
  - ✗ 失败：25 张（空 content，疑似内容过滤或瞬时速率限制）
  - **建议默认值**：20（保守策略，避开 25 张异常区）
  - **建议上限**：50（实测可用，留冗余空间）

- **付费版升级预期**：
  - 可提升至 100-200/请求（官方上限 3,000-3,600）
  - 需根据网络带宽和延迟要求调整

**配置位置**：
- `src/vrenamer/core/config.py`: `AnalysisConfig.batch_size = 20`
- `config/analysis_tasks.yaml`: 各任务的 `batch_size: 20`
- `src/vrenamer/webui/settings.py`: `analysis_batch_size = 20`

### 3.3 音频转写参数（预留）

**transcript.enabled**：默认 `false`（功能待实现）
- 当前版本使用 `DummyTranscriptExtractor`（返回空字符串）
- 待 Gemini Audio API 测试通过后启用

**transcript.backend**：`dummy` | `gemini`（默认 `dummy`）
- `dummy`：占位实现，不执行实际转写
- `gemini`：使用 Gemini 2.5 Flash 音频输入（待实现）

**transcript.timeout**：60 秒（音频转写超时时间）

## 四、Free vs 付费版差异（实测完成）

| 参数                | Free Tier（实测）      | 付费版（Vertex AI） | 说明                   |
| ------------------- | ---------------------- | ------------------- | ---------------------- |
| **图片输入上限**    | 50 张/请求             | 3,000-3,600 张/请求 | Free Tier 远超预期     |
| **建议 batch_size** | 20（默认）/ 50（上限） | 100-200 起步        | 根据网络调整           |
| **音频转写**        | 待测试                 | 支持                | 测试遇阻，暂时搁置     |
| **并发能力**        | 受 Key 轮询限制        | 更高                | 依赖 GPT-Load Key 数量 |

**性能提升预期**（升级付费版后）：
- 批次大小可提升 5-10 倍（20 → 100-200）
- 总 API 调用次数减少 80-90%
- 处理速度提升 3-5 倍（减少网络往返）

## 五、验证方法

### 5.1 图片上限测试（已完成）
```powershell
.\.venv\Scripts\python.exe test_free_tier_limits.py --counts "5,10,20,50"
```
- 测试结果：5/10/15/20/30/40/50 张成功，25 张失败
- 详见：`docs/decisions.md` "Free Tier 限制与测试计划"

### 5.2 音频转写测试（待修复）
```powershell
.\.venv\Scripts\python.exe scripts\debug\test_audio_transcription.py --video "X:\Gallery\sample.mp4" --transport openai_compat
```
- 当前状态：gzip 解压问题导致脚本挂起
- 待办事项：修复后重新测试

### 5.3 配置验证
- 所有测试使用 `.env` 中参数
- 媒体文件不复制入项目目录（使用临时目录）
- 测试脚本实现指数退避重试（应对 429 速率限制）

