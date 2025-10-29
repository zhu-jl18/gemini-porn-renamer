# GPT-Load API 接口说明

GPT-Load 提供两种接口协议，可根据需要选择使用。

## 接口类型对比

### 1. OpenAI 兼容接口（推荐）

**基础URL格式**：
```
http://localhost:3001/proxy/free/v1beta/openai
```

**完整端点**：
```
http://localhost:3001/proxy/free/v1beta/openai/chat/completions
```

**优势**：
- 标准 OpenAI API 格式，生态丰富
- 多模态图片拼接更简单（base64 inline）
- 支持 `response_format: {type: "json_object"}` 结构化输出
- 与大部分 LLM 工具链兼容

**响应格式**：
```json
{
  "choices": [{
    "finish_reason": "stop",
    "index": 0,
    "message": {
      "content": "...",
      "role": "assistant"
    }
  }],
  "model": "gemini-2.5-flash",
  "usage": {
    "completion_tokens": 100,
    "prompt_tokens": 50,
    "total_tokens": 150
  }
}
```

### 2. Gemini 原生接口

**基础URL格式**：
```
http://localhost:3001/proxy/free
```

**完整端点**：
```
http://localhost:3001/proxy/free/v1beta/models/{model}:generateContent
```

**优势**：
- 原生 Gemini API 格式
- 可能支持 Gemini 特有功能
- 直接访问最新模型特性

**响应格式**：
```json
{
  "candidates": [{
    "content": {
      "parts": [
        {"text": "..."}
      ],
      "role": "model"
    },
    "finishReason": "STOP"
  }]
}
```

## 项目配置

### 使用 OpenAI 兼容接口（当前默认）

`.env` 配置：
```env
GEMINI_BASE_URL=http://localhost:3001/proxy/free
LLM_TRANSPORT=openai_compat
MODEL_FLASH=gemini-2.5-flash
MODEL_PRO=gemini-2.5-pro
GEMINI_API_KEY=在此填写你的GPT-Load密钥
```

客户端会自动拼接：`{GEMINI_BASE_URL}/v1beta/openai/chat/completions`

### 使用 Gemini 原生接口

`.env` 配置：
```env
GEMINI_BASE_URL=http://localhost:3001/proxy/free
LLM_TRANSPORT=gemini_native
MODEL_FLASH=gemini-2.5-flash
MODEL_PRO=gemini-2.5-pro
GEMINI_API_KEY=在此填写你的GPT-Load密钥
```

客户端会拼接：`{GEMINI_BASE_URL}/v1beta/models/{model}:generateContent`

## 接口选择建议

### 推荐使用 OpenAI 兼容接口
- ✅ 更成熟的生态支持
- ✅ 多模态处理更简洁
- ✅ JSON 结构化输出更可靠
- ✅ 代码可移植性强（切换到其他提供商）

### 使用 Gemini 原生接口的场景
- 需要 Gemini 独有功能
- OpenAI 接口不支持某些参数
- 调试原生 API 行为

## 测试连接

### 测试脚本
```powershell
.\.venv\Scripts\python.exe test_gptload.py
```

测试内容：
1. 文本补全（JSON 响应）
2. 多模态图片分析

### 预期输出
```
=== Testing GPT-Load Connection ===

✓ Text completion: True
✓ Multimodal: True
```

## 常见问题

### Q: 如何切换接口类型？
A: 修改 `.env` 中的 `LLM_TRANSPORT` 参数：
- `openai_compat` → OpenAI 兼容接口
- `gemini_native` → Gemini 原生接口

### Q: 两种接口性能有差异吗？
A: 底层都是 Gemini 模型，性能理论相同。差异主要在协议格式和功能支持。

### Q: 可以同时使用两种接口吗？
A: 可以，但需在代码中明确指定。默认情况下由 `LLM_TRANSPORT` 全局控制。

### Q: GPT-Load 键轮询如何工作？
A: GPT-Load 内置上万个 Gemini API Key，自动负载均衡和轮询，客户端无需关心。只需设置好 `GEMINI_API_KEY`（GPT-Load 管理密钥）即可。


## Free Tier vs 付费版限制差异（实测完成）

### 图片输入限制（2025-10-29 实测）

**测试环境**：
- API Key 类型：Google AI Studio Free Tier
- 测试工具：`test_free_tier_limits.py`
- 测试视频：`X:\Gallery\#DDR JK王冬儿 被教导主任 换衣间 睡奸.mp4`

**实测结果**：
| 图片数量 | 结果       | 说明                     |
| -------- | ---------- | ------------------------ |
| 5-20 张  | ✓ 全部成功 | -                        |
| 25 张    | ✗ 失败     | 返回空 content（非 429） |
| 30-50 张 | ✓ 全部成功 | -                        |

**关键发现**：
1. **Free Tier 支持远超预期**：实测 50 张图片/请求成功，远高于社区传言的 10 张限制
2. **25 张异常失败**：唯一失败点在 25 张，但 30/40/50 张均成功，说明这不是硬性上限
3. **失败原因分析**：可能是内容过滤、Key 轮询瞬时问题或 GPT-Load 路由到不同后端

**架构参数建议**：
- **Free Tier**：
  - 默认 `batch_size = 20`（保守策略，避开 25 张异常区）
  - 上限 `batch_size_max = 50`（实测可用）
- **付费版（Vertex AI）**：
  - 官方上限：3,000-3,600 张/请求
  - 建议起步值：100-200 张/请求
  - 可根据网络带宽和延迟要求进一步提升

**性能提升预期**（升级付费版后）：
- 批次大小可提升 5-10 倍（20 → 100-200）
- 总 API 调用次数减少 80-90%
- 处理速度提升 3-5 倍（减少网络往返）

### 音频转写支持（测试遇阻）

**测试状态**：
- 测试工具：`scripts/debug/test_audio_transcription.py`
- 当前问题：gzip 解压错误导致脚本挂起
- 待办事项：修复 gzip 处理逻辑后重新测试

**临时方案**：
- 音频转写功能暂时搁置
- 使用占位接口 `DummyTranscriptExtractor`（返回空字符串）
- 配置开关 `transcript.enabled = false`（默认禁用）

### 验证方法

**图片上限测试**（已完成）：
```powershell
.\.venv\Scripts\python.exe test_free_tier_limits.py --counts "5,10,20,50"
```

**音频转写测试**（待修复）：
```powershell
.\.venv\Scripts\python.exe scripts\debug\test_audio_transcription.py --video "X:\Gallery\sample.mp4" --transport openai_compat
```

详细测试结果参考：`docs/decisions.md` "Free Tier 限制与测试计划"

## 参考资料

- GPT-Load 文档：（填入实际链接）
- OpenAI API 文档：https://platform.openai.com/docs/api-reference
- Gemini API 文档：https://ai.google.dev/docs
