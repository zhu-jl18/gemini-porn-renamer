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
  "model": "gemini-2.0-flash-exp",
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
MODEL_FLASH=gemini-2.0-flash-exp
MODEL_PRO=gemini-2.0-flash-thinking-exp
GEMINI_API_KEY=在此填写你的GPT-Load密钥
```

客户端会自动拼接：`{GEMINI_BASE_URL}/v1beta/openai/chat/completions`

### 使用 Gemini 原生接口

`.env` 配置：
```env
GEMINI_BASE_URL=http://localhost:3001/proxy/free
LLM_TRANSPORT=gemini_native
MODEL_FLASH=gemini-2.0-flash-exp
MODEL_PRO=gemini-2.0-flash-thinking-exp
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

## 参考资料

- GPT-Load 文档：（填入实际链接）
- OpenAI API 文档：https://platform.openai.com/docs/api-reference
- Gemini API 文档：https://ai.google.dev/docs
