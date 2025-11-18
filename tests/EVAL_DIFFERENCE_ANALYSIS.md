# 测试结果差异分析

## 问题描述

- **Eval 单测/组合测试**：Gemini 性能更好
- **实际运行测试** (`test_summarizer_eval.py`)：GPT-4o-mini 效果更好

## 根本原因：测试方式完全不同

### 1. Eval 脚本 (`eval/run_summarizer_gemini.py`)

**模型输出格式**：
```json
{
  "actor": "Alice",
  "action": "send",
  "object": "project draft",
  "deadline": "2025-11-14",
  "notes": "..."
}
```

**评估方式**：
- 直接比较 JSON 字段
- 使用 `slot_acc()` 比较 `actor`, `action`, `object`, `deadline`
- 使用 `fact_prf()` 比较所有字段的 token 集合
- 有 `postprocess_summary()` 后处理（归一化 actor, action）

**Prompt**：
- 要求模型直接输出结构化 JSON
- 格式：`{actor, action, object, deadline, notes}`

---

### 2. 实际运行测试 (`tests/test_summarizer_eval.py`)

**模型输出格式**：
```json
{
  "summary": "Alice asks you to send the project draft by Friday."
}
```

**评估方式**：
- 从 summary **文本**中提取 facts（使用正则表达式）
- `extract_predicted_facts()` 函数解析文本
- 提取 `actor`, `action`, `object`, `deadline` 从句子中

**Prompt**：
- 要求模型输出一个句子
- 格式：`{summary: "..."}`

---

## 关键差异对比

| 特性 | Eval 脚本 | 实际运行测试 |
|------|----------|------------|
| **输出格式** | 结构化 JSON 字段 | Summary 文本句子 |
| **模型任务** | 直接提取结构化信息 | 生成自然语言句子 |
| **评估方式** | 直接比较 JSON 字段 | 从文本中提取 facts |
| **后处理** | `postprocess_summary()` | `extract_predicted_facts()` (正则) |
| **Prompt** | "Output JSON with keys: actor, action..." | "Return ONE sentence..." |
| **数据来源** | `eval/dataset/emails.jsonl` | `tests/data/summarizer_gold.jsonl` |

---

## 为什么结果不同？

### Gemini 在 Eval 脚本中表现更好

**原因**：
1. ✅ **结构化输出优势**：Gemini 擅长直接输出结构化 JSON
2. ✅ **字段提取准确**：直接输出字段，无需文本解析
3. ✅ **后处理帮助**：`postprocess_summary()` 归一化帮助匹配

**Gemini 的优势**：
- 直接输出 `{actor: "Alice", action: "send", ...}`
- 字段格式规范，易于比较
- 不需要从文本中提取，减少错误

---

### GPT-4o-mini 在实际运行测试中表现更好

**原因**：
1. ✅ **自然语言生成优势**：GPT-4o-mini 擅长生成自然语言句子
2. ✅ **句子结构清晰**：生成的句子格式规范，易于正则提取
3. ✅ **Few-shot 示例帮助**：`SUMMARY_FEW_SHOT_EXAMPLES` 提供示例

**GPT-4o-mini 的优势**：
- 生成 "Alice asks you to send the project draft by Friday."
- 句子结构清晰，正则表达式容易提取
- Actor 准确率 100%（因为句子以 actor 开头）

---

## 具体指标分析

### Gemini 在 Eval 脚本中的表现
- **Action Accuracy: 25%** - 低（但 eval 脚本有映射函数帮助）
- **Object Accuracy: 30%** - 低
- **ROUGE-1: 0.5963** - 中等

### GPT-4o-mini 在实际运行测试中的表现
- **Action Accuracy: 60%** - 更高（从句子中提取更容易）
- **Object Accuracy: 0%** - 极低（正则表达式提取失败）
- **ROUGE-1: 0.7443** - 更高（句子生成质量好）

---

## 问题根源

### Object Accuracy = 0% 的原因

GPT-4o-mini 生成的句子格式可能是：
```
"Alice asks you to send the project draft by Friday."
```

但 `extract_predicted_facts()` 的正则表达式可能无法正确提取 object：
- 期望格式：`"to [action] [object]"`
- 实际格式：`"asks you to [action] [object]"`

正则表达式 `r"\bto\s+([^.;]+)"` 可能匹配到整个短语，而不是单独提取 object。

---

## 解决方案

### 方案 1：统一测试方式（推荐）

让 `test_summarizer_eval.py` 也使用结构化 JSON 输出：

1. 修改 `app/services/summarizer.py` 支持两种模式：
   - 模式 A：输出 `{summary: "..."}`（当前）
   - 模式 B：输出 `{actor, action, object, deadline}`（eval 脚本）

2. 或者修改 `test_summarizer_eval.py` 调用 eval 脚本的客户端

### 方案 2：改进文本提取逻辑

改进 `extract_predicted_facts()` 函数，更好地从句子中提取 facts。

### 方案 3：使用实际运行格式

修改 eval 脚本，使用实际运行的格式（输出 summary 文本），然后从文本中提取。

---

## 结论

**这不是模型性能问题，而是测试方式不同导致的**：

- **Eval 脚本**：测试结构化 JSON 输出能力 → Gemini 表现好
- **实际运行测试**：测试自然语言生成能力 → GPT-4o-mini 表现好

**建议**：
1. 确定实际使用场景需要什么格式
2. 统一测试方式，使用相同的输出格式和评估方法
3. 根据实际使用场景选择模型

