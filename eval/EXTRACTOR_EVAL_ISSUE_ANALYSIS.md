# Extractor 评估结果差的原因分析

## 问题描述

使用 eval 逻辑测试的结果非常差：
- TP (strict matches): 1
- TP (partial matches): 0
- TP (total): 1
- FP: 24
- FN: 24
- Task Precision: 0.0400
- Task Recall: 0.0400
- Task F1: 0.0400

## 根本原因

### 1. Deadline 解析失败

**问题**：`_normalize_date` 函数无法正确解析相对时间表达式（如 "Friday", "Friday at 6 PM"）

**原因**：
- `_normalize_date` 需要 `received_at` 参数来解析相对时间
- 但在评估代码中，调用 `_normalize_date` 时**没有传递 `received_at` 参数**
- 导致 "Friday" 无法被解析为具体日期，返回原字符串 "Friday"
- 预测的 deadline（如 "2025-11-15T18:00:00Z"）会被解析为 "2025-11-15"
- Ground truth 的 deadline（如 "Friday at 6 PM"）无法解析，保持为 "Friday at 6 PM"
- **结果**：两者永远不匹配

**修复**：
- 在调用 `_normalize_date` 时传递 `received_at` 参数
- 从 row 中获取 `sent_date` 或 `date` 字段作为 `received_at`

### 2. 默认 lenient=True 可能导致问题

**问题**：默认使用 `lenient=True`，但可能应该使用 `very_lenient=True` 来获得更好的匹配

**原因**：
- `lenient` 模式只进行文本标准化，不进行语义相似度匹配
- 如果 action 或 object 有细微差异，`lenient` 模式无法匹配
- 例如："review" vs "Review" 可以匹配，但 "review" vs "check" 无法匹配

**建议**：
- 默认使用 `very_lenient=True` 和 `sim_threshold=0.6`
- 或者让用户明确指定评估模式

### 3. Title 解析可能不准确

**问题**：从 title 解析 action 和 object 可能不准确

**原因**：
- LLM 返回的 title 格式是 `[VERB + OBJECT + OWNER]`（根据 EXTRACTION_PROMPT）
- Ground truth 的 title 格式是自然语言（如 "Review updated brand guidelines and send feedback"）
- `parse_action_object_from_title` 函数需要处理这两种格式
- 如果解析不准确，action 或 object 可能为 None 或错误，导致匹配失败

**示例**：
- LLM: `[Submit Q4 report Alice]` → action="submit", object="q4 report"
- GT: `Submit Q4 report` → action="submit", object="Q4 report"
- 解析后应该能匹配，但如果有细微差异（如大小写、空格），可能失败

### 4. 数据格式不一致

**问题**：预测任务和 ground truth 任务的格式可能不一致

**原因**：
- LLM 返回的任务格式：`{title, owner, due, type}`
- Ground truth 格式：`{title, owner, due_raw}`
- 转换后的格式：`{owner, action, object, deadline}`
- 如果转换过程中丢失信息或解析错误，会导致匹配失败

## 修复方案

### 1. 修复 deadline 解析

```python
# 在 evaluate_dataset 中获取 received_at
received_at = row.get("sent_date") or row.get("date") or row.get("received_at")

# 在调用 _normalize_date 时传递 received_at
deadline = _normalize_date(task.get("deadline"), received_at=received_at)
```

### 2. 改进默认评估模式

```python
# 默认使用 very_lenient 模式
lenient: bool = False,
very_lenient: bool = True,  # 改为默认 True
sim_threshold: float = 0.6,
task_match_k: int = 2,
```

### 3. 增强 title 解析

- 改进 `parse_action_object_from_title` 函数，更好地处理 `[VERB + OBJECT + OWNER]` 格式
- 处理自然语言格式时，更准确地提取 action 和 object

### 4. 添加调试输出

- 在转换任务格式时，打印转换前后的任务，便于调试
- 在匹配失败时，打印具体的匹配失败原因

## 验证修复

修复后，应该看到：
- Deadline 匹配率提高（因为能正确解析相对时间）
- TP 数量增加（因为 deadline 能匹配）
- Precision 和 Recall 提高

## 建议

1. **使用 very_lenient 模式**：对于任务提取评估，语义相似度匹配比严格匹配更合理
2. **确保 received_at 传递**：这是解析相对时间的关键
3. **改进 title 解析**：确保从不同格式的 title 中准确提取 action 和 object
4. **添加详细日志**：帮助诊断匹配失败的原因

