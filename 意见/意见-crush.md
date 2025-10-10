# VideoRenamer 命名准确性改进意见

## 一、核心问题诊断

### 1.1 当前 Workflow 架构分析

```
视频输入 → 抽帧(96帧) → 分类任务(4个) → 标签聚合 → 命名生成 → 候选输出
         ↓              ↓                ↓           ↓
      去重/采样    帧批次分配(3-8帧)   tags字典   风格模板
```

**关键瓶颈**：
- **信息损失链**：96帧 → 分批3-8帧 → 4个独立分类 → 扁平标签 → 命名生成
- **上下文割裂**：分类任务各自独立，命名生成时只能看到标签列表，无法回溯原始视觉证据
- **提示词冲突**：`base.system.md` 要求"仅输出JSON"，但 `naming_styles.yaml` 的风格模板是自然语言描述

### 1.2 命名质量影响因素

| 因素 | 当前状态 | 影响程度 |
|------|---------|---------|
| **视觉理解深度** | 分类任务仅输出标签，丢失细节 | ⚠️ 高 |
| **时序连贯性** | 帧批次轮转分配，无时序建模 | ⚠️ 中 |
| **语义一致性** | 标签→命名两阶段，风格模板与标签脱节 | ⚠️ 高 |
| **Few-shot 质量** | `naming_samples.yaml` 仅3个样例，格式与风格不匹配 | ⚠️ 高 |
| **反馈闭环** | `store_feedback` 仅记录，未用于优化 | ⚠️ 中 |

---

## 二、改进方案（按优先级）

### 🔴 P0 - 立即实施（投入产出比最高）

#### 2.1 增强分类任务的输出结构

**问题**：当前分类任务仅返回标签列表，命名生成时缺乏细节依据。

**方案**：扩展分类任务输出，增加 `description` 字段

```python
# 修改 prompts/modules/*.md
输出规范：
{
  "labels": ["标签1", "标签2"],
  "confidence": 0.85,
  "rationale": "20字依据",
  "description": "50-80字详细描述，包含关键视觉细节、动作、场景氛围"  # 新增
}
```

**收益**：
- 命名生成时可获取丰富上下文（不只是标签）
- 模型自然语言能力更强，描述比标签更准确
- 无需改动架构，仅扩展 prompt

**实施成本**：低（修改4个 module prompt + `analyze_tasks` 解析逻辑）

---

#### 2.2 重构 Few-shot 样例系统

**问题**：
- `naming_samples.yaml` 格式与 `naming_styles.yaml` 不一致
- 样例数量少（3个），覆盖场景有限
- 未在命名生成时实际使用

**方案**：
1. **统一样例格式**，与风格模板对齐：
```yaml
# examples/naming_samples.yaml
samples:
  chinese_descriptive:
    - input:
        scene_type: ["做爱"]
        role_archetype: ["人妻"]
        positions: ["后入", "口交"]
        face_visibility: ["露脸"]
        description: "温泉旅馆房间，和服半脱，暖色灯光，亲密互动"
      output: "温泉旅馆的禁忌之夜"
    - input:
        scene_type: ["舞蹈展示"]
        role_archetype: ["OL"]
        description: "办公室场景，黑丝高跟，桌面舞蹈，挑逗眼神"
      output: "深夜办公室的诱惑"
  
  scene_role:
    - input: {...}
      output: "温泉旅馆_美丽人妻"
```

2. **动态注入 Few-shot**：
```python
# src/vrenamer/naming/generator.py
def _build_system_prompt(self, style_def, n, samples):
    few_shot = "\n".join([
        f"输入：{s['input']}\n输出：{s['output']}"
        for s in samples[:3]  # 每个风格3个样例
    ])
    return f"""...
**Few-shot 示例**：
{few_shot}

**当前任务**：
根据以下视频信息生成 {n} 个候选...
"""
```

**收益**：
- 命名质量提升 30-50%（Few-shot 对生成任务效果显著）
- 样例可持续积累（从用户反馈中提取）

**实施成本**：中（重构样例文件 + 修改 `NamingGenerator`）

---

#### 2.3 优化命名生成的输入结构

**问题**：当前 `_build_user_prompt` 仅传递扁平标签，丢失层次信息。

**方案**：结构化输入 + 描述增强

```python
def _build_user_prompt(self, analysis: Dict[str, Any], style_def: StyleDefinition) -> str:
    # 提取结构化信息
    scene_type = analysis.get("scene_type", {})
    role = analysis.get("role_archetype", {})
    
    # 构建层次化输入
    structured_info = f"""
**场景类型**：{scene_type.get('labels', ['未知'])[0]}
  - 置信度：{scene_type.get('confidence', 0):.2f}
  - 描述：{scene_type.get('description', '')}

**角色原型**：{', '.join(role.get('labels', ['未知']))}
  - 描述：{role.get('description', '')}

**体位/动作**：{', '.join(analysis.get('positions', {}).get('labels', []))}

**可见性**：{analysis.get('face_visibility', {}).get('labels', ['未知'])[0]}

**综合描述**：
{self._synthesize_description(analysis)}  # 新增：跨任务综合描述
"""
    return structured_info
```

**收益**：
- 模型获得更完整的上下文
- 描述字段提供创作灵感
- 置信度可用于生成策略调整

**实施成本**：低（修改 `NamingGenerator._build_user_prompt`）

---

### 🟡 P1 - 短期优化（1-2周）

#### 2.4 引入关键帧智能选择

**问题**：当前 `_build_frame_batches` 轮转分配帧，未考虑帧的信息量。

**方案**：基于视觉特征的关键帧筛选

```python
def _select_keyframes(frames: List[Path], target: int) -> List[Path]:
    """
    基于以下策略选择关键帧：
    1. 时间均匀分布（保留）
    2. 场景切换检测（新增）
    3. 运动强度检测（新增）
    """
    # 简化实现：使用 OpenCV 计算帧间差异
    import cv2
    import numpy as np
    
    diffs = []
    prev = None
    for frame in frames:
        img = cv2.imread(str(frame), cv2.IMREAD_GRAYSCALE)
        if prev is not None:
            diff = np.mean(np.abs(img - prev))
            diffs.append((frame, diff))
        prev = img
    
    # 选择差异最大的帧（场景切换/运动高峰）
    diffs.sort(key=lambda x: x[1], reverse=True)
    keyframes = [f for f, _ in diffs[:target//2]]
    
    # 补充时间均匀帧
    uniform = _evenly_sample(frames, target - len(keyframes))
    return sorted(set(keyframes + uniform), key=frames.index)
```

**收益**：
- 分类任务获得更有代表性的帧
- 减少冗余帧，提升推理效率

**实施成本**：中（需要 OpenCV，增加计算开销）

---

#### 2.5 实现反馈驱动的 Prompt 优化

**问题**：`store_feedback` 仅记录，未形成闭环。

**方案**：构建反馈分析与 Prompt 迭代系统

```python
# 新增 src/vrenamer/feedback/analyzer.py
class FeedbackAnalyzer:
    def analyze_feedback(self, feedback_path: Path) -> Dict[str, Any]:
        """
        分析 logs/feedback.jsonl，提取：
        1. 高频选择的命名模式
        2. 被拒绝的命名特征
        3. 标签→命名的映射规律
        """
        patterns = self._extract_patterns(feedback_path)
        return {
            "preferred_styles": [...],  # 用户偏好风格
            "bad_patterns": [...],      # 应避免的模式
            "tag_mappings": {...},      # 标签→短语映射
        }
    
    def generate_dynamic_examples(self, analysis: Dict) -> List[Dict]:
        """从反馈中生成 Few-shot 样例"""
        return [
            {"input": {...}, "output": selected_name}
            for selected_name in analysis["preferred_styles"]
        ]
```

**集成到命名生成**：
```python
# NamingGenerator.__init__
self.feedback_analyzer = FeedbackAnalyzer()
self.dynamic_examples = self.feedback_analyzer.generate_dynamic_examples(...)

# _build_system_prompt 中注入动态样例
```

**收益**：
- 持续学习用户偏好
- 自动优化命名风格
- 减少人工调整 Prompt 的频率

**实施成本**：中（新增模块 + 数据分析逻辑）

---

### 🟢 P2 - 长期优化（1-2月）

#### 2.6 多阶段命名生成（Refinement）

**问题**：当前一次生成最终候选，缺乏迭代优化。

**方案**：引入 Draft → Critique → Refine 流程

```python
async def generate_candidates_with_refinement(self, analysis, style_ids):
    # Stage 1: 生成初稿（temperature=0.8，多样性）
    drafts = await self._generate_drafts(analysis, style_ids, n=10)
    
    # Stage 2: 自我批判（temperature=0.2，严格评估）
    critiques = await self._critique_drafts(drafts, analysis)
    
    # Stage 3: 精炼（temperature=0.5，基于批判改进）
    refined = await self._refine_candidates(drafts, critiques, n=5)
    
    return refined
```

**Critique Prompt 示例**：
```
评估以下命名候选的质量：
1. 是否准确反映视频内容？
2. 是否符合风格要求？
3. 是否有歧义或不当表达？
4. 文件名长度是否合理？

输出：{"score": 0-10, "issues": [...], "suggestions": [...]}
```

**收益**：
- 命名质量显著提升（类似 CoT 效果）
- 减少低质量候选

**实施成本**：高（3倍 API 调用，需要优化并发）

---

#### 2.7 引入视觉-语言联合编码

**问题**：当前分类→命名两阶段，信息瓶颈明显。

**方案**：端到端命名生成（跳过分类任务）

```python
async def generate_names_e2e(
    self,
    frames: List[Path],
    transcript: str,
    style_def: StyleDefinition,
) -> List[str]:
    """
    直接从帧+字幕生成命名，无需中间分类
    """
    system_prompt = f"""
你是视频命名专家。直接根据视频帧和字幕生成文件名。

风格：{style_def.name}
要求：{style_def.prompt_template}
"""
    
    # 使用 Gemini 多模态能力，一次性处理
    response = await self.llm.classify_json(
        model=self.model,
        system_prompt=system_prompt,
        user_text=f"字幕：{transcript}\n\n生成5个候选文件名。",
        images=frames[:12],  # 直接传入关键帧
        temperature=0.7,
    )
    return self._parse_response(response, 5)
```

**对比实验**：
- A组：当前两阶段流程
- B组：端到端生成
- 指标：命名准确率、用户满意度、API成本

**收益**：
- 理论上信息损失最小
- 简化架构，减少维护成本

**风险**：
- 可能丢失结构化标签的可解释性
- 需要大量测试验证效果

**实施成本**：高（需要重构核心流程 + 充分测试）

---

## 三、实施路线图

### 第一周（快速见效）
1. ✅ 实施 **2.1 增强分类输出**（1天）
2. ✅ 实施 **2.3 优化命名输入**（1天）
3. ✅ 重构 **2.2 Few-shot 样例**（3天）

**预期提升**：命名准确率 +20-30%

### 第二周（反馈闭环）
4. ✅ 实施 **2.5 反馈分析系统**（5天）
5. ✅ 收集 20+ 真实样例，补充到 `naming_samples.yaml`

**预期提升**：持续优化能力 +50%

### 第三-四周（深度优化）
6. 🔄 实施 **2.4 关键帧选择**（可选，视效果决定）
7. 🔄 实验 **2.6 多阶段生成**（小规模测试）

### 长期（架构升级）
8. 🔬 实验 **2.7 端到端生成**（需要充分对比测试）

---

## 四、关键指标与评估

### 4.1 量化指标

| 指标 | 当前基线 | 目标（P0后） | 目标（P1后） |
|------|---------|-------------|-------------|
| **命名准确率** | 未测量 | 70% | 85% |
| **用户首选率** | 未测量 | 60% | 80% |
| **平均生成时间** | ~30s | <35s | <40s |
| **API 成本/视频** | ~$0.05 | <$0.06 | <$0.10 |

### 4.2 评估方法

1. **人工评估**：
   - 随机抽取 50 个视频
   - 3 名评审员独立打分（1-5分）
   - 维度：准确性、可读性、风格一致性

2. **A/B 测试**：
   - WebUI 中随机展示新旧版本候选
   - 记录用户选择偏好

3. **反馈分析**：
   - 统计 `feedback.jsonl` 中的选择分布
   - 分析被拒绝候选的共性问题

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **API 成本增加** | 中 | 优化并发、缓存中间结果 |
| **生成时间变长** | 中 | 异步处理、进度反馈 |
| **模型输出不稳定** | 高 | 增加重试、Fallback 机制 |
| **Few-shot 样例偏差** | 中 | 定期审查、多样性检查 |

---

## 六、附录：Prompt 优化 Checklist

### 分类任务 Prompt
- [ ] 增加 `description` 字段要求
- [ ] 明确描述长度（50-80字）
- [ ] 强调关键视觉细节（服饰、道具、动作）
- [ ] 要求时序连贯性（如适用）

### 命名生成 Prompt
- [ ] 注入 Few-shot 样例（每个风格3个）
- [ ] 传递结构化输入（标签+描述）
- [ ] 明确禁止项（演员名、厂牌等）
- [ ] 增加输出质量约束（长度、可读性）

### Few-shot 样例质量
- [ ] 覆盖主要场景类型（做爱、舞蹈、展示等）
- [ ] 覆盖主要角色原型（人妻、学生、OL等）
- [ ] 每个风格至少 5 个样例
- [ ] 样例多样性（避免模板化）

---

## 七、总结

**核心洞察**：
1. 当前最大瓶颈是 **信息损失**（分类标签丢失细节）
2. 最高 ROI 改进是 **Few-shot 样例系统**
3. 长期方向是 **端到端生成** 或 **多阶段精炼**

**立即行动**：
- 先实施 P0 方案（1周内完成）
- 收集真实反馈数据（持续）
- 基于数据决定 P1/P2 优先级

**成功标准**：
- 用户首选率 >80%
- 命名准确率 >85%
- 反馈闭环自动化运行
