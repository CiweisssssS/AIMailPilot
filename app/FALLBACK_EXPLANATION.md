# Fallback 机制说明

## 什么是 Fallback？

**Fallback（回退/备用）** 是一种容错机制：当检测到复杂情况时，自动切换到更强大的模型或备用方案。

## 在 Extractor 中的 Fallback

### 工作原理

1. **默认情况**：使用默认模型（GPT-4o-mini）
2. **检测复杂情况**：自动检测文本中是否包含复杂时间表达式
3. **自动切换**：如果检测到复杂时间，切换到 fallback 模型

### 代码流程

```python
# 1. 检测复杂时间表达式
use_fallback = _has_complex_time_expression(text_for_llm)

# 2. 根据检测结果选择模型
if use_fallback:
    logger.info("Complex time expression detected, using fallback model (GPT-4o-mini)")
    # 使用 fallback 模型
else:
    logger.info("Using default extractor model (GPT-4o-mini)")
    # 使用默认模型

# 3. 调用 LLM
tasks = await llm_provider.extract_tasks([...], use_fallback=use_fallback)
```

### 复杂时间表达式示例

以下情况会触发 fallback：

- ✅ "next week", "this month", "this quarter"
- ✅ "early next week", "mid next month"
- ✅ "in 2 weeks", "3 months later"
- ✅ "end of next week", "beginning of next month"
- ✅ "first week of October"
- ✅ "by the end of next week"
- ✅ "10/15/2024 at 3:30pm"
- ✅ "Friday morning", "next Friday evening"

### 为什么需要 Fallback？

**原因**：
- 复杂时间表达式需要更强的推理能力
- 默认模型（GPT-4o-mini）可能无法准确解析复杂时间
- Fallback 模型（原本是 GPT-4o）有更强的理解能力

**当前状态**：
- 现在默认和 fallback 都是 GPT-4o-mini
- Fallback 机制仍然存在，但使用的是同一个模型
- 如果将来需要，可以轻松切换 fallback 到更强大的模型

## Fallback 的优势

1. **智能切换**：自动识别需要更强模型的情况
2. **成本优化**：只在必要时使用更昂贵的模型
3. **性能平衡**：在速度和准确性之间取得平衡

## 实际例子

### 示例 1：简单时间（不使用 fallback）
```
邮件内容: "Please send the report by Friday 5pm"
检测结果: 简单时间表达式
使用模型: GPT-4o-mini（默认）
```

### 示例 2：复杂时间（使用 fallback）
```
邮件内容: "Please complete the project by the end of next week"
检测结果: 复杂时间表达式（"end of next week"）
使用模型: GPT-4o-mini（fallback，虽然现在和默认一样）
```

## 代码位置

- **检测函数**: `app/services/extractor.py:68` - `_has_complex_time_expression()`
- **模型选择**: `app/core/llm.py:347` - `extract_tasks()` 方法
- **配置**: `app/core/config.py:20` - `extractor_fallback_model`

## 总结

**Fallback = 备用方案**

- 正常情况下：使用默认模型（快速、便宜）
- 复杂情况下：自动切换到 fallback 模型（更准确）
- 当前配置：默认和 fallback 都是 GPT-4o-mini，但机制仍然有效

