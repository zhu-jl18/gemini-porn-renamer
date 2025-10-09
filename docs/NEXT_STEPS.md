# 开发路线图

## 当前状态（2025-01-10 更新）

### ✅ 已完成
- 虚拟环境配置和依赖管理
- GPT-Load OpenAI 兼容端点连接测试（多模态正常）
- CLI 单视频流程框架：抽帧 → 转录(占位) → Flash 标签 → Pro 命名 → 终端交互
- LLM 客户端响应解析（OpenAI compat + Gemini native）
- 基础审计和回滚命令框架
- **命名风格系统**：6 种内置风格，YAML 配置，支持自定义
- **命名候选生成器**：多风格并行生成，智能解析响应
- **CLI 风格参数**：`--use-styles` 和 `--styles` 支持
- **单元测试**：命名风格系统测试全部通过

### 🚧 进行中
- 集成测试和文档更新

### ❌ 未实现
- 目录扫描器（乱码识别、递归扫描）
- 高并发工作流（asyncio 任务池 + GPT-Load 键轮询）
- 音频转录（faster-whisper 集成）
- 迭代优化机制（样本管理、prompt 调优）
- WebUI 真实 LLM 集成

## 开发优先级（按需求对齐）

### P0 - 核心功能（必须）

#### 1. 单视频流程完善
- [ ] 修复 GeminiClient 文本响应解压缩问题
- [ ] 接入真实 GPT-Load 测试完整流程
- [ ] 完善进度展示（Rich 进度条优化）
- [ ] 补全 `extract_transcript`（faster-whisper）
- [ ] 错误处理和重试逻辑（指数退避）
- [ ] 真实改名测试（`--rename` 模式）+ 回滚验证

#### 2. 目录扫描器
- [ ] 设计 `Scanner` 类：递归扫描、文件过滤
- [ ] 乱码文件名识别（chardet 检测编码）
- [ ] 已处理文件跟踪（避免重复处理）
- [ ] 扫描结果预览和确认
- [ ] CLI 命令：`scan` 子命令

#### 3. 高并发工作流
- [ ] 设计 `WorkflowManager`：asyncio 任务池
- [ ] Semaphore 并发限流（可配置：默认 32）
- [ ] GPT-Load 键轮询对接（利用其内置负载均衡）
- [ ] 批量进度跟踪（Rich Live Display）
- [ ] 断点续传（保存处理状态到 JSON）
- [ ] CLI 命令：`batch` 子命令

### P1 - 质量提升（重要）

#### 4. 迭代优化机制
- [ ] 设计命名样例格式（YAML）：`examples/naming_samples.yaml`
- [ ] 误命名反馈收集：`feedback` 子命令
- [ ] Few-shot 样例自动注入 prompt
- [ ] A/B 测试框架（对比不同 prompt）
- [ ] `iterate` 命令：基于反馈调优

#### 5. 错误处理和日志
- [ ] 结构化日志（JSON Lines）
- [ ] 分类错误：网络、API、解析、文件系统
- [ ] 失败任务自动重试队列
- [ ] 错误统计和报告

### P2 - 体验优化（可选）

#### 6. WebUI 集成
- [ ] 接入真实 LLM 管线
- [ ] 帧缩略图展示
- [ ] 字幕预览
- [ ] 批量任务管理界面

#### 7. 命名规则增强
- [ ] 自定义命名模板（Jinja2）
- [ ] 非法字符智能替换
- [ ] 去重策略（hash 后缀）
- [ ] 命名规范验证

## 技术选型

### 并发模型
- **asyncio** + `asyncio.Semaphore`：控制并发数
- GPT-Load 自带键轮询，客户端无需手动管理

### 扫描策略
- 递归遍历：`pathlib.Path.rglob("*.mp4")`
- 乱码检测：`chardet` 库
- 过滤规则：扩展名白名单、文件大小阈值

### 状态持久化
- 审计日志：`logs/rename_audit.jsonl`（JSON Lines）
- 批处理状态：`logs/batch_state.json`（断点续传）
- 反馈样本：`data/feedback/*.yaml`

### 错误恢复
- 指数退避重试：`backoff` 库
- 失败任务队列：`logs/failed_tasks.jsonl`
- 幂等性保证：所有操作可重入

## 配置提醒
- `.env`：敏感配置，**绝对不得提交**
- `logs/` 目录：本地日志，已加入 `.gitignore`
- `test_gptload.py`：临时测试文件，开发完成后可删除

## 安全注意
- 如果远程仓库有旧密钥历史，使用 `git filter-repo` 清理
- 定期轮换 GPT-Load API Key
- 生产环境使用独立配置文件

