# extractor_eval.py 修改说明

## 修改目的

将 `tests/extractor_eval.py` 的评估逻辑与 `eval/run_pipeline.py` 脚本对齐，确保测试结果一致。

## 主要修改

### 1. 导入 eval 脚本的评估函数

```python
from eval.run_pipeline import prf_tasks, due_date_correctness, _normalize_owner, _normalize_text, _normalize_date, _similarity
```

### 2. 添加任务格式转换函数

**`parse_action_object_from_title()`**：
- 从 `title` 字段中解析 `action` 和 `object`
- 支持两种格式：
  - `[VERB OBJECT OWNER]` 格式（括号格式）
  - 自然语言格式（如 "Review brand guidelines"）

**`convert_task_to_eval_format()`**：
- 将任务从 `{title, owner, due_iso}` 格式转换为 `{owner, action, object, deadline}` 格式
- 使用原始 `due` 文本（如果可用），而不是标准化后的 `due_iso`

### 3. 修改 `evaluate_dataset` 函数

**之前**：
- 使用 `compute_metrics()` 函数
- 比较 `title` 相似度和 `due_iso` 时间容差

**现在**：
- 使用 `prf_tasks()` 函数（与 eval 脚本一致）
- 比较 `{owner, action, object, deadline}` 四个字段
- 从 `title` 中解析 `action` 和 `object`
- 使用原始 `due` 文本（从 LLM 响应中获取）

### 4. 获取原始 LLM 响应

当 agent 是 `extract_tasks_from_text` 时：
- 直接调用 LLM 获取原始响应
- 提取原始 `due` 文本（未标准化）
- 合并到格式化任务中

## 评估方式对比

| 特性 | 修改前 | 修改后 |
|------|--------|--------|
| **任务格式** | `{title, owner, due_iso}` | `{owner, action, object, deadline}` |
| **评估函数** | `compute_metrics()` | `prf_tasks()` |
| **匹配方式** | Title 相似度 + 时间容差 | JSON 字符串化或 k-of-4 字段匹配 |
| **Deadline 格式** | 标准化后的 `due_iso` | 原始 `due` 文本 |
| **Action/Object** | 从 title 中提取（用于显示） | 从 title 中解析（用于评估） |

## 使用方式

运行方式不变：

```bash
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl \
  --title_thresh 0.5 \
  --tolerance_minutes 60
```

## 预期效果

- ✅ 与 eval 脚本使用相同的评估逻辑
- ✅ 结果应该与 `eval/run_pipeline.py` 一致
- ✅ 使用相同的任务格式和匹配方式

## 注意事项

1. **数据格式**：
   - Gold tasks 可以是 `{title, owner, due_raw}` 格式或 `{owner, action, object, deadline}` 格式
   - 脚本会自动转换

2. **原始 due 文本**：
   - 如果 agent 是 `extract_tasks_from_text`，脚本会尝试获取原始 LLM 响应
   - 如果获取失败，会使用格式化任务中的 `due_iso`

3. **Title 解析**：
   - 支持 `[VERB OBJECT OWNER]` 格式
   - 支持自然语言格式
   - 如果解析失败，会使用 fallback 逻辑

4. **评估模式**：
   - 使用 `very_lenient=True` 模式
   - `task_match_k=2`（至少匹配 2 个字段）
   - `sim_threshold=0.6`（相似度阈值）

## 与 eval 脚本的一致性

现在 `tests/extractor_eval.py` 使用与 `eval/run_pipeline.py` 相同的：
- ✅ 任务格式：`{owner, action, object, deadline}`
- ✅ 评估函数：`prf_tasks()`
- ✅ 归一化函数：`_normalize_owner()`, `_normalize_text()`, `_normalize_date()`
- ✅ 相似度计算：`_similarity()`
- ✅ Due date 评估：`due_date_correctness()`

因此，结果应该与 eval 脚本一致。

