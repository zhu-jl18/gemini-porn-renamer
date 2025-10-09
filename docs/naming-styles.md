# 命名风格配置指南

本文档说明如何配置和自定义视频命名风格。

## 📝 设计理念

**AI 创造性命名**，而非死板的格式化模板。系统会根据配置的风格，生成多种命名候选供用户选择。

## 📁 配置文件

### 位置
```
examples/naming_styles.yaml
```

### 结构
```yaml
styles:
  风格ID:
    name: "风格显示名称"
    description: "风格描述"
    language: "zh/en"
    format: "{格式说明}"
    examples: ["示例1", "示例2"]
    prompt_template: |
      给 AI 的提示词...
```

## 🎨 内置风格

### 1. 中文描述性 (`chinese_descriptive`)
**特点**：优雅含蓄，注重场景和氛围

**示例**：
```
温泉旅馆的诱惑.mp4
午后的秘密时光.mp4
海边别墅的邂逅.mp4
雨夜的禁忌关系.mp4
```

**适用场景**：
- 希望文件名优雅含蓄
- 不想太露骨
- 注重氛围感

### 2. 场景+角色 (`scene_role`)
**特点**：场景与角色类型结合，更具体

**示例**：
```
温泉旅馆_美丽人妻.mp4
深夜办公室_女上司.mp4
按摩店_新人技师.mp4
健身房_瑜伽教练.mp4
```

**适用场景**：
- 需要明确场景和角色
- 便于分类查找
- 信息量适中

### 3. 角色+场景+动作 (`role_scene_action`)
**特点**：完整叙事，三要素齐全

**示例**：
```
人妻在温泉旅馆的秘密.mp4
护士在医院值班的夜晚.mp4
女教师放学后的补习.mp4
邻家姐姐的午后来访.mp4
```

**适用场景**：
- 需要完整故事感
- 信息量丰富
- 长文件名可接受

### 4. P站风格 (`pornhub_style`)
**特点**：英文直接，符合国际站点风格

**示例**：
```
Hot MILF seduced in hotel.mp4
Sexy nurse after night shift.mp4
Beautiful wife cheating at home.mp4
Young teacher private lesson.mp4
```

**适用场景**：
- 偏好英文命名
- 直接明确
- 国际化风格

### 5. 简洁标题 (`concise`)
**特点**：短小精悍，3-6 个字

**示例**：
```
温泉诱惑.mp4
午夜秘密.mp4
禁忌关系.mp4
邻家少妇.mp4
```

**适用场景**：
- 喜欢简短命名
- 系统文件名长度限制
- 核心概念突出

### 6. 场景+演员 (`with_actor`)
**特点**：场景描述 + 演员名（可选）

**示例**：
```
温泉旅馆的诱惑_明日花绮罗.mp4
午后的秘密时光_波多野结衣.mp4
办公室加班.mp4  # 未识别演员时省略
```

**适用场景**：
- 需要演员信息
- 按演员整理
- 演员可识别时

## ⚙️ 使用配置

### 方式1：环境变量配置
编辑 `.env` 文件：

```env
# 默认使用的风格（逗号分隔，按顺序生成）
NAMING_STYLES=chinese_descriptive,scene_role,pornhub_style,concise

# 风格配置文件路径
NAMING_STYLE_CONFIG=examples/naming_styles.yaml

# 每种风格生成候选数
CANDIDATES_PER_STYLE=1

# 总候选数
TOTAL_CANDIDATES=5
```

### 方式2：CLI 命令行指定
```powershell
# 使用默认风格
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "test.mp4"

# 指定特定风格
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "test.mp4" \
  --styles chinese_descriptive,pornhub_style

# 使用自定义配置文件
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "test.mp4" \
  --style-config my_custom_styles.yaml
```

## 🎨 自定义风格

### 步骤1：编辑配置文件
复制 `examples/naming_styles.yaml` 创建自己的：

```powershell
copy examples\naming_styles.yaml examples\my_styles.yaml
```

### 步骤2：添加自定义风格
```yaml
custom_styles:
  my_romantic_style:
    name: "浪漫温馨"
    description: "强调情感和浪漫氛围"
    language: "zh"
    format: "{情感词汇}_{场景}"
    examples:
      - "甜蜜的约会_海边夕阳"
      - "温柔的夜晚_星空下"
      - "浪漫的邂逅_咖啡馆"
    prompt_template: |
      生成浪漫温馨的命名，强调情感。
      格式：{情感词汇}_{场景}
      要求：
      - 使用温馨词汇（甜蜜、温柔、浪漫等）
      - 场景富有诗意
      - 10-15个汉字
```

### 步骤3：使用自定义风格
```powershell
.\.venv\Scripts\python.exe -m vrenamer.cli.main run "test.mp4" \
  --style-config examples/my_styles.yaml \
  --styles my_romantic_style
```

## 💡 风格设计技巧

### 1. Prompt 模板设计
好的 prompt 应该包含：
- **明确的格式说明**：告诉 AI 输出什么结构
- **具体的要求**：长度、语言、风格
- **限制条件**：禁止什么、必须什么

**示例**：
```yaml
prompt_template: |
  生成视频文件名，风格：{你的风格描述}
  
  格式：{格式说明}
  
  要求：
  - 长度：10-20 个字符
  - 语言：中文/英文
  - 风格：优雅/直接/简洁
  - 禁止：粗俗词汇、过长描述
  
  参考示例：
  {列举 2-3 个示例}
```

### 2. 示例（Examples）的重要性
- 至少提供 3-5 个示例
- 示例要体现风格特点
- 示例长度和格式保持一致

### 3. 语言选择
- `zh`：中文命名
- `en`：英文命名
- `mixed`：中英混合（如：`Hot Scene_温泉旅馆.mp4`）

### 4. 格式字段说明
常用字段占位符：
- `{场景}`：温泉、办公室、海边
- `{角色}`：人妻、护士、教师
- `{动作}`：诱惑、邂逅、秘密
- `{氛围}`：午后、雨夜、深夜
- `{演员}`：明日花绮罗、波多野结衣

## 🔄 风格组合策略

### 策略1：多样化组合
```yaml
selected_styles:
  - chinese_descriptive   # 含蓄
  - pornhub_style        # 直接
  - concise              # 简洁
```
→ 给用户从含蓄到直接的多种选择

### 策略2：同类风格组合
```yaml
selected_styles:
  - chinese_descriptive
  - scene_role
  - role_scene_action
```
→ 都是中文，信息量递增

### 策略3：语言混合
```yaml
selected_styles:
  - chinese_descriptive  # 中文
  - pornhub_style       # 英文
```
→ 中英文各一半

## 📊 批量处理时的风格选择

批量处理时，建议：
1. 选择 1-2 种主要风格
2. 每种风格生成 2-3 个候选
3. 使用一致的风格便于整理

```powershell
# 批量处理使用单一风格
.\.venv\Scripts\python.exe -m vrenamer.cli.main batch "D:\Videos" \
  --styles chinese_descriptive \
  --candidates 3
```

## ⚠️ 注意事项

1. **文件名长度**：Windows 文件名限制 255 字符，建议不超过 80
2. **非法字符**：`< > : " / \ | ? *` 会自动替换为 `_`
3. **演员识别**：AI 可能识别不出演员，建议使用可选演员风格
4. **语言混用**：避免在同一个文件名中混用中英文（除非特意设计）

## 📚 参考资料

- 完整配置示例：`examples/naming_styles.yaml`
- 核心需求文档：`核心需求.md`
- AI 协作准则：`AGENTS.md`
