# Extractor 评估准确率低的问题诊断

## 问题现象

- **TP (strict matches): 0** - 没有完全匹配的任务
- **TP (partial matches): 25** - 所有匹配都是部分的
- **Task Precision/Recall/F1: 0.5000** - 准确率很低

## 可能的原因

### 1. Title 解析不准确

**问题**：从 `title` 字段解析 `action` 和 `object` 可能不准确。

**原因**：
- LLM 返回的 title 格式可能不是标准的 `[VERB OBJECT OWNER]` 格式
- 可能是自然语言格式，如 "Review updated brand guidelines and send feedback"
- 复合动作（如 "review and send"）难以准确解析

**解决方案**：
- 已改进 `parse_action_object_from_title()` 函数
- 添加了对复合动作的处理
- 添加了调试输出，可以查看解析结果

### 2. 任务格式不匹配

**问题**：预测任务和 ground truth 任务的格式可能不一致。

**检查方法**：
运行测试时会输出调试信息：
```
[DEBUG] Email e001:
  Raw task: {'title': '...', 'owner': '...', 'due_iso': '...'}
  Converted: {'owner': '...', 'action': '...', 'object': '...', 'deadline': '...'}
  Gold task: {'title': '...', 'owner': '...', 'due_raw': '...'}
  Gold converted: {'owner': '...', 'action': '...', 'object': '...', 'deadline': '...'}
```

**解决方案**：
- 检查调试输出，确认解析是否正确
- 如果解析不准确，需要改进 `parse_action_object_from_title()` 函数

### 3. Deadline 格式不匹配

**问题**：预测的 deadline 和 ground truth 的 deadline 格式可能不同。

**原因**：
- 预测任务使用 `due_iso`（标准化后的格式）
- Ground truth 使用 `due_raw`（原始文本）
- 转换时可能丢失信息

**解决方案**：
- 已修改代码，优先使用原始 `due` 文本
- 如果 LLM 返回了原始 `due`，会使用它而不是 `due_iso`

### 4. 评估逻辑问题

**问题**：TP/FP/FN 计算逻辑可能不正确。

**已修复**：
- 使用与 eval 脚本相同的 greedy matching 逻辑
- 直接计算 lenient TP，而不是从 precision 反推
- 使用 `task_match_k=2`（至少匹配 2 个字段）

## 调试步骤

### 1. 运行测试并查看调试输出

```bash
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl \
  --max_examples 10
```

查看调试输出，检查：
- Raw task 的格式
- Converted task 的格式
- Gold task 的格式
- Gold converted 的格式

### 2. 检查 title 解析

如果 action 或 object 解析不正确，可能需要：
- 改进 `parse_action_object_from_title()` 函数
- 添加更多动词模式
- 处理特殊情况

### 3. 检查 LLM 输出格式

确认 LLM 返回的格式是否符合预期：
- Title 应该是 `[VERB OBJECT OWNER]` 格式
- 如果返回自然语言，需要改进解析逻辑

## 与 Eval 脚本的差异

### Eval 脚本
- 直接要求 LLM 返回 `{owner, action, object, deadline}` 格式
- 不需要从 title 解析

### 实际运行测试
- LLM 返回 `{title, owner, due}` 格式
- 需要从 title 解析 action 和 object
- 这是导致准确率低的主要原因

## 建议

1. **短期方案**：改进 title 解析逻辑，处理更多情况
2. **长期方案**：修改实际运行的 extractor，直接返回 `{owner, action, object, deadline}` 格式，与 eval 脚本一致

## 下一步

1. 运行测试并查看调试输出
2. 根据调试输出改进 title 解析逻辑
3. 如果问题仍然存在，考虑修改 extractor 的输出格式

