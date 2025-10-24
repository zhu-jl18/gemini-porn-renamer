# 测试验证指南

**修复版本**: 2025-01-24
**测试目标**: 验证三大问题修复效果

---

## 🎯 测试前准备

### 1. 安装新依赖

```powershell
# 确保虚拟环境已激活
.\.venv\Scripts\Activate.ps1

# 安装新依赖
pip install imagehash==4.3.1 pillow==10.4.0

# 或者重装全部依赖
pip install -r requirements.txt
```

### 2. 验证依赖安装

```powershell
python -c "import imagehash; from PIL import Image; print('✓ 依赖已安装')"
```

---

## 📋 测试清单

### 测试 1: LLM 空回复问题 🐛

**目标**: 验证图片分析接口返回正常

**步骤**:
```powershell
# 运行单视频分析
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "测试视频.mp4" --n 5
```

**预期结果**:
```
[DEBUG] classify_json - HTTP Status: 200
[DEBUG] classify_json - Response Headers: {...}
[DEBUG] classify_json - Raw Bytes Length: XXXX
[DEBUG] classify_json - JSON Keys: ['choices', 'usage', ...]
[DEBUG] classify_json - Choices count: 1
[DEBUG] classify_json - Message keys: ['role', 'content']
[DEBUG] classify_json - Content length: XXX
[DEBUG] classify_json - Content preview: {"labels": [...], ...}
```

**验收标准**:
- [ ] 能看到完整的 HTTP 响应日志
- [ ] `Content length` > 0（不是空回复）
- [ ] `Content preview` 包含 JSON 数据
- [ ] 无 `[ERROR] 空 choices 数组` 错误

**故障排查**:
如果仍然空回复，检查日志中的：
1. HTTP Status 是否为 200
2. Response Headers 是否正常
3. 完整响应内容（会打印在 ERROR 日志中）

---

### 测试 2: 并发数提升 ⚡

**目标**: 验证并发数达到 32+

**步骤**:
```powershell
# 运行单视频分析，观察并发信息
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "测试视频.mp4"
```

**预期结果**:
```
━━━ 步骤 3/4: AI 多模态分析 ━━━
  → 使用模型: gemini-flash-latest
  → 并发数: 64  <--- 应该显示 64
  → 分析任务数: 4
```

**验收标准**:
- [ ] 显示 `并发数: 64`（而非 8）
- [ ] 多个任务同时处理（观察进度条）
- [ ] 无并发相关错误

---

### 测试 3: 帧利用率提升 📈

**目标**: 验证利用率达到 70%+

**步骤**:
```powershell
# 运行单视频分析（长视频更明显）
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "长视频.mp4"
```

**预期结果**:
```
步骤 1/4: 视频抽帧
  ✓ 抽取帧数: 96 帧
  → 原始帧数: 96
  → 去重后: 85 帧  <--- 去重生效
  → 最终采样: 85 帧

步骤 3/4: AI 多模态分析
  [INFO] ========== 帧分配策略 ==========
  [INFO] 总帧数: 85, 任务数: 4
  [INFO] 目标范围: 每任务 15-20 帧
  [INFO] 时间轴覆盖: 保留首帧 [...] 和尾帧 [...]
  [INFO] 随机打乱: 83 个中间帧
  [INFO] 每任务目标: 20 帧
  [INFO]   ✓ role_archetype: 20 帧
  [INFO]   ✓ face_visibility: 20 帧
  [INFO]   ✓ scene_type: 20 帧
  [INFO]   ✓ positions: 20 帧

  [INFO] ========== 利用率统计 ==========
  [INFO] 总帧数: 85
  [INFO] 已使用: 80
  [INFO] 利用率: 94.1%  <--- 目标达成！
  [SUCCESS] 利用率达标！
  [INFO] ===================================
```

**验收标准**:
- [ ] 去重生效（原始帧数 > 去重后帧数）
- [ ] 每任务使用 15-20 帧（而非 3-8 帧）
- [ ] **利用率 ≥ 70%** ✨
- [ ] 显示 `[SUCCESS] 利用率达标！`

**性能对比**:

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 每任务帧数 | 3-8 帧 | 15-20 帧 | **2.5 倍** |
| 利用率 | 33% | 70-94% | **2.1-2.8 倍** |
| 去重方式 | 仅 MD5 | MD5 + pHash | 质量提升 |

---

## 🧪 高级测试

### 测试 4: 去重算法效果

**目标**: 验证 pHash 相似度去重

**步骤**:
```powershell
# 准备包含相似帧的视频（如静态场景较多的视频）
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "静态场景视频.mp4"
```

**预期结果**:
```
步骤 1/4: 视频抽帧
  [INFO] 去重算法: MD5 + pHash (汉明距离阈值 ≤ 5)
  [INFO] 去重结果: 原始 96 帧 → 保留 72 帧 (移除 24 帧)
```

**验收标准**:
- [ ] 显示 `MD5 + pHash` 去重
- [ ] 移除了相似帧（移除数 > 0）
- [ ] 保留的帧有足够多样性

---

### 测试 5: 随机性验证

**目标**: 验证帧分配的随机性

**步骤**:
```powershell
# 运行同一视频 3 次，观察帧分配是否不同
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "测试.mp4"
# 再运行 2 次...
```

**预期结果**:
- 每次运行的帧分配顺序不同（随机打乱生效）
- 首尾帧始终被使用（时间轴覆盖）

---

## 📊 性能测试

### 测试 6: 并发压力测试

**目标**: 验证高并发稳定性

**步骤**:
1. 确保 `.env` 配置：
   ```env
   MAX_CONCURRENCY=64
   ```

2. 运行多个视频测试：
   ```powershell
   # 测试 1 个视频
   .\.venv\Scripts\python.exe -m vrenamer.cli.main run "video1.mp4"
   ```

**监控指标**:
- API 调用成功率
- 内存使用（应 < 4GB）
- 错误日志（无超时或限流错误）

---

## ✅ 完整验收报告

测试完成后，填写此表：

| 测试项 | 结果 | 实际值 | 备注 |
|--------|------|--------|------|
| LLM 返回正常 | ☐ 通过 ☐ 失败 | Content length: ___ | |
| 并发数达标 | ☐ 通过 ☐ 失败 | 并发数: ___ | |
| 帧利用率 | ☐ 通过 ☐ 失败 | 利用率: ___% | |
| 去重算法 | ☐ 通过 ☐ 失败 | 移除: ___ 帧 | |
| 随机性 | ☐ 通过 ☐ 失败 | - | |
| 命名质量 | ☐ 提升 ☐ 不变 ☐ 下降 | - | 对比优化前 |

---

## 🐛 常见问题

### Q1: imagehash 安装失败
```powershell
# 解决方案：先安装 pillow
pip install pillow
pip install imagehash
```

### Q2: 利用率仍然低于 70%
**可能原因**:
- 视频帧数太少（< 60 帧）
- 任务数太多

**解决方案**:
修改 `pipeline.py:498-499`，增加 `max_batch`:
```python
min_batch: int = 15
max_batch: int = 25  # 提升到 25
```

### Q3: LLM 仍然空回复
**排查步骤**:
1. 检查 `.env` 中的 API Key 是否正确
2. 查看完整错误日志（会打印在 `[ERROR]` 中）
3. 尝试切换接口模式：
   ```env
   LLM_TRANSPORT=gemini_native  # 或 openai_compat
   ```

---

## 📝 反馈

测试完成后，请记录：

1. **成功的优化点**:
   -
   -

2. **仍存在的问题**:
   -
   -

3. **建议后续优化**:
   -
   -

---

**文档版本**: v1.0
**最后更新**: 2025-01-24
**状态**: 待测试
