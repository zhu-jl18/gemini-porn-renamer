# 测试验证指南

**文档版本**: v1.1  
**最后更新**: 2025-10-24  
**测试目标**: 确认异步管线、帧分配策略以及 LLM 适配器的稳定性。

---

## 🎯 测试前准备

1. 激活虚拟环境：`.\.venv\Scripts\Activate.ps1`
2. 确保核心依赖与图像库已安装：  
   `pip install httpx python-dotenv pydantic pydantic-settings typer rich pillow imagehash`
3. 校验 ffmpeg / ffprobe 是否在 PATH 中：`ffmpeg -version`、`ffprobe -version`

---

## ✅ 自动化测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

预期输出：`8 passed`（包含 `tests/test_pipeline.py` 新增用例）。  
关键断言：
- **`test_generate_names_with_styles_uses_adapter`**：确认 `GeminiLLMAdapter` 被调用且自动清理非法字符。
- **`test_analyze_tasks_respects_batches`**：验证帧批次与 API 调用次数一致，且每批最多 5 帧。
- **`test_generate_names_json_fallback`**：确保 JSON 嵌套文本可以正确解析。

> 若其中任意用例失败，请回顾最近的管线改动，优先检查 `pipeline.py` 与 `llm/adapter.py`。

---

## 🔍 手工冒烟测试

### 1. 单视频 dry-run
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\sample.mp4"
```
> 观察日志是否出现：  
`总计将使用 X 帧（覆盖率 X/Y）` 与 `汇总 N 次调用 → [...] (置信度: xx)`。

### 2. 风格命名回归
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "X:\Videos\sample.mp4" --use-styles --n 3
```
检查要点：
- 候选表格包含 `风格 / 名称 / 语言` 列。
- 选择序号后生成 `logs/rename_audit.jsonl` 记录（dry-run 标记为 `true`）。

### 3. ffmpeg/ffprobe 缓存验证
1. 首次运行 dry-run，确认日志输出 `执行命令: ffmpeg ...`。
2. 第二次运行同一命令，确保未再次报错或提示缺少可执行文件（路径已缓存）。

---

## 📈 验收指标

| 指标 | 验收标准 | 观察方式 |
|------|----------|----------|
| 单元测试 | `pytest -q` 全绿 | 终端输出 |
| 帧利用率 | 小样本 ≥ 分配帧数；常规场景 ≥70% | Pipeline 日志 |
| 每批帧数 | ≤5 帧 | Pipeline 日志 |
| LLM 响应解析 | 无 `[ERROR] ... JSON 解析失败` | 终端日志 |
| 审计记录 | dry-run 标记 true，包含 tags 和 has_transcript 字段 | `logs/rename_audit.jsonl` |

---

## 🐛 常见问题与排查

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| ffmpeg 未找到 | 日志提示 `未找到 ffmpeg 命令` | 确认 PATH，安装后重启终端（路径缓存需刷新） |
| 帧覆盖率过低 | 覆盖率 <50% | 检查视频帧数是否过少，必要时调整 `min_batch`/`max_batch` |
| JSON 解析失败 | `parse_json_loose` 返回 `None` | 检查模型返回是否包含合法 JSON，必要时重试或记录完整响应 |
| pytest 失败 | `AttributeError: generate` 等 | 确认 `GeminiLLMAdapter` 未被绕开，检查依赖注入逻辑 |

---

## 📝 测试记录模板

| 测试项 | 结果 | 备注 |
|--------|------|------|
| pytest -q | ☐ 通过 ☐ 失败 | |
| dry-run 日志 | ☐ 正常 ☐ 异常 | |
| 风格候选表格 | ☐ 正常 ☐ 异常 | |
| 审计记录 | ☐ 正常 ☐ 异常 | |
| 其他问题 | ☐ 有 ☐ 无 | |

---

若发现新的问题或调优点，请在 `docs/decisions.md` 与 `docs/NEXT_STEPS.md` 中同步记录，确保团队共享最新上下文。
