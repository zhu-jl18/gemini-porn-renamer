# 实施任务列表

## 任务概述

本任务列表将 VideoRenamer 项目重构分解为可执行的代码任务。每个任务都是独立的、可测试的，并引用相关需求。

## 任务列表

- [x] 1. 项目清理和准备





- [ ] 1.1 清理测试垃圾文件和缓存
  - 删除 `test_fixes.py`、`.pytest_cache/`、所有 `__pycache__/` 目录
  - 删除 `.pyc` 文件


  - _需求: 1.1, 9.1_

- [ ] 1.2 清理和整理文档
  - 删除 `docs/bugfix-plan-20250124.md`、`docs/progress-tracker.md`


  - 评估并清理 `意见/` 目录
  - 评估并清理 `.serena/` 和 `.crush/` 目录





  - _需求: 1.1, 9.1_

- [ ] 1.3 创建新的目录结构
  - 创建 `src/vrenamer/core/`、`src/vrenamer/services/`、`src/vrenamer/utils/` 目录
  - 创建 `config/prompts/analysis/`、`config/prompts/naming/` 目录


  - 创建 `scripts/debug/`、`docs/modules/` 目录
  - _需求: 1.1, 1.3_

- [x] 2. 核心层实现


- [ ] 2.1 实现配置管理系统
  - 创建 `src/vrenamer/core/config.py`
  - 实现 `LLMBackendConfig`、`ModelConfig`、`ConcurrencyConfig`、`AnalysisConfig`、`NamingConfig`、`AppConfig` 类


  - 支持从 `.env` 和 YAML 文件加载配置





  - 实现配置验证（如 API key 检查）
  - _需求: 4.1, 4.2, 4.3, 4.4_



- [ ] 2.2 实现日志系统
  - 创建 `src/vrenamer/core/logging.py`
  - 实现 `AppLogger` 类，支持控制台和文件输出
  - 支持结构化日志和日志级别配置
  - _需求: 5.2, 5.3, 5.5_



- [ ] 2.3 定义异常类型
  - 创建 `src/vrenamer/core/exceptions.py`
  - 定义 `VRenamerError`、`ConfigError`、`APIError`、`VideoProcessingError`、`FileOperationError` 等异常类


  - _需求: 5.1_

- [x] 2.4 定义共享类型


  - 创建 `src/vrenamer/core/types.py`
  - 定义 `VideoInfo`、`AnalysisResult`、`NameCandidate`、`RenameOperation` 等数据类
  - _需求: 7.5_








- [ ] 3. LLM 客户端层实现
- [ ] 3.1 实现 LLM 客户端抽象基类
  - 创建 `src/vrenamer/llm/base.py`
  - 定义 `BaseLLMClient` 抽象类，包含 `classify()` 和 `generate()` 方法
  - _需求: 7.2, 7.3_

- [x] 3.2 实现 Gemini 客户端


  - 创建 `src/vrenamer/llm/gemini.py`
  - 实现 `GeminiClient` 类，支持 `openai_compat` 和 `gemini_native` 两种传输格式
  - 实现 `classify()` 和 `generate()` 方法
  - 处理响应解析和错误处理
  - _需求: 7.2, 7.3_

- [ ] 3.3 实现 OpenAI 客户端
  - 创建 `src/vrenamer/llm/openai.py`
  - 实现 `OpenAIClient` 类
  - 实现 `classify()` 和 `generate()` 方法
  - _需求: 7.2, 7.3_



- [ ] 3.4 实现客户端工厂
  - 创建 `src/vrenamer/llm/factory.py`
  - 实现 `LLMClientFactory.create()` 方法，根据配置创建对应的客户端
  - _需求: 7.2, 7.4_



- [ ] 3.5 实现 JSON 解析工具
  - 保留并优化 `src/vrenamer/llm/json_utils.py`
  - 实现宽松的 JSON 解析逻辑，支持多种格式




  - _需求: 7.3_

- [x] 3.6 实现提示词加载器


  - 创建 `src/vrenamer/llm/prompts.py`
  - 实现从 YAML 配置文件加载提示词的功能





  - _需求: 4.4, 7.3_

- [x] 4. 服务层实现


- [ ] 4.1 实现视频处理服务
  - 创建 `src/vrenamer/services/video.py`
  - 实现 `VideoProcessor` 类


  - 实现 `sample_frames()` 方法（抽帧、去重、限制）
  - 实现 `get_duration()` 方法
  - 实现 `extract_audio()` 方法（可选）
  - 检查 ffmpeg 和 ffprobe 依赖
  - _需求: 7.1, 7.5_



- [ ] 4.2 实现分析服务（两层并发）
  - 创建 `src/vrenamer/services/analysis.py`
  - 实现 `AnalysisService` 类


  - 实现 `analyze_video()` 方法（主入口）



  - 实现 `_execute_tasks_concurrent()` 方法（第一层并发：子任务并发）
  - 实现 `_execute_single_task()` 方法（第二层并发：批次并发）
  - 实现 `_execute_batches_concurrent()` 方法
  - 实现 `_aggregate_batch_results()` 方法（汇总批次结果）
  - 实现 `_aggregate_task_results()` 方法（汇总子任务结果）


  - 实现 `_load_tasks_config()` 方法（从 YAML 加载任务配置）
  - 实现 `_load_prompt()` 方法（从 YAML 加载提示词）
  - _需求: 7.1, 7.5_

- [ ] 4.3 实现命名生成服务
  - 创建 `src/vrenamer/services/naming.py`


  - 实现 `NamingService` 类
  - 实现 `generate_candidates()` 方法
  - 集成 `NamingGenerator` 和 `NamingStyleConfig`
  - _需求: 7.1, 7.5_

- [ ] 4.4 实现文件扫描服务
  - 创建 `src/vrenamer/services/scanner.py`
  - 实现 `ScannerService` 类
  - 实现 `scan_directory()` 方法
  - 实现 `is_video_file()` 和 `is_garbled_filename()` 方法
  - 实现 `get_scan_summary()` 方法
  - _需求: 7.1, 7.5_

- [ ] 5. 命名风格系统优化
- [ ] 5.1 优化命名风格配置加载
  - 保留并优化 `src/vrenamer/naming/styles.py`
  - 确保 `NamingStyleConfig.from_yaml()` 正确加载配置
  - _需求: 7.3_

- [ ] 5.2 优化命名生成器
  - 保留并优化 `src/vrenamer/naming/generator.py`
  - 确保 `NamingGenerator` 使用新的 LLM 客户端抽象
  - _需求: 7.3_

- [ ] 6. 配置文件创建
- [ ] 6.1 创建 LLM 后端配置文件
  - 创建 `config/llm_backends.yaml`
  - 定义 Gemini 和 OpenAI 后端配置
  - _需求: 4.4_





- [ ] 6.2 创建分析任务配置文件
  - 创建 `config/analysis_tasks.yaml`
  - 定义角色原型、脸部可见性、场景类型、姿势标签等子任务


  - _需求: 4.4_

- [ ] 6.3 创建分析提示词配置文件
  - 创建 `config/prompts/analysis/role_archetype.yaml`


  - 创建 `config/prompts/analysis/face_visibility.yaml`
  - 创建 `config/prompts/analysis/scene_type.yaml`
  - 创建 `config/prompts/analysis/positions.yaml`


  - 每个文件包含 `system_prompt`、`user_prompt_template`、`response_format`、`temperature`、`max_tokens`
  - _需求: 4.4_



- [ ] 6.4 创建命名提示词配置文件
  - 创建 `config/prompts/naming/system.yaml`



  - 定义命名生成的系统提示词
  - _需求: 4.4_

- [ ] 6.5 更新 .env.example 模板
  - 更新 `.env.example`，包含所有新的配置参数
  - 添加详细的参数说明
  - _需求: 4.4, 9.3_

- [ ] 7. CLI 接口重构
- [ ] 7.1 创建 CLI 主应用
  - 创建 `src/vrenamer/cli/app.py`
  - 使用 typer 创建主应用
  - 注册子命令
  - _需求: 6.1, 6.2_

- [ ] 7.2 实现 run 命令（单视频处理）
  - 创建 `src/vrenamer/cli/commands/run.py`
  - 实现单视频处理流程
  - 集成视频处理、分析、命名服务
  - 使用 Rich 显示进度和结果
  - 支持 `--dry-run`、`--styles` 等参数
  - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 7.3 实现 scan 命令（目录扫描）
  - 创建 `src/vrenamer/cli/commands/scan.py`
  - 实现目录扫描和预览功能
  - 显示扫描摘要
  - _需求: 6.1, 6.2, 6.5_

- [ ] 7.4 实现 batch 命令（批量处理）
  - 创建 `src/vrenamer/cli/commands/batch.py`
  - 实现批量处理（循环调用单视频处理）
  - 显示批量进度
  - _需求: 6.1, 6.2, 6.5_

- [ ] 7.5 实现 rollback 命令（回滚操作）
  - 创建 `src/vrenamer/cli/commands/rollback.py`
  - 实现从审计日志回滚重命名操作
  - _需求: 6.1, 6.2_

- [ ] 7.6 创建 Rich UI 组件
  - 创建 `src/vrenamer/cli/ui.py`
  - 实现进度条、表格、面板等 UI 组件
  - _需求: 6.3_

- [ ] 8. 工具函数实现
- [ ] 8.1 实现文件操作工具
  - 创建 `src/vrenamer/utils/file.py`
  - 实现文件名清理、路径验证等工具函数
  - _需求: 7.5_

- [ ] 8.2 实现文本处理工具
  - 创建 `src/vrenamer/utils/text.py`
  - 实现文本清理、编码检测等工具函数
  - _需求: 7.5_

- [ ] 9. 调试脚本实现
- [ ] 9.1 创建视频处理调试脚本
  - 创建 `scripts/debug/debug_video.py`
  - 实现视频抽帧、时长获取等功能的独立测试




  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 9.2 创建分析模块调试脚本
  - 创建 `scripts/debug/debug_analysis.py`
  - 实现两层并发策略的独立测试
  - 支持 mock 模式
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 9.3 创建命名模块调试脚本
  - 创建 `scripts/debug/debug_naming.py`
  - 实现命名生成的独立测试
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 9.4 创建 LLM 客户端调试脚本
  - 创建 `scripts/debug/debug_llm.py`
  - 实现不同 LLM 后端的独立测试
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 9.5 创建调试脚本文档
  - 创建 `scripts/debug/README.md`
  - 编写调试脚本使用指南
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 10. 测试实现
- [ ] 10.1 创建 pytest 配置和 fixtures
  - 创建 `tests/conftest.py`
  - 实现 mock 配置、mock LLM 客户端、示例视频等 fixtures
  - _需求: 2.1, 2.2, 2.3, 2.4_

- [ ] 10.2 实现核心层单元测试
  - 创建 `tests/unit/test_config.py`（配置管理测试）
  - 创建 `tests/unit/test_logging.py`（日志系统测试）
  - 创建 `tests/unit/test_exceptions.py`（异常类型测试）
  - _需求: 2.1, 2.2, 2.3_

- [ ] 10.3 实现 LLM 客户端单元测试
  - 创建 `tests/unit/test_llm_client.py`
  - 测试 Gemini 和 OpenAI 客户端
  - 使用 mock 避免真实 API 调用
  - _需求: 2.1, 2.2, 2.3_

- [ ] 10.4 实现服务层单元测试
  - 创建 `tests/unit/test_video.py`（视频处理测试）
  - 创建 `tests/unit/test_analysis.py`（分析服务测试）
  - 创建 `tests/unit/test_naming.py`（命名服务测试）
  - 创建 `tests/unit/test_scanner.py`（扫描服务测试）
  - _需求: 2.1, 2.2, 2.3_

- [ ] 10.5 实现集成测试
  - 创建 `tests/integration/test_video_pipeline.py`（完整视频处理流程测试）
  - 创建 `tests/integration/test_cli.py`（CLI 命令测试）
  - _需求: 2.2_

- [ ] 11. 文档更新
- [ ] 11.1 更新 README.md
  - 更新项目概述、快速开始、架构图
  - 添加新的 CLI 命令说明
  - _需求: 9.3, 9.4_

- [ ] 11.2 创建架构文档
  - 创建 `docs/architecture.md`
  - 描述分层架构、模块职责、数据流
  - _需求: 1.5, 9.4_

- [ ] 11.3 创建模块文档
  - 创建 `docs/modules/video.md`（视频处理模块）
  - 创建 `docs/modules/analysis.md`（分析模块，含并发策略详解）
  - 创建 `docs/modules/naming.md`（命名模块）
  - 创建 `docs/modules/llm.md`（LLM 客户端）
  - _需求: 1.5, 9.4_

- [ ] 11.4 创建调试指南
  - 创建 `docs/debugging.md`
  - 描述如何使用调试脚本、如何定位问题
  - _需求: 9.4_

- [ ] 11.5 更新测试指南
  - 更新 `docs/testing-guide.md`
  - 添加新的测试结构和运行方法
  - _需求: 2.6, 9.4_

- [ ] 11.6 整合并发策略文档
  - 将 `docs/concurrent-strategy-explained.md` 的内容整合到 `docs/modules/analysis.md`
  - 删除原文件
  - _需求: 1.5_

- [ ] 12. 依赖管理和打包
- [ ] 12.1 更新 pyproject.toml
  - 更新项目元数据、依赖列表
  - 配置开发工具（black、isort、mypy、ruff）
  - 配置 pytest
  - _需求: 3.1, 3.2, 3.3, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 12.2 生成 requirements.txt
  - 使用 pip-tools 生成 `requirements.txt`
  - _需求: 3.3_

- [ ] 12.3 创建安装脚本
  - 创建 `scripts/setup.ps1`（Windows）
  - 创建 `scripts/setup.sh`（Linux/macOS）
  - 自动创建虚拟环境、安装依赖、复制配置模板
  - _需求: 9.1, 9.2, 9.3_

- [ ] 13. 迁移和兼容性
- [ ] 13.1 创建配置迁移脚本
  - 创建 `scripts/migrate_config.py`
  - 自动转换旧版 `.env` 格式到新版
  - _需求: 10.1_

- [ ] 13.2 验证向后兼容性
  - 测试旧的 CLI 命令是否仍然工作
  - 测试旧的配置文件是否兼容
  - _需求: 10.1, 10.2, 10.3, 10.4_

- [ ] 14. 最终验证和清理
- [ ] 14.1 运行完整测试套件
  - 运行 `pytest` 确保所有测试通过
  - 检查测试覆盖率（目标 80%+）
  - _需求: 2.1, 2.5_

- [ ] 14.2 运行代码检查
  - 运行 `black`、`isort`、`mypy`、`ruff`
  - 修复所有警告和错误
  - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 14.3 端到端测试
  - 使用真实视频测试完整流程
  - 验证所有 CLI 命令
  - 验证调试脚本
  - _需求: 9.3, 9.4_

- [ ] 14.4 更新文档索引
  - 更新 `docs/README.md`
  - 确保所有文档链接正确
  - _需求: 9.4_

- [ ] 14.5 最终清理
  - 删除所有临时文件和未使用的代码
  - 确保 `.gitignore` 正确配置
  - _需求: 1.1_
