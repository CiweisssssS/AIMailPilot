# Extractor 测试结果差异分析

## 问题描述

- **Eval 单测/组合测试**：Gemini 性能更好
- **实际运行测试** (`tests/extractor_eval.py`)：GPT-4o-mini 效果更好

## 根本原因：评估方式完全不同

### 1. Eval 脚本 (`eval/run_pipeline.py`)

**任务格式期望**：
```json
{
  "owner": "Alice",
  "action": "review",
  "object": "brand guidelines",
  "deadline": "Friday 6 PM"
}
```

**评估方式**：
- 使用 `prf_tasks()` 函数
- 比较 `{owner, action, object, deadline}` 四个字段
- 从 `title` 字段中解析出 `action` 和 `object`
- 使用 `due` 字段（原始文本，如 "Friday 6 PM"）

**Prompt**：
- 要求输出 `{title, owner, due, type, source_message_id}`
- `title` 格式：`[VERB OBJECT OWNER]`
- `due` 是原始文本，不转换为 ISO 格式

**后处理**：
- 从 `title` 中提取 `action` 和 `object`
- 使用原始 `due` 文本

---

### 2. 实际运行测试 (`tests/extractor_eval.py`)

**任务格式期望**：
```json
{
  "title": "Review updated brand guidelines and send feedback",
  "owner": "Mark",
  "due_iso": "Mon Nov 14, 2025, 18:00"
}
```

**评估方式**：
- 使用 `compute_metrics()` 函数
- 比较 `title` 相似度（使用 `title_similarity()`）
- 比较 `due_raw` vs `due_iso`（使用时间容差匹配）
- 比较 `owner`（精确匹配）

**Prompt**：
- 使用 `EXTRACTION_PROMPT`（与 eval 脚本相同）
- 但后处理不同

**后处理**：
- `normalize_deadline()` 将原始 `due` 转换为 `due_iso` 格式
- `_infer_owner()` 推断 owner
- 返回 `{title, owner, due_iso, source_span}`

---

### 3. 实际运行 (`app/services/extractor.py`)

**返回格式**：
```json
{
  "title": "Review updated brand guidelines and send feedback",
  "owner": "Mark",
  "due_iso": "Mon Nov 14, 2025, 18:00",
  "source_span": {"start": 0, "end": 100}
}
```

**处理流程**：
1. 调用 `llm_provider.extract_tasks()` 获取原始任务
2. 使用 `normalize_deadline()` 标准化 deadline
3. 使用 `_infer_owner()` 推断 owner
4. 返回格式化后的任务

---

## 关键差异对比

| 特性 | Eval 脚本 | 实际运行测试 | 实际运行 |
|------|----------|------------|---------|
| **任务格式** | `{owner, action, object, deadline}` | `{title, owner, due_iso}` | `{title, owner, due_iso, source_span}` |
| **评估字段** | owner, action, object, deadline | title, owner, due_iso | N/A |
| **Deadline 格式** | 原始文本 ("Friday 6 PM") | ISO 格式 ("Mon Nov 14, 2025, 18:00") | ISO 格式 |
| **Title 处理** | 从 title 解析 action/object | 直接比较 title 相似度 | 保留原始 title |
| **Owner 处理** | 直接使用 | `_infer_owner()` 推断 | `_infer_owner()` 推断 |
| **评估函数** | `prf_tasks()` | `compute_metrics()` | N/A |
| **匹配方式** | JSON 字符串化或 k-of-4 字段匹配 | Title 相似度 + 时间容差 | N/A |

---

## 为什么结果不同？

### GPT-4o-mini 在实际运行测试中表现更好

**原因**：
1. ✅ **Title 生成质量**：GPT-4o-mini 生成的 title 更符合测试脚本的相似度匹配
2. ✅ **Deadline 标准化**：`normalize_deadline()` 后处理帮助 GPT-4o-mini 的 deadline 匹配更好
3. ✅ **Owner 推断**：`_infer_owner()` 后处理帮助 GPT-4o-mini 的 owner 匹配更好

**GPT-4o-mini 的优势**：
- Title 格式更规范，相似度匹配更容易
- Deadline 标准化后，时间容差匹配更准确
- Owner 推断逻辑更适合 GPT-4o-mini 的输出格式

---

### Gemini 在 Eval 脚本中表现更好

**原因**：
1. ✅ **结构化输出优势**：Gemini 擅长直接输出结构化字段
2. ✅ **字段提取准确**：从 title 中解析 action/object 更准确
3. ✅ **原始 deadline 格式**：Gemini 的原始 deadline 文本更符合 eval 脚本的期望

**Gemini 的优势**：
- 直接输出 `{owner, action, object, deadline}` 格式更规范
- Title 格式 `[VERB OBJECT OWNER]` 更易于解析
- 原始 deadline 文本更准确

---

## 具体指标分析

### GPT-4o-mini 在实际运行测试中的表现
- **Task Precision: 0.8148** - 较高
- **Task Recall: 0.8800** - 很高
- **Task F1: 0.8462** - 最高
- **Owner match: 0.9091** - 很高（得益于 `_infer_owner()`）
- **Due match: 0.5000** - 中等（标准化后匹配）

### Gemini 在 Eval 脚本中的表现
- **Task Precision: 0.8077** - 较高
- **Task Recall: 0.8400** - 较高
- **Task F1: 0.8235** - 较高
- **Owner match: 0.9524** - 很高（直接输出更准确）
- **Due match: 0.4762** - 中等（原始文本匹配）

---

## 问题根源

### 1. 评估格式不匹配

- **Eval 脚本**：评估 `{owner, action, object, deadline}` 格式
- **测试脚本**：评估 `{title, owner, due_iso}` 格式
- **实际运行**：返回 `{title, owner, due_iso, source_span}` 格式

### 2. 后处理逻辑不同

- **Eval 脚本**：从 title 解析 action/object，使用原始 deadline
- **测试脚本**：直接使用 title，标准化 deadline，推断 owner

### 3. 匹配算法不同

- **Eval 脚本**：JSON 字符串化或 k-of-4 字段匹配
- **测试脚本**：Title 相似度 + 时间容差匹配

---

## 解决方案

### 方案 1：统一测试方式（推荐）

让 `tests/extractor_eval.py` 也使用 eval 脚本的评估逻辑：

1. 修改 `extract_tasks_from_text()` 返回格式，包含 `action` 和 `object` 字段
2. 或修改评估逻辑，从 `title` 中解析 `action` 和 `object`
3. 使用 `prf_tasks()` 函数进行评估

### 方案 2：改进后处理逻辑

改进 `extract_tasks_from_text()` 的后处理，使其输出格式与 eval 脚本一致。

### 方案 3：使用实际运行格式

修改 eval 脚本，使用实际运行的格式（`{title, owner, due_iso}`），然后从 title 中提取信息。

---

## 结论

**这不是模型性能问题，而是测试方式不同导致的**：

- **Eval 脚本**：测试结构化字段提取能力（owner, action, object, deadline） → Gemini 表现好
- **实际运行测试**：测试任务提取和标准化能力（title, owner, due_iso） → GPT-4o-mini 表现好

**建议**：
1. 确定实际使用场景需要什么格式
2. 统一测试方式，使用相同的输出格式和评估方法
3. 根据实际使用场景选择模型

**当前情况**：
- 如果实际使用需要 `{title, owner, due_iso}` 格式，GPT-4o-mini 更适合
- 如果实际使用需要 `{owner, action, object, deadline}` 格式，Gemini 更适合

