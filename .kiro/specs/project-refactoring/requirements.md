# 需求文档

## 简介

重构 VideoRenamer 项目，解决当前代码臃肿混乱、缺少自动化测试、使用不便的问题。重构后的系统应保持 Python 环境隔离，具有清晰的模块结构，完善的测试覆盖，并提供更友好的用户体验。

## 术语表

- **VideoRenamer 系统**：基于 Gemini 多模态 AI 的成人视频自动重命名工具
- **虚拟环境**：Python venv 隔离的依赖环境
- **GPT-Load**：本地 Gemini API 代理服务，提供 key 轮询功能
- **命名风格**：不同的文件命名策略（中文描述、场景角色、P站风格等）
- **CLI**：命令行界面
- **单视频处理**：一次处理一个视频文件的工作流
- **批量处理**：并发处理多个视频文件的工作流

## 需求

### 需求 1：清晰的项目结构

**用户故事**：作为开发者，我希望项目具有清晰的模块划分和依赖关系，以便快速理解代码结构并进行维护。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 采用分层架构，包含核心层、服务层、接口层三个清晰的层次
2. THE VideoRenamer 系统 SHALL 将配置管理、日志记录、错误处理等横切关注点独立为单独模块
3. THE VideoRenamer 系统 SHALL 在每个模块中提供清晰的 `__init__.py` 导出接口
4. THE VideoRenamer 系统 SHALL 使用依赖注入模式，避免模块间的硬编码依赖
5. THE VideoRenamer 系统 SHALL 提供项目结构文档，说明各模块的职责和依赖关系

### 需求 2：完善的自动化测试

**用户故事**：作为开发者，我希望项目具有完善的自动化测试，以便在修改代码时快速验证功能正确性，避免引入回归问题。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 为核心业务逻辑提供单元测试，测试覆盖率达到 80% 以上
2. THE VideoRenamer 系统 SHALL 为关键工作流提供集成测试，验证模块间协作
3. THE VideoRenamer 系统 SHALL 使用 pytest 作为测试框架，支持参数化测试和 fixture
4. THE VideoRenamer 系统 SHALL 提供测试数据和 mock 工具，避免依赖外部服务（如 Gemini API）
5. THE VideoRenamer 系统 SHALL 支持通过 `pytest` 命令一键运行所有测试
6. THE VideoRenamer 系统 SHALL 在 CI/CD 流程中自动运行测试（可选）

### 需求 3：改进的依赖管理

**用户故事**：作为用户，我希望能够轻松安装和管理项目依赖，确保环境隔离和版本一致性。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 使用 `pyproject.toml` 统一管理项目元数据和依赖
2. THE VideoRenamer 系统 SHALL 在 `pyproject.toml` 中明确区分核心依赖、开发依赖和可选依赖
3. THE VideoRenamer 系统 SHALL 提供 `requirements.txt` 用于快速安装（通过 pip-tools 生成）
4. THE VideoRenamer 系统 SHALL 支持通过 `pip install -e .` 以可编辑模式安装
5. THE VideoRenamer 系统 SHALL 在文档中提供清晰的虚拟环境创建和依赖安装指南

### 需求 4：统一的配置管理

**用户故事**：作为用户，我希望能够通过统一的配置文件管理所有系统参数，避免在代码中硬编码配置。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 使用 pydantic-settings 管理配置，支持从环境变量和 `.env` 文件加载
2. THE VideoRenamer 系统 SHALL 提供配置验证，确保必需参数存在且格式正确
3. THE VideoRenamer 系统 SHALL 将配置分组为 API 配置、并发配置、路径配置等类别
4. THE VideoRenamer 系统 SHALL 提供 `.env.example` 模板，包含所有可配置参数的说明
5. THE VideoRenamer 系统 SHALL 支持通过 CLI 参数覆盖配置文件中的设置

### 需求 5：改进的错误处理和日志

**用户故事**：作为用户，我希望在出现错误时能够获得清晰的错误信息和日志，以便快速定位和解决问题。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 定义自定义异常类型，区分不同类型的错误（API 错误、文件错误、配置错误等）
2. THE VideoRenamer 系统 SHALL 使用结构化日志，记录关键操作和错误信息
3. THE VideoRenamer 系统 SHALL 支持配置日志级别（DEBUG、INFO、WARNING、ERROR）
4. THE VideoRenamer 系统 SHALL 在 CLI 中提供友好的错误提示，避免直接暴露技术栈信息
5. THE VideoRenamer 系统 SHALL 将详细日志保存到文件，便于事后分析

### 需求 6：改进的 CLI 用户体验

**用户故事**：作为用户，我希望 CLI 工具易于使用，提供清晰的命令结构和帮助信息。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 使用 typer 构建 CLI，提供子命令结构（run、scan、batch 等）
2. THE VideoRenamer 系统 SHALL 为每个命令提供 `--help` 选项，显示参数说明和使用示例
3. THE VideoRenamer 系统 SHALL 使用 rich 库提供彩色输出、进度条和表格展示
4. THE VideoRenamer 系统 SHALL 支持 `--dry-run` 模式，预览操作而不实际执行
5. THE VideoRenamer 系统 SHALL 在交互式操作中提供清晰的提示和确认步骤

### 需求 7：模块化的核心功能

**用户故事**：作为开发者，我希望核心功能（视频处理、AI 分析、命名生成）被封装为独立模块，便于测试和复用。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 将视频帧抽取功能封装为独立的 VideoProcessor 模块
2. THE VideoRenamer 系统 SHALL 将 Gemini API 调用封装为独立的 LLMClient 模块
3. THE VideoRenamer 系统 SHALL 将命名生成逻辑封装为独立的 NamingGenerator 模块
4. THE VideoRenamer 系统 SHALL 将文件扫描和过滤封装为独立的 VideoScanner 模块
5. THE VideoRenamer 系统 SHALL 确保每个模块具有清晰的接口和最小的外部依赖

### 需求 8：改进的开发工具链

**用户故事**：作为开发者，我希望项目配置代码格式化、类型检查等开发工具，提高代码质量。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 使用 black 进行代码格式化，配置行长度为 100
2. THE VideoRenamer 系统 SHALL 使用 isort 管理导入顺序，与 black 兼容
3. THE VideoRenamer 系统 SHALL 使用 mypy 进行类型检查，启用严格模式
4. THE VideoRenamer 系统 SHALL 使用 ruff 进行代码检查，替代 flake8 和 pylint
5. THE VideoRenamer 系统 SHALL 在 `pyproject.toml` 中统一配置所有工具
6. THE VideoRenamer 系统 SHALL 提供 pre-commit 配置，自动运行格式化和检查（可选）

### 需求 9：简化的安装和使用流程

**用户故事**：作为新用户，我希望能够通过简单的步骤完成安装和首次使用，快速体验系统功能。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 提供一键安装脚本（setup.ps1 或 setup.sh）
2. THE VideoRenamer 系统 SHALL 在安装脚本中自动创建虚拟环境、安装依赖、复制配置模板
3. THE VideoRenamer 系统 SHALL 提供快速开始文档，包含 3-5 个步骤即可运行第一个示例
4. THE VideoRenamer 系统 SHALL 在首次运行时检查配置完整性，提示缺失的必需参数
5. THE VideoRenamer 系统 SHALL 提供示例视频或测试数据，便于用户验证安装

### 需求 10：向后兼容和迁移支持

**用户故事**：作为现有用户，我希望重构后的系统能够兼容现有的配置和数据，或提供迁移工具。

#### 验收标准

1. THE VideoRenamer 系统 SHALL 保持 `.env` 配置文件的兼容性，或提供迁移指南
2. THE VideoRenamer 系统 SHALL 保持命名风格配置文件（naming_styles.yaml）的兼容性
3. THE VideoRenamer 系统 SHALL 保持审计日志格式的兼容性，或提供转换工具
4. THE VideoRenamer 系统 SHALL 在文档中说明重构前后的主要变化
5. THE VideoRenamer 系统 SHALL 提供从旧版本迁移到新版本的步骤指南
