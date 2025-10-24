# 调试脚本使用指南

## 概述

本目录包含各模块的独立调试脚本，用于开发和测试。每个脚本都可以独立运行，无需完整的应用环境。

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
python scripts/debug/debug_naming.py --tags '{"role_archetype":["人妻"]}' --styles new_style
```

## 详细说明

### debug_video.py - 视频处理模块

**功能**：
- 检查 ffmpeg 和 ffprobe 是否可用
- 测试视频时长获取
- 测试视频抽帧
- 验证帧去重逻辑

**用法**：
```bash
python scripts/debug/debug_video.py path/to/video.mp4
```

**输出**：
- 视频时长
- 抽取的帧数
- 帧文件列表（前 5 个）
- 帧保存目录

**示例**：
```bash
$ python scripts/debug/debug_video.py test.mp4
============================================================
视频处理模块调试
============================================================

[1/3] 检查视频时长...
  ✓ 时长: 180.50 秒

[2/3] 抽取视频帧...
  ✓ 抽取帧数: 96
  ✓ 保存目录: frames/test
  ✓ 抽帧帧率: 0.5319 fps

[3/3] 验证帧文件...
  1. frame_00001.jpg (45.23 KB)
  2. frame_00002.jpg (46.12 KB)
  ...

✅ 视频处理模块测试完成
```

### debug_analysis.py - 分析模块

**功能**：
- 测试两层并发策略
- 验证子任务配置加载
- 测试提示词加载
- 支持 mock 模式（无需真实 API）

**用法**：
```bash
# 使用真实 API
python scripts/debug/debug_analysis.py frames/video_name

# 使用 mock（无需 API key）
python scripts/debug/debug_analysis.py frames/video_name --mock
```

**输出**：
- 加载的帧数
- 并发配置信息
- 每个批次的处理进度
- 最终分析结果

**示例**：
```bash
$ python scripts/debug/debug_analysis.py frames/test --mock
============================================================
分析模块调试（两层并发）
============================================================

使用 Mock LLM 客户端（无需真实 API）
加载 80 个帧文件

开始分析（两层并发）...
  第一层并发: 4 个子任务
  第二层并发: 16 个批次

  [role_archetype] 批次 1/16 完成: ['标签A']
  [face_visibility] 批次 1/16 完成: ['标签B']
  ...

============================================================
分析结果：
============================================================
  role_archetype: ['标签A', '标签B']
  face_visibility: ['露脸']
  scene_type: ['办公室']
  positions: ['传教士']

✅ 分析模块测试完成
```

### debug_naming.py - 命名模块

**功能**：
- 测试命名风格加载
- 测试提示词构建
- 测试候选生成
- 验证文件名清理

**用法**：
```bash
# 使用默认风格
python scripts/debug/debug_naming.py --tags '{"role_archetype": ["人妻"], "scene_type": ["办公室"]}'

# 指定风格
python scripts/debug/debug_naming.py --tags '{"role_archetype": ["人妻"]}' --styles chinese_descriptive,scene_role
```

**输出**：
- 输入标签
- 使用的风格
- 生成的候选名称列表

**示例**：
```bash
$ python scripts/debug/debug_naming.py --tags '{"role_archetype": ["人妻"], "scene_type": ["办公室"]}'
============================================================
命名模块调试
============================================================

输入标签: {
  "role_archetype": ["人妻"],
  "scene_type": ["办公室"]
}
使用风格: ['chinese_descriptive', 'scene_role']

生成候选名称...

生成 2 个候选：
============================================================
1. [中文描述性] 办公室的秘密时光 (zh)
2. [场景角色] 办公室_美丽人妻 (zh)

✅ 命名模块测试完成
```

### debug_llm.py - LLM 客户端

**功能**：
- 测试不同 LLM 后端（Gemini、OpenAI）
- 验证 API 连接
- 测试响应解析
- 对比不同后端的输出

**用法**：
```bash
# 测试 Gemini 生成任务
python scripts/debug/debug_llm.py --backend gemini --test generate

# 测试 OpenAI 分类任务
python scripts/debug/debug_llm.py --backend openai --test classify

# 测试所有功能
python scripts/debug/debug_llm.py --backend gemini --test both
```

**输出**：
- 客户端类型
- API 响应内容
- 响应解析结果

**示例**：
```bash
$ python scripts/debug/debug_llm.py --backend gemini --test generate
============================================================
LLM 客户端调试
============================================================

使用后端: gemini
✓ 客户端创建成功: GeminiClient

[测试] 生成任务...
------------------------------------------------------------
响应长度: 156 字符
响应内容:
{"names": ["创意文件名1", "创意文件名2", "创意文件名3"]}

✓ 生成任务测试成功

============================================================
✅ LLM 客户端测试完成
============================================================
```

## 日志输出

所有调试脚本都会输出详细日志到 `logs/` 目录，便于事后分析：

- `logs/vrenamer.log` - 主日志文件
- 日志级别：DEBUG（包含所有详细信息）

## Mock 模式

部分脚本支持 `--mock` 参数，使用 mock 数据避免真实 API 调用，适合：

- ✅ 快速测试逻辑
- ✅ 无网络环境
- ✅ 节省 API 配额
- ✅ 开发新功能时的单元测试

## 常见问题

### Q: 脚本找不到模块？

A: 确保在项目根目录运行脚本，或者脚本会自动添加项目路径到 Python 路径。

### Q: 如何查看详细日志？

A: 查看 `logs/vrenamer.log` 文件，或者在脚本中设置 `LOG_LEVEL=DEBUG`。

### Q: Mock 模式和真实模式有什么区别？

A: Mock 模式使用假数据，不调用真实 API，适合快速测试。真实模式调用实际的 LLM API，需要配置 API key。

### Q: 如何添加新的调试脚本？

A: 参考现有脚本的结构，创建新的 Python 文件，确保：
1. 添加项目路径到 sys.path
2. 使用 AppLogger 记录日志
3. 提供清晰的命令行参数
4. 输出详细的调试信息

## 最佳实践

1. **开发时先用 mock**：开发新功能时，先用 mock 模式验证逻辑，再用真实 API 测试
2. **保存日志**：遇到问题时，保存日志文件以便分析
3. **小步测试**：每次只测试一个模块，逐步验证
4. **对比输出**：修改代码后，对比修改前后的输出差异

## 相关文档

- [架构设计](../../docs/architecture.md)
- [模块文档](../../docs/modules/)
- [测试指南](../../docs/testing-guide.md)
